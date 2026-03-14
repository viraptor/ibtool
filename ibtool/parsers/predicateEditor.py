from ..models import ArchiveContext, NibObject, NibMutableList, NibMutableSet, NibNSNumber, XibObject, NibNil, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..constants import vFlags


def _parse_row_template(ctx, elem, parent):
    obj = XibObject(ctx, "NSPredicateEditorRowTemplate", elem, parent)
    ctx.extraNibObjects.append(obj)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)

    row_type = elem.attrib.get("rowType", "simple")
    obj["NSPredicateTemplateType"] = 2 if row_type == "compound" else 1

    options = 0
    opts_elem = elem.find("comparisonPredicateOptions")
    if opts_elem is not None:
        if opts_elem.attrib.get("caseInsensitive") == "YES":
            options |= 1
        if opts_elem.attrib.get("diacriticInsensitive") == "YES":
            options |= 2
    obj["NSPredicateTemplateOptions"] = options
    obj["NSPredicateTemplateModifier"] = 0
    obj["NSPredicateTemplateLeftAttributeType"] = 0
    obj["NSPredicateTemplateRightAttributeType"] = 0

    views = NibMutableList([])
    popup_menus = elem.find("popUpMenus")
    if popup_menus is not None:
        for menu_elem in popup_menus:
            if menu_elem.tag != "menu":
                continue
            popup = _build_popup_button(ctx, menu_elem, parent)
            views.addItem(popup)

    obj["NSPredicateTemplateViews"] = views

    left_wild = True
    right_wild = True

    left_arr_elem = elem.find("array")
    if left_arr_elem is not None and left_arr_elem.attrib.get("key") == "leftExpressionObject":
        left_wild = False
    right_int_elem = elem.find("integer")
    if right_int_elem is not None and right_int_elem.attrib.get("key") == "rightExpressionObject":
        right_wild = False
        obj["NSPredicateTemplateRightAttributeType"] = int(right_int_elem.attrib.get("value", "0"))

    obj["NSPredicateTemplateLeftIsWildcard"] = left_wild
    obj["NSPredicateTemplateRightIsWildcard"] = right_wild

    operators = NibMutableList([])
    if popup_menus is not None:
        menus = list(popup_menus)
        if len(menus) >= 2 and row_type == "simple":
            items_el = menus[1].find("items")
            if items_el is not None:
                for mi_el in items_el:
                    if mi_el.tag != "menuItem":
                        continue
                    rep = mi_el.find("integer")
                    if rep is not None and rep.attrib.get("key") == "representedObject":
                        operators.addItem(NibNSNumber(int(rep.attrib["value"])))

    obj["NSPredicateTemplateOperators"] = operators

    if left_arr_elem is not None and left_arr_elem.attrib.get("key") == "leftExpressionObject":
        left_exprs = NibMutableList([])
        for expr_el in left_arr_elem:
            if expr_el.tag == "expression":
                expr_obj = _build_expression(ctx, expr_el)
                left_exprs.addItem(expr_obj)
        obj["NSPredicateTemplateLeftExpressions"] = left_exprs

    return obj


def _build_expression(ctx, expr_el):
    expr_obj = NibObject("NSExpression")
    expr_type = expr_el.attrib.get("type", "")
    if expr_type == "keyPath":
        expr_obj["NSExpressionType"] = 10
        kp = expr_el.find("string")
        if kp is not None:
            expr_obj["NSKeyPath"] = NibString.intern(kp.text or "")
    return expr_obj


def _build_popup_button(ctx, menu_elem, parent):
    popup = XibObject(ctx, "NSPopUpButton", menu_elem, parent)
    ctx.extraNibObjects.append(popup)
    if popup.xibid:
        ctx.addObject(popup.xibid, popup)
    popup["NSNextResponder"] = NibNil()
    popup["NSNibTouchBar"] = NibNil()
    popup["NSvFlags"] = 0x100
    popup["NSSubviews"] = NibMutableList([])
    popup["NSFrame"] = NibString.intern("{{7, 1}, {68, 24}}")
    popup["NSSuperview"] = NibNil()
    popup["NSNextKeyView"] = NibNil()
    popup["NSViewWantsBestResolutionOpenGLSurface"] = True
    popup["IBNSSafeAreaLayoutGuide"] = NibNil()
    popup["IBNSLayoutMarginsGuide"] = NibNil()
    popup["IBNSClipsToBounds"] = 0
    popup["NSTag"] = -1
    popup["NSEnabled"] = True

    cell = NibObject("NSPopUpButtonCell")
    cell["NSCellFlags"] = 0x4000040
    cell["NSCellFlags2"] = 0x10000800
    font = NibObject("NSFont")
    font["NSName"] = NibString.intern(".AppleSystemUIFont")
    font["NSSize"] = 13.0
    font["NSfFlags"] = 0x1104
    cell["NSSupport"] = font
    cell["NSControlView"] = popup
    cell["NSAlternateContents"] = NibString.intern("")
    cell["NSButtonFlags"] = 0x4804110c
    cell["NSButtonFlags2"] = 0x02
    cell["NSAltersState"] = True
    cell["NSKeyEquivalent"] = NibString.intern("")
    cell["NSArrowPosition"] = 2
    cell["NSPreferredEdge"] = 3
    cell["NSUsesItemFromMenu"] = True

    nsmenu = NibObject("NSMenu")
    nsmenu["NSTitle"] = NibString.intern("")
    menu_items = NibMutableList([])

    items_elem = menu_elem.find("items")
    first_item = None
    if items_elem is not None:
        for mi_elem in items_elem:
            if mi_elem.tag != "menuItem":
                continue
            mi = NibObject("NSMenuItem")
            mi["NSTitle"] = NibString.intern(mi_elem.attrib.get("title", ""))
            mi["NSKeyEquiv"] = NibString.intern("")
            mi["NSKeyEquivModMask"] = 0x100000
            mi["NSMnemonicLoc"] = 0x7fffffff
            mi["NSAction"] = NibString.intern("_popUpItemAction:")
            mi["NSTarget"] = cell
            if mi_elem.attrib.get("state") == "on":
                mi["NSState"] = True
            mi["NSMenu"] = nsmenu
            mi["NSIsSeparator"] = False

            rep_elem = mi_elem.find("integer")
            if rep_elem is not None and rep_elem.attrib.get("key") == "representedObject":
                mi["NSRepresentedObject"] = NibNSNumber(int(rep_elem.attrib["value"]))

            expr_elem = mi_elem.find("expression")
            if expr_elem is not None and expr_elem.attrib.get("key") == "representedObject":
                mi["NSRepresentedObject"] = _build_expression(ctx, expr_elem)

            menu_items.addItem(mi)
            if first_item is None:
                first_item = mi

    nsmenu["NSMenuItems"] = menu_items
    if first_item:
        cell["NSMenuItem"] = first_item
    cell["NSMenu"] = nsmenu

    popup["NSCell"] = cell
    return popup


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    obj = make_xib_object(ctx, "NSPredicateEditor", elem, parent)
    obj["NSSuperview"] = parent

    slice_holder = NibObject("_NSRuleEditorViewSliceHolder")
    slice_holder["NSNextResponder"] = NibNil()
    slice_holder["NSNibTouchBar"] = NibNil()
    slice_holder["NSvFlags"] = 0x112
    slice_holder["NSSubviews"] = NibMutableList([])

    rect_elem = elem.find("rect")
    if rect_elem is not None:
        w = float(rect_elem.attrib.get("width", "0"))
        h = float(rect_elem.attrib.get("height", "0"))
        frame_size = f"{{{int(w)}, {int(h)}}}"
    else:
        frame_size = "{100, 100}"

    slice_holder["NSFrameSize"] = NibString.intern(frame_size)
    slice_holder["NSSuperview"] = obj
    slice_holder["NSNextKeyView"] = NibNil()
    slice_holder["NSViewWantsBestResolutionOpenGLSurface"] = True
    slice_holder["IBNSSafeAreaLayoutGuide"] = NibNil()
    slice_holder["IBNSLayoutMarginsGuide"] = NibNil()
    slice_holder["IBNSClipsToBounds"] = 0

    obj["NSSubviews"] = NibMutableList([slice_holder])

    drag_types = NibMutableSet([NibString.intern("NSRuleEditorItemPBoardType")])
    obj["NSDragTypes"] = drag_types

    obj["NSFrameSize"] = NibString.intern(frame_size)
    obj["NSNextKeyView"] = slice_holder
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    obj["IBNSLayoutMarginsGuide"] = NibNil()
    obj["IBNSClipsToBounds"] = 0
    obj["NSEnabled"] = True
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlSize"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = -1
    obj["NSControlTextAlignment"] = 0
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlSendActionMask"] = 0

    row_height = float(elem.attrib.get("rowHeight", "25"))
    obj["NSRuleEditorRowHeight"] = row_height

    nesting = elem.attrib.get("nestingMode", "compound")
    obj["NSRuleEditorNestingMode"] = {"single": 0, "list": 1, "compound": 2, "simple": 3}.get(nesting, 2)
    obj["NSRuleEditorAllowsEmptyCompoundRows"] = False
    obj["NSRuleEditorEditable"] = True
    obj["NSRuleEditorDelegate"] = NibNil()

    templates = NibMutableList([])
    row_templates_elem = elem.find("rowTemplates")
    if row_templates_elem is not None:
        for rt_elem in row_templates_elem:
            if rt_elem.tag == "predicateEditorRowTemplate":
                template = _parse_row_template(ctx, rt_elem, obj)
                templates.addItem(template)

    obj["NSPredicateTemplates"] = templates
    obj["NSPredicateEditorPredicate"] = NibNil()

    h = elem.attrib.get("verticalHuggingPriority", "250")
    hh = elem.attrib.get("horizontalHuggingPriority", "250")
    if hh != "250" or h != "750":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{hh}, {h}}}")

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
