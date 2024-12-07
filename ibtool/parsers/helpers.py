from contextlib import contextmanager
from ..models import ArchiveContext, XibId, NibObject, NibNil, XibObject, NibMutableSet, NibString, NibInlineString
from xml.etree.ElementTree import Element
from typing import Optional
from ..constants import vFlags, CellFlags, CellFlags2, LineBreakMode, CONTROL_SIZE_MAP, CONTROL_SIZE_MAP2, ButtonFlags, ButtonFlags2
from ..constant_objects import RGB_COLOR_SPACE, GENERIC_GREY_COLOR_SPACE


def parse_interfacebuilder_properties(ctx: ArchiveContext, elem: Element, _parent: Optional[NibObject], obj: NibObject) -> None:
    rid = elem.attrib.get("restorationIdentifier")
    if rid:
        obj["UIRestorationIdentifier"] = rid

    ibid = elem.attrib.get("id")
    if ibid:
        ctx.addObject(XibId(ibid), obj)

def make_xib_object(ctx: ArchiveContext, classname: str, elem: Element, parent: Optional[NibObject], view_attributes: bool = True) -> XibObject:
    obj = XibObject(ctx, classname, elem, parent)
    if obj.xibid is not None:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    if view_attributes:
        _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(elem is not None and elem.get("key") == "contentView"))
    return obj

def _xibparser_common_view_attributes(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], obj: XibObject, topLevelView: bool = False) -> None:
    obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    obj["IBNSLayoutMarginsGuide"] = NibNil()
    obj["IBNSClipsToBounds"] = int(0 if elem is None else elem.attrib.get("clipsToBounds") == "YES")
    if elem is not None and elem.attrib.get("hidden", "NO") == "YES":
        obj.flagsOr("NSvFlags", vFlags.HIDDEN)
    obj.flagsOr("NSvFlags", vFlags.AUTORESIZES_SUBVIEWS)
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    if parent is None or obj.extraContext.get("key") == "contentView":
        obj.setIfEmpty("NSNextResponder", NibNil())
    elif isinstance(parent, XibObject) and (parent.extraContext.get("key") == "contentView" or parent.xib_parent() is None):
        obj.setIfEmpty("NSNextResponder", parent)
    else:
        obj.setIfEmpty("NSNextResponder", parent.get("NSNextResponder") or NibNil())
    obj["NSNibTouchBar"] = NibNil()
    if elem is not None and elem.attrib.get("verticalHuggingPriority") is not None:
        obj.extraContext["verticalHuggingPriority"] = elem.attrib.get("verticalHuggingPriority")
    if elem is not None and elem.attrib.get("horizontalHuggingPriority") is not None:
        obj.extraContext["horizontalHuggingPriority"] = elem.attrib.get("horizontalHuggingPriority")
    __xibparser_set_compression_priority(ctx, obj, elem)

    if elem is not None and elem.attrib.get('translatesAutoresizingMaskIntoConstraints', "YES") == "NO":
        obj.extraContext["NSDoNotTranslateAutoresizingMask"] = True

def __xibparser_cell_flags(elem: Element, obj: NibObject, parent: NibObject) -> None:
    sendsAction = elem.attrib.get("sendsActionOnEndEditing", "NO") == "YES"
    sendsActionMask = CellFlags2.SENDS_ACTION_ON_END_EDITING if sendsAction else 0
    lineBreakMode = elem.attrib.get("lineBreakMode")
    lineBreakModeMask = {
        None: 0,
        "wordWrapping": 0,
        "charWrapping": 0,
        "truncatingTail": CellFlags.TRUNCATE_LAST_LINE,
        "truncatingHead": CellFlags.TRUNCATE_LAST_LINE,
        "truncatingMiddle": CellFlags.TRUNCATE_LAST_LINE,
        "clipping": CellFlags.TRUNCATE_LAST_LINE,
    }[lineBreakMode]
    lineBreakModeMask2 = {
        None: 0,
        "wordWrapping": CellFlags2.LINE_BREAK_MODE_WORD_WRAPPING,
        "charWrapping": CellFlags2.LINE_BREAK_MODE_CHAR_WRAPPING,
        "clipping": CellFlags2.LINE_BREAK_MODE_CLIPPING,
        "truncatingHead": CellFlags2.LINE_BREAK_MODE_TRUNCATING_HEAD,
        "truncatingTail": CellFlags2.LINE_BREAK_MODE_TRUNCATING_TAIL,
        "truncatingMiddle": CellFlags2.LINE_BREAK_MODE_TRUNCATING_MIDDLE,
    }[lineBreakMode]
    textAlignment = elem.attrib.get("alignment")
    textAlignmentMask = {None: CellFlags2.TEXT_ALIGN_NONE, "left": CellFlags2.TEXT_ALIGN_LEFT, "center": CellFlags2.TEXT_ALIGN_CENTER, "right": CellFlags2.TEXT_ALIGN_RIGHT}[textAlignment]
    selectable = (CellFlags.SELECTABLE + 1) if elem.attrib.get("selectable") == "YES" else 0
    state_on = CellFlags.STATE_ON if (elem.attrib.get("state") == "on") else 0
    text_field_flag = CellFlags.UNKNOWN_TEXT_FIELD if obj.originalclassname() in ["NSTextFieldCell", "NSButtonCell", "NSSearchFieldCell", "NSPopUpButtonCell", "NSTableHeaderCell"] else 0
    refuses_first_responder = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    refuses_first_responder_mask = CellFlags2.REFUSES_FIRST_RESPONDER if refuses_first_responder else 0
    scrollable = CellFlags.SCROLLABLE if elem.attrib.get("scrollable", "NO") == "YES" else 0
    disabled = 0 if elem.attrib.get("enabled", "YES") == "YES" else CellFlags.DISABLED
    editable = CellFlags.EDITABLE if elem.attrib.get("editable") == "YES" else 0
    bezeled = CellFlags.BEZELED if elem.attrib.get("borderStyle") == "bezel" else 0
    border = CellFlags.BORDERED if obj.originalclassname() == "NSTableHeaderCell" else 0 # TODO: hack
    size_flag = {
        None: 0,
        "regular": 0,
        "mini": CellFlags2.CONTROL_SIZE_MINI,
        "small": CellFlags2.CONTROL_SIZE_SMALL,
    }[elem.attrib.get("controlSize")]
    allows_mixed_state = CellFlags2.ALLOWS_MIXED_STATE if elem.attrib.get("allowsMixedState") == "YES" else 0

    obj.flagsOr("NSCellFlags", lineBreakModeMask | text_field_flag | selectable | state_on | scrollable | disabled | editable | bezeled | border)
    obj.flagsOr("NSCellFlags2", textAlignmentMask | sendsActionMask | lineBreakModeMask2 | refuses_first_responder_mask | size_flag | allows_mixed_state)

    if parent.originalclassname() == "NSTableColumn" and editable:
        parent["NSIsEditable"] = True

def __xibparser_cell_options(elem: Element, obj: NibObject, parent: NibObject) -> None:
    __xibparser_cell_flags(elem, obj, parent)
    parent["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder") == "YES"
    parent["NSControlLineBreakMode"] = {
        None: LineBreakMode.BY_WORD_WRAPPING,
        "wordWrapping": LineBreakMode.BY_WORD_WRAPPING,
        "charWrapping": LineBreakMode.BY_CHAR_WRAPPING,
        "clipping": LineBreakMode.BY_CLIPPING,
        "truncatingHead": LineBreakMode.BY_TRUNCATING_HEAD,
        "truncatingTail": LineBreakMode.BY_TRUNCATING_TAIL,
        "truncatingMiddle": LineBreakMode.BY_TRUNCATING_MIDDLE,
    }[elem.attrib.get("lineBreakMode")].value
    if obj.originalclassname() in ['NSButtonCell', 'NSTextFieldCell', 'NSImageCell', 'NSSearchFieldCell', 'NSPopUpButtonCell']:
        textAlignmentValue = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
        parent["NSControlTextAlignment"] = textAlignmentValue

    control_size = elem.attrib.get("controlSize")
    parent["NSControlSize"] = CONTROL_SIZE_MAP[control_size]
    parent["NSControlSize2"] = CONTROL_SIZE_MAP2[control_size]
    obj["NSControlSize2"] = CONTROL_SIZE_MAP2[control_size]



def __xibparser_button_flags(elem: Element, obj: XibObject, parent: NibObject) -> None:
    inset = int(elem.attrib.get("inset", "0"))
    inset = min(max(inset, 0), 3)
    inset = {0: 0, 1: ButtonFlags.INSET_1, 2: ButtonFlags.INSET_2, 3: (ButtonFlags.INSET_1|ButtonFlags.INSET_2)}[inset]
    buttonType = elem.attrib.get("type", "push")
    buttonTypeMask = {
        "push": 0,
        "radio": ButtonFlags.TYPE_RADIO,
        "recessed": ButtonFlags.TYPE_RECESSED,
        "check": ButtonFlags.TYPE_CHECK,
        "roundRect": ButtonFlags.TYPE_ROUND_RECT,
        "square": 0,
        "disclosureTriangle": 0,
        "help": 0,
        "smallSquare": 0,
        "roundTextured": 0,
        "disclosure": 0,
        "inline": 0,
        "bevel": 0,
    }[buttonType]
    button_type_id = {
        "push": 0x1,
        "check": 0x2,
        "radio": 0x2,
        "square": 0x2|0x4,
        "disclosureTriangle": 0x1|0x4,
        "help": 0x1|0x20,
        "smallSquare": 0x2|0x20,
        "roundTextured": 0x1|0x2|0x20,
        "disclosure": 0x2|0x4|0x20,
        "roundRect": 0x4|0x20,
        "recessed": 0x1|0x4|0x8|0x20,
        "inline": 0x1|0x2|0x4|0x20,
        "bevel": 0x2,
    }[buttonType]
    borderStyle = elem.attrib.get("borderStyle")
    borderStyleMask = {None: 0, "border": ButtonFlags.BORDERED, "borderAndBezel": ButtonFlags.BORDERED | ButtonFlags.BEZEL}[borderStyle]
    imageScaling = elem.attrib.get("imageScaling")
    imageScalingMask = {None: 0, "proportionallyDown": ButtonFlags2.IMAGE_SCALING_PROPORTIONALLY_DOWN}[imageScaling]
    imagePosition = elem.attrib.get("imagePosition")
    imagePositionMask = {None: 0, "left": ButtonFlags.IMAGE_LEFT, "right": ButtonFlags.IMAGE_RIGHT, "above": ButtonFlags.IMAGE_ABOVE, "below": ButtonFlags.IMAGE_BELOW, "only": ButtonFlags.IMAGE_ONLY}[imagePosition]

    obj.flagsOr("NSButtonFlags", inset | buttonTypeMask | borderStyleMask | imagePositionMask)
    obj.flagsOr("NSButtonFlags2", imageScalingMask | button_type_id)
    obj["NSAuxButtonType"] = {
        "push": 7,
        "radio": 4,
        "recessed": 1,
        "check": 3,
        "roundRect": 7,
        "square": 7,
        "disclosureTriangle": 2,
        "help": 7,
        "smallSquare": 7,
        "roundTextured": 7,
        "disclosure": 6,
        "inline": 7,
        "bevel": 7,
    }[buttonType]

def __xibparser_set_compression_priority(_ctx: ArchiveContext, obj: XibObject, elem: Element) -> None:
    horizontal_compression_prio = None if elem is None else elem.attrib.get('horizontalCompressionResistancePriority')
    vertical_compression_prio = None if elem is None else elem.attrib.get('verticalCompressionResistancePriority')
    if horizontal_compression_prio is not None or vertical_compression_prio is not None:
        if horizontal_compression_prio is None:
            horizontal_compression_prio = "750"
        if vertical_compression_prio is None:
            vertical_compression_prio = "750"
        obj["NSAntiCompressionPriority"] = f"{{{horizontal_compression_prio}, {vertical_compression_prio}}}"

@contextmanager
def __handle_view_chain(ctx: ArchiveContext, obj: XibObject):
    if ctx.viewKeyList:
        ctx.viewKeyList[-1]["NSNextKeyView"] = obj
    ctx.viewKeyList.append(obj)
    yield object()
    ctx.viewKeyList.pop(-1)

    x, y, w, h = obj.frame()
    if x == 0 and y == 0:
        obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        obj["NSFrame"] = NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")

def make_system_image(name: str, parent: NibObject) -> NibObject:
    obj = NibObject("NSCustomResource", parent)
    obj["NSResourceName"] = NibString.intern(name)
    obj["NSClassName"] = NibString.intern("NSImage")
    obj["IBNamespaceID"] = NibString.intern("system")
    design_size = NibObject("NSValue", obj)
    design_size["NS.sizeval"] = NibString.intern("{32, 32}")
    design_size["NS.special"] = 2
    obj["IBDesignSize"] = design_size
    obj["IBDesignImageConfiguration"] = NibNil()
    return obj

def default_drag_types() -> NibMutableSet:
    return NibMutableSet([
        NibString.intern('Apple PDF pasteboard type'),
        NibString.intern('Apple PICT pasteboard type'),
        NibString.intern('Apple PNG pasteboard type'),
        NibString.intern('NSFilenamesPboardType'),
        NibString.intern('NeXT TIFF v4.0 pasteboard type'),
        NibString.intern('com.apple.NSFilePromiseItemMetaData'),
        NibString.intern('com.apple.pasteboard.promised-file-content-type'),
        NibString.intern('dyn.ah62d4rv4gu8yc6durvwwa3xmrvw1gkdusm1044pxqyuha2pxsvw0e55bsmwca7d3sbwu')
        ])

def makeSystemColor(name):
    def systemGrayColorTemplate(name, components, white):
        return NibObject('NSColor', None, {
            'NSCatalogName': 'System',
            'NSColor': NibObject('NSColor', None, {
                'NSColorSpace': 3,
                'NSComponents': NibInlineString(components),
                'NSCustomColorSpace': GENERIC_GREY_COLOR_SPACE,
                'NSWhite': NibInlineString(white),
                }),
            'NSColorName': NibString.intern(name),
            'NSColorSpace': 6,
            })

    def systemCustomRGBColorTemplate(name, sub_name, components, rgb):
        return NibObject("NSColor", None, {
            "NSCatalogName": NibString.intern("System"),
            "NSColorName": NibString.intern(name),
            "NSColorSpace": 6,
            "NSColor": NibObject("NSColor", None, {
                "NSCatalogName": NibString.intern("System"),
                "NSColorSpace": 6,
                "NSColorName": NibString.intern(sub_name),
                "NSColor": NibObject("NSColor", None, {
                    "NSComponents": NibInlineString(components),
                    "NSColorSpace": 1,
                    "NSRGB": NibInlineString(rgb),
                    "NSCustomColorSpace": RGB_COLOR_SPACE,
                }),
            })
        })

    def systemRGBColorTemplate(name, components, rgb):
        return NibObject("NSColor", None, {
            "NSCatalogName": NibString.intern("System"),
            "NSColorName": NibString.intern(name),
            "NSColorSpace": 6,
            "NSColor": NibObject("NSColor", None, {
                "NSColorSpace": 1,
                "NSComponents": NibInlineString(components),
                "NSRGB": NibInlineString(rgb),
                "NSCustomColorSpace": RGB_COLOR_SPACE,
            }),
        })


    if name == 'controlColor':
        return systemGrayColorTemplate(name, b'0.6666666667 1', b'0.602715373\x00')
    elif name == 'controlTextColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'controlBackgroundColor':
        return systemGrayColorTemplate(name, b'0.6666666667 1', b'0.602715373\x00')
    elif name == 'textColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'textBackgroundColor':
        return systemGrayColorTemplate(name, b'1 1', b'1\x00')
    elif name == 'labelColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'textInsertionPointColor':
        return systemCustomRGBColorTemplate(name, 'systemBlueColor', '0 0 1 1', b'0 0 0.9981992245\x00')
    elif name == 'selectedTextBackgroundColor':
        return systemGrayColorTemplate(name, b'0.6666666667 1', b'0.602715373\x00')
    elif name == 'selectedTextColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'linkColor':
        return systemRGBColorTemplate(name, '0 0 1 1', b'0 0 0.9981992245\x00')
    elif name == 'gridColor':
        return systemGrayColorTemplate(name, b'0.5 1', b'0.4246723652\x00')
    elif name == 'headerTextColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'headerColor':
        return systemGrayColorTemplate(name, b'1 1', b'1\x00')
    else:
        raise Exception(f"unknown name {name}")
