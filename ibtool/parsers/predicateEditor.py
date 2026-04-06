from ..models import ArchiveContext, NibObject, NibList, NibMutableList, NibMutableSet, NibDictionary, NibNSNumber, NibInlineString, XibObject, NibNil, NibString
from ..constant_objects import MENU_ON_IMAGE, MENU_MIXED_IMAGE, GENERIC_GREY_COLOR_SPACE
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..constants import vFlags, FontFlags, NSNotFound, EventModifierFlags
from .font import to_flags_val
import math

# SF Pro Text Regular glyph advances at 2048 UPM
_SF_ADVANCES = {
    ' ': 576,
    'A': 1380, 'B': 1346, 'C': 1466, 'D': 1488, 'E': 1220, 'F': 1172, 'G': 1529,
    'H': 1520, 'I': 548,  'J': 1102, 'K': 1349, 'L': 1163, 'M': 1790, 'N': 1520,
    'O': 1580, 'P': 1301, 'Q': 1580, 'R': 1338, 'S': 1305, 'T': 1298, 'U': 1510,
    'V': 1380, 'W': 1982, 'X': 1390, 'Y': 1342, 'Z': 1355,
    'a': 1130, 'b': 1258, 'c': 1146, 'd': 1258, 'e': 1170, 'f': 741,  'g': 1248,
    'h': 1205, 'i': 506,  'j': 505,  'k': 1112, 'l': 518,  'm': 1782, 'n': 1195,
    'o': 1210, 'p': 1250, 'q': 1248, 'r': 780,  's': 1072, 't': 744,  'u': 1195,
    'v': 1110, 'w': 1586, 'x': 1074, 'y': 1112, 'z': 1104,
}
_POPUP_CHROME = 37
_POPUP_KP_CHROME = 36
_POPUP_PER_ITEM = 0.14
_POPUP_FONT_SIZE = 13.0
_POPUP_UPM = 2048

COMPOUND_POPUP_FRAMES = [
    (7, 68),
    (81, 173),
]


def _measure_text_width(text, zero_dots=False):
    if zero_dots:
        return sum(_SF_ADVANCES.get(c, 1000) if c != '.' else 0 for c in text) * _POPUP_FONT_SIZE / _POPUP_UPM
    return sum(_SF_ADVANCES.get(c, 1000) for c in text) * _POPUP_FONT_SIZE / _POPUP_UPM


def _compute_popup_width(menu_elem):
    max_title_w = 0
    max_kp_w = 0
    num_items = 0
    items_elem = menu_elem.find("items")
    if items_elem is not None:
        for mi_elem in items_elem:
            if mi_elem.tag == "menuItem":
                num_items += 1
                title = mi_elem.attrib.get("title", "")
                tw = _measure_text_width(title)
                if tw > max_title_w:
                    max_title_w = tw
                expr_elem = mi_elem.find("expression")
                if expr_elem is not None and expr_elem.attrib.get("type") == "keyPath":
                    kp_text = expr_elem.attrib.get("keyPath", "")
                    if not kp_text:
                        kp_str_elem = expr_elem.find("string")
                        if kp_str_elem is not None and kp_str_elem.text:
                            kp_text = kp_str_elem.text
                    if kp_text:
                        kp_w = _measure_text_width(kp_text, zero_dots=True)
                        if kp_w > max_kp_w:
                            max_kp_w = kp_w
    title_popup_w = math.ceil(max_title_w + num_items * _POPUP_PER_ITEM) + _POPUP_CHROME
    if max_kp_w > 0:
        kp_popup_w = math.ceil(max_kp_w) + _POPUP_KP_CHROME
        return max(title_popup_w, kp_popup_w)
    return title_popup_w


def _parse_row_template(ctx, elem, parent, has_simple_templates=False):
    custom_class = elem.attrib.get("customClass")
    if custom_class:
        elem.attrib.pop("customClass", None)
        obj = XibObject(ctx, "NSPredicateEditorRowTemplate", elem, parent)
        obj.setclassname("NSClassSwapper")
        obj["NSClassName"] = NibString.intern(custom_class)
        obj["NSOriginalClassName"] = NibString.intern("NSPredicateEditorRowTemplate")
    else:
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

    left_arr_elem = elem.find("array")
    has_left = left_arr_elem is not None and left_arr_elem.attrib.get("key") == "leftExpressionObject"
    right_int_elem = elem.find("integer")
    has_right = right_int_elem is not None and right_int_elem.attrib.get("key") == "rightExpressionObject"

    if row_type == "compound":
        left_wild = False
        right_wild = False
    else:
        left_wild = not has_left
        right_wild = has_right

    if has_right:
        obj["NSPredicateTemplateRightAttributeType"] = int(right_int_elem.attrib.get("value", "0"))

    views = []
    popup_menus = elem.find("popUpMenus")
    if popup_menus is not None:
        menu_elems = [me for me in popup_menus if me.tag == "menu"]
        if row_type == "compound":
            for i, menu_elem in enumerate(menu_elems):
                if i < len(COMPOUND_POPUP_FRAMES):
                    x, w = COMPOUND_POPUP_FRAMES[i]
                else:
                    x, w = COMPOUND_POPUP_FRAMES[-1]
                popup = _build_popup_button(ctx, menu_elem, obj, x, w, add_subviews=has_simple_templates)
                views.append(popup)
        else:
            x = 37
            for menu_elem in menu_elems:
                w = _compute_popup_width(menu_elem)
                popup = _build_popup_button(ctx, menu_elem, obj, x, w, add_subviews=not custom_class)
                views.append(popup)
                x += w + 6

        if right_wild and row_type != "compound":
            editor_w = parent.extraContext.get("pe_editor_width", 429)
            tf_x = x
            tf_w = editor_w - tf_x - 76
            if tf_w < 20:
                tf_w = 98
            text_field = _build_text_field(ctx, tf_x, tf_w, add_subviews=not custom_class)
            views.append(text_field)

        set_chain = custom_class or (row_type == "compound" and not has_simple_templates)
        if set_chain:
            for i in range(len(views) - 1):
                views[i]["NSNextKeyView"] = views[i + 1]

    obj["NSPredicateTemplateViews"] = NibList(views)

    obj["NSPredicateTemplateLeftIsWildcard"] = left_wild
    obj["NSPredicateTemplateRightIsWildcard"] = right_wild

    return obj


def _build_expression(ctx, expr_el):
    expr_type = expr_el.attrib.get("type", "")
    if expr_type == "keyPath":
        kp_text = expr_el.attrib.get("keyPath", "")

        kp_spec = NibObject("NSKeyPathSpecifierExpression")
        kp_spec["NSExpressionType"] = 10
        kp_spec["NSKeyPath"] = NibString.intern(kp_text)

        self_expr = NibObject("NSSelfExpression")
        self_expr["NSExpressionType"] = 1

        selector = "valueForKeyPath:" if "." in kp_text else "valueForKey:"

        expr_obj = NibObject("NSKeyPathExpression")
        expr_obj["NSExpressionType"] = 3
        expr_obj["NSSelectorName"] = NibString.intern(selector)
        expr_obj["NSOperand"] = self_expr
        expr_obj["NSArguments"] = NibMutableList([kp_spec])
        return expr_obj
    expr_obj = NibObject("NSExpression")
    return expr_obj


def _build_popup_button(ctx, menu_elem, row_template, x, w, add_subviews=True):
    popup = NibObject("NSPopUpButton")
    popup["NSNextResponder"] = NibNil()
    popup["NSNibTouchBar"] = NibNil()
    popup["NSvFlags"] = 0x100
    popup["NSFrame"] = NibString.intern(f"{{{{{x}, 1}}, {{{w}, 24}}}}")
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
    font["NSSize"] = 11.0
    font["NSfFlags"] = to_flags_val(FontFlags.ROLE_SMALL_SYSTEM_FONT.value)
    cell["NSSupport"] = font
    cell["NSControlView"] = popup
    cell["NSButtonFlags"] = -0x797fc000
    cell["NSButtonFlags2"] = 0x24
    cell["NSBezelStyle"] = 12
    cell["NSKeyEquivalent"] = NibString.intern("")
    cell["NSPeriodicDelay"] = 400
    cell["NSPeriodicInterval"] = 75
    cell["NSAuxButtonType"] = -1

    nsmenu = XibObject(ctx, "NSMenu", menu_elem, row_template)
    nsmenu["NSTitle"] = NibString.intern("")
    menu_items = NibMutableList([])

    items_elem = menu_elem.find("items")
    first_item = None
    if items_elem is not None:
        for mi_elem in items_elem:
            if mi_elem.tag != "menuItem":
                continue
            mi = XibObject(ctx, "NSMenuItem", mi_elem, nsmenu)
            mi["NSMenu"] = nsmenu
            mi["NSAllowsKeyEquivalentLocalization"] = True
            mi["NSAllowsKeyEquivalentMirroring"] = True
            mi["NSTitle"] = NibString.intern(mi_elem.attrib.get("title", ""))
            mi["NSKeyEquiv"] = NibString.intern("")
            mi["NSKeyEquivModMask"] = EventModifierFlags.COMMAND
            mi["NSMnemonicLoc"] = NSNotFound
            if mi_elem.attrib.get("state") == "on":
                mi["NSState"] = 1
            mi["NSOnImage"] = MENU_ON_IMAGE
            mi["NSMixedImage"] = MENU_MIXED_IMAGE
            mi["NSAction"] = NibString.intern("_popUpItemAction:")

            rep_elem = mi_elem.find("integer")
            if rep_elem is not None and rep_elem.attrib.get("key") == "representedObject":
                mi["NSRepObject"] = NibNSNumber(int(rep_elem.attrib["value"]))

            expr_elem = mi_elem.find("expression")
            if expr_elem is not None and expr_elem.attrib.get("key") == "representedObject":
                mi["NSRepObject"] = _build_expression(ctx, expr_elem)

            mi["NSTarget"] = cell
            mi["NSHiddenInRepresentation"] = False

            menu_items.addItem(mi)
            if first_item is None:
                first_item = mi

    nsmenu["NSMenuItems"] = menu_items
    ctx.extraNibObjects.append(nsmenu)
    for mi_obj in menu_items.items():
        ctx.extraNibObjects.append(mi_obj)

    if first_item:
        cell["NSMenuItem"] = first_item
        if first_item.properties.get("NSRepObject"):
            cell["NSRepresentedObject"] = first_item["NSRepObject"]
    cell["NSMenuItemRespectAlignment"] = True
    cell["NSMenu"] = nsmenu
    cell["NSPreferredEdge"] = 1
    cell["NSUsesItemFromMenu"] = True
    cell["NSAltersState"] = True
    cell["NSArrowPosition"] = 2

    if add_subviews:
        popup["NSSubviews"] = NibMutableList([])
    popup["NSCell"] = cell
    popup["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    popup["NSControlSize"] = 0
    popup["NSControlContinuous"] = False
    popup["NSControlRefusesFirstResponder"] = False
    popup["NSControlUsesSingleLineMode"] = False
    popup["NSControlTextAlignment"] = 4
    popup["NSControlLineBreakMode"] = 4
    popup["NSControlWritingDirection"] = -1
    popup["NSControlSendActionMask"] = 4
    popup["IBNSShadowedSymbolConfiguration"] = NibNil()
    return popup


def _build_text_field(ctx, x, w, add_subviews=True):
    tf = NibObject("NSTextField")
    tf["NSNextResponder"] = NibNil()
    tf["NSNibTouchBar"] = NibNil()
    tf["NSvFlags"] = 0x100
    tf["NSFrame"] = NibString.intern(f"{{{{{x}, 4}}, {{{w}, 18}}}}")
    tf["NSSuperview"] = NibNil()
    tf["NSNextKeyView"] = NibNil()
    tf["NSViewWantsBestResolutionOpenGLSurface"] = True
    tf["IBNSSafeAreaLayoutGuide"] = NibNil()
    tf["IBNSLayoutMarginsGuide"] = NibNil()
    tf["IBNSClipsToBounds"] = 0
    tf["NSEnabled"] = True

    cell = NibObject("NSTextFieldCell")
    cell["NSCellFlags"] = 0x14700040
    cell["NSCellFlags2"] = 0x420400
    cell["NSContents"] = NibString.intern("")
    font = NibObject("NSFont")
    font["NSName"] = NibString.intern(".AppleSystemUIFont")
    font["NSSize"] = 11.0
    font["NSfFlags"] = to_flags_val(FontFlags.ROLE_SMALL_SYSTEM_FONT.value)
    cell["NSSupport"] = font
    cell["NSControlView"] = tf
    cell["NSDrawsBackground"] = True

    bg_color = NibObject("NSColor")
    bg_color["NSColorSpace"] = 6
    bg_color["NSCatalogName"] = NibString.intern("System")
    bg_color["NSColorName"] = NibString.intern("textBackgroundColor")
    inner_bg = NibObject("NSColor")
    inner_bg["NSColorSpace"] = 3
    inner_bg["NSWhite"] = NibInlineString(b'1\x00')
    inner_bg["NSCustomColorSpace"] = GENERIC_GREY_COLOR_SPACE
    inner_bg["NSComponents"] = NibInlineString(b'1 1')
    inner_bg["NSLinearExposure"] = NibInlineString(b'1')
    bg_color["NSColor"] = inner_bg
    cell["NSBackgroundColor"] = bg_color

    text_color = NibObject("NSColor")
    text_color["NSColorSpace"] = 6
    text_color["NSCatalogName"] = NibString.intern("System")
    text_color["NSColorName"] = NibString.intern("controlTextColor")
    inner_tc = NibObject("NSColor")
    inner_tc["NSColorSpace"] = 3
    inner_tc["NSWhite"] = NibInlineString(b'0\x00')
    inner_tc["NSCustomColorSpace"] = GENERIC_GREY_COLOR_SPACE
    inner_tc["NSComponents"] = NibInlineString(b'0 1')
    inner_tc["NSLinearExposure"] = NibInlineString(b'1')
    text_color["NSColor"] = inner_tc
    cell["NSTextColor"] = text_color

    if add_subviews:
        tf["NSSubviews"] = NibMutableList([])
    tf["NSCell"] = cell
    tf["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    tf["NSControlSize"] = 1
    tf["NSControlContinuous"] = False
    tf["NSControlRefusesFirstResponder"] = False
    tf["NSControlUsesSingleLineMode"] = False
    tf["NSControlTextAlignment"] = 0
    tf["NSControlLineBreakMode"] = 2
    tf["NSControlWritingDirection"] = -1
    tf["NSControlSendActionMask"] = 4
    tf["NSTextFieldAlignmentRectInsetsVersion"] = 2
    tf["NSAllowsWritingTools"] = True
    tf["NSTextFieldAllowsWritingToolsAffordance"] = False
    tf["NS.resolvesNaturalAlignmentWithBaseWritingDirection"] = False
    return tf


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    obj = make_xib_object(ctx, "NSPredicateEditor", elem, parent)
    obj["NSSuperview"] = parent

    slice_holder = NibObject("_NSRuleEditorViewSliceHolder")
    slice_holder["NSNextResponder"] = obj
    slice_holder["NSNibTouchBar"] = NibNil()
    slice_holder["NSvFlags"] = 0x112
    slice_holder["NSSubviews"] = NibMutableList([])

    rect_elem = elem.find("rect")
    if rect_elem is not None:
        w = float(rect_elem.attrib.get("width", "0"))
        h = float(rect_elem.attrib.get("height", "0"))
        frame_size = f"{{{int(w)}, {int(h)}}}"
    else:
        w = 100
        h = 100
        frame_size = "{100, 100}"

    obj.extraContext["pe_editor_width"] = int(w)

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
    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    obj["NSControlSize"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlTextAlignment"] = 0
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlWritingDirection"] = 0
    obj["NSControlSendActionMask"] = 4

    row_height = float(elem.attrib.get("rowHeight", "25"))

    obj["NSRuleEditorAlignmentGridWidth"] = 75.0
    obj["NSRuleEditorSliceHeight"] = row_height
    obj["NSRuleEditorFormattingDictionary"] = NibDictionary([])
    obj["NSRuleEditorEditable"] = True
    obj["NSRuleEditorAllowsEmptyCompoundRows"] = False
    obj["NSRuleEditorDisallowEmpty"] = True

    nesting = elem.attrib.get("nestingMode", "compound")
    obj["NSRuleEditorNestingMode"] = {"single": 0, "list": 1, "compound": 2, "simple": 3}.get(nesting, 2)

    obj["NSRuleEditorRowTypeKeyPath"] = NibString.intern("rowType")
    obj["NSRuleEditorSubrowsArrayKeyPath"] = NibString.intern("subrows")
    obj["NSRuleEditorItemsKeyPath"] = NibString.intern("criteria")
    obj["NSRuleEditorValuesKeyPath"] = NibString.intern("displayValues")
    obj["NSRuleEditorBoundArrayKeyPath"] = NibString.intern("boundArray")
    obj["NSRuleEditorRowClass"] = NibString.intern("NSMutableDictionary")
    obj["NSRuleEditorSlicesHolder"] = slice_holder
    obj["NSRuleEditorDelegate"] = NibNil()

    unbound_holder = NibObject("_NSRuleEditorViewUnboundRowHolder")
    unbound_holder["NSBoundArray"] = NibMutableList([])
    obj["NSRuleEditorBoundArrayOwner"] = unbound_holder

    obj["NSRuleEditorSlices"] = NibMutableList([])

    templates = NibList([])
    row_templates_elem = elem.find("rowTemplates")
    has_simple_templates = False
    if row_templates_elem is not None:
        for rt_elem in row_templates_elem:
            if rt_elem.tag == "predicateEditorRowTemplate" and rt_elem.attrib.get("rowType", "simple") != "compound":
                has_simple_templates = True
                break
    if has_simple_templates:
        parent.extraContext["preserve_clip_autoresizing"] = True
    if row_templates_elem is not None:
        for rt_elem in row_templates_elem:
            if rt_elem.tag == "predicateEditorRowTemplate":
                template = _parse_row_template(ctx, rt_elem, obj, has_simple_templates=has_simple_templates)
                templates.addItem(template)

    obj["NSPredicateTemplates"] = templates
    obj["NSPredicateEditorPredicate"] = NibNil()

    h_prio = elem.attrib.get("verticalHuggingPriority", "250")
    hh_prio = elem.attrib.get("horizontalHuggingPriority", "250")
    if hh_prio != "250" or h_prio != "750":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{hh_prio}, {h_prio}}}")

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    ar_elem = elem.find("autoresizingMask")
    if ar_elem is not None:
        from .autoresizingMask import parse as parse_ar
        parse_ar(ctx, ar_elem, obj)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    conn_elem = elem.find("connections")
    if conn_elem is not None:
        from ..parsers_base import parse_children as _pc
        _pc(ctx, conn_elem, obj)

    return obj
