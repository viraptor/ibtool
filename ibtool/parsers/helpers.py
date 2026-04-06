from contextlib import contextmanager
from ..models import ArchiveContext, XibId, NibObject, NibNil, XibObject, NibMutableSet, NibString, NibInlineString, NibList, NibNSNumber, NibData, NibMutableList, NibDictionary
from xml.etree.ElementTree import Element
from typing import Optional, Any, Callable
from ..constants import vFlags, CellFlags, CellFlags2, LineBreakMode, CONTROL_SIZE_MAP, CONTROL_SIZE_MAP2, ButtonFlags, ButtonFlags2, BEZEL_STYLE_MAP
from ..constant_objects import RGB_COLOR_SPACE, GENERIC_GREY_COLOR_SPACE
from dataclasses import dataclass
import re as _re


def _fmt_coord(v) -> str:
    if isinstance(v, float) and v != int(v):
        return repr(v)
    return str(int(v))

def frame_string(x, y, w, h) -> NibString:
    return NibString.intern(f"{{{{{_fmt_coord(x)}, {_fmt_coord(y)}}}, {{{_fmt_coord(w)}, {_fmt_coord(h)}}}}}")

def size_string(w: int, h: int) -> NibString:
    return NibString.intern(f"{{{int(w)}, {int(h)}}}")

def parse_frame_string(s) -> 'tuple[int, int, int, int] | None':
    """Parse '{{x, y}, {w, h}}' NibString to (x, y, w, h)."""
    m = _re.match(r'\{\{(\d+), (\d+)\}, \{(\d+), (\d+)\}\}', s._text)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return None


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
    obj.setIfEmpty("IBNSSafeAreaLayoutGuide", NibNil())
    obj.setIfEmpty("IBNSLayoutMarginsGuide", NibNil())
    obj["IBNSClipsToBounds"] = int(0 if elem is None else elem.attrib.get("clipsToBounds") == "YES")
    if elem is not None and elem.attrib.get("hidden", "NO") == "YES":
        obj.flagsOr("NSvFlags", vFlags.HIDDEN)
    if elem is None or elem.attrib.get("autoresizesSubviews", "YES") != "NO":
        obj.flagsOr("NSvFlags", vFlags.AUTORESIZES_SUBVIEWS)
    else:
        obj.extraContext["no_autoresizes_subviews"] = True
    focus_ring_type = elem.attrib.get("focusRingType") if elem is not None else None
    if focus_ring_type:
        obj.extraContext["focusRingType"] = focus_ring_type
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    if parent is None or obj.extraContext.get("key") == "contentView":
        obj.setIfEmpty("NSNextResponder", NibNil())
    elif isinstance(parent, XibObject):
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

def _xibparser_common_translate_autoresizing(ctx: ArchiveContext, elem: Element, _parent: Optional[NibObject], obj: XibObject) -> None:
    if elem is not None and elem.attrib.get("fixedFrame") == "YES":
        obj.extraContext["fixedFrame"] = True
    if elem is not None and elem.attrib.get('translatesAutoresizingMaskIntoConstraints', "YES") == "NO":
        obj.extraContext["NSDoNotTranslateAutoresizingMask"] = True
        if elem.attrib.get("fixedFrame") != "YES" and _parent is None:
            obj["NSDoNotTranslateAutoresizingMask"] = True

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
    text_field_flag = CellFlags.TYPE_TEXT_CELL if obj.originalclassname() in ["NSTextFieldCell", "NSButtonCell", "NSSearchFieldCell", "NSPopUpButtonCell", "NSTableHeaderCell", "NSSegmentedCell", "NSDatePickerCell", "NSSecureTextFieldCell", "NSPathCell"] else 0
    refuses_first_responder = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    refuses_first_responder_mask = CellFlags2.REFUSES_FIRST_RESPONDER if refuses_first_responder else 0
    scrollable = CellFlags.SCROLLABLE if elem.attrib.get("scrollable", "NO") == "YES" else 0
    disabled = 0 if elem.attrib.get("enabled", "YES") == "YES" else CellFlags.DISABLED
    editable = CellFlags.EDITABLE if elem.attrib.get("editable") == "YES" else 0
    bezeled = CellFlags.BEZELED if elem.attrib.get("borderStyle") == "bezel" else 0
    border = CellFlags.BORDERED if obj.originalclassname() in ("NSTableHeaderCell", "NSSegmentedCell") else 0 # TODO: hack
    allows_undo = 0 if elem.attrib.get("allowsUndo", "YES") == "YES" else CellFlags2.FORBIDS_UNDO
    uses_single_line_mode = CellFlags2.USES_SINGLE_LINE_MODE if elem.attrib.get("usesSingleLineMode", "NO") == "YES" else 0
    parent.extraContext["usesSingleLineMode"] = bool(uses_single_line_mode)
    size_flag = {
        None: 0,
        "regular": 0,
        "mini": CellFlags2.CONTROL_SIZE_MINI,
        "small": CellFlags2.CONTROL_SIZE_SMALL,
    }[elem.attrib.get("controlSize")]
    allows_mixed_state = CellFlags2.ALLOWS_MIXED_STATE if elem.attrib.get("allowsMixedState") == "YES" else 0
    focus_ring_type = elem.attrib.get("focusRingType")
    focus_ring_none = CellFlags2.FOCUS_RING_NONE if focus_ring_type == "none" else (CellFlags2.FOCUS_RING_EXTERIOR if focus_ring_type == "exterior" else 0)
    truncates_last_visible = CellFlags2.TRUNCATES_LAST_VISIBLE_LINE if elem.attrib.get("truncatesLastVisibleLine") == "YES" else 0

    obj.flagsOr("NSCellFlags", lineBreakModeMask | text_field_flag | selectable | state_on | scrollable | disabled | editable | bezeled | border)
    obj.flagsOr("NSCellFlags2", textAlignmentMask | sendsActionMask | lineBreakModeMask2 | refuses_first_responder_mask | size_flag | allows_mixed_state | allows_undo | uses_single_line_mode | focus_ring_none | truncates_last_visible)

    if parent.originalclassname() == "NSTableColumn" and editable:
        parent["NSIsEditable"] = True

def __xibparser_cell_options(elem: Element, obj: NibObject, parent: NibObject) -> None:
    __xibparser_cell_flags(elem, obj, parent)
    parent["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder") == "YES"
    parent.setIfNotDefault("NSAutomaticTextCompletionDisabled", elem.attrib.get("textCompletion") == "NO", False)
    parent["NSControlLineBreakMode"] = {
        None: LineBreakMode.BY_WORD_WRAPPING,
        "wordWrapping": LineBreakMode.BY_WORD_WRAPPING,
        "charWrapping": LineBreakMode.BY_CHAR_WRAPPING,
        "clipping": LineBreakMode.BY_CLIPPING,
        "truncatingHead": LineBreakMode.BY_TRUNCATING_HEAD,
        "truncatingTail": LineBreakMode.BY_TRUNCATING_TAIL,
        "truncatingMiddle": LineBreakMode.BY_TRUNCATING_MIDDLE,
    }[elem.attrib.get("lineBreakMode")].value
    if obj.originalclassname() in ['NSButtonCell', 'NSTextFieldCell', 'NSImageCell', 'NSSearchFieldCell', 'NSPopUpButtonCell', 'NSSegmentedCell', 'NSColorWellCell', 'NSSliderCell', 'NSSecureTextFieldCell']:
        textAlignmentValue = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
        parent["NSControlTextAlignment"] = textAlignmentValue
        direction = {'natural': -1, "leftToRight": 0, "rightToLeft": 1}[elem.attrib.get("baseWritingDirection=", "natural")]
        parent["NSControlWritingDirection"] = direction
        parent["NSControlContinuous"] = elem.attrib.get("continuous", "NO") == "YES"

    control_size = elem.attrib.get("controlSize")
    parent["NSControlSize"] = CONTROL_SIZE_MAP[control_size]



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
        "squareTextured": 0,
        "disclosureTriangle": 0,
        "help": 0,
        "smallSquare": 0,
        "roundTextured": 0,
        "disclosure": 0,
        "inline": 0,
        "bevel": 0,
    }[buttonType]
    bezelStyle = elem.attrib.get("bezelStyle")
    button_type_id = {
        "radio": BEZEL_STYLE_MAP.get(bezelStyle, 0),
        "push": 0x1,
        "check": 0x2,
        "square": 0x2|0x4,
        "squareTextured": 0x20,
        "disclosureTriangle": 0x1|0x4,
        "help": 0x1|0x20,
        "smallSquare": 0x2|0x20,
        "roundTextured": 0x1|0x2|0x20,
        "disclosure": 0x2|0x4|0x20,
        "roundRect": 0x4|0x20,
        "recessed": 0x1|0x4|0x8|0x20,
        "inline": 0x1|0x2|0x4|0x20,
        "bevel": 0x1 if bezelStyle == "rounded" else 0x2,
    }[buttonType]
    borderStyle = elem.attrib.get("borderStyle")
    borderStyleMask = {None: 0, "border": ButtonFlags.BORDERED, "bezel": ButtonFlags.BEZEL, "borderAndBezel": ButtonFlags.BORDERED | ButtonFlags.BEZEL}[borderStyle]
    imageScaling = elem.attrib.get("imageScaling")
    imageScalingMask = {None: 0, "proportionallyDown": ButtonFlags2.IMAGE_SCALING_PROPORTIONALLY_DOWN, "proportionallyUpOrDown": 0x40}[imageScaling]
    imagePosition = elem.attrib.get("imagePosition")
    imagePositionMask = {None: 0, "left": ButtonFlags.IMAGE_LEFT, "right": ButtonFlags.IMAGE_RIGHT, "above": ButtonFlags.IMAGE_ABOVE, "below": ButtonFlags.IMAGE_BELOW, "only": ButtonFlags.IMAGE_ONLY, "overlaps": ButtonFlags.IMAGE_OVERLAPS}[imagePosition]

    obj.flagsOr("NSButtonFlags", inset | buttonTypeMask | borderStyleMask | imagePositionMask)
    obj.flagsOr("NSButtonFlags2", imageScalingMask | button_type_id)
    aux_type_map = {
        "push": 7,
        "radio": 4,
        "recessed": 1,
        "check": 3,
        "roundRect": 7,
        "squareTextured": 7,
        "disclosureTriangle": 2,
        "help": 7,
        "smallSquare": 7,
        "roundTextured": 7,
        "disclosure": 6,
        "inline": 7,
        "bevel": 7,
    }
    if buttonType in ("square", "squareTextured"):
        behavior_elem = elem.find("behavior")
        if behavior_elem is not None and behavior_elem.attrib.get("lightByContents") == "YES" and behavior_elem.attrib.get("pushIn") != "YES":
            obj["NSAuxButtonType"] = 5
        elif behavior_elem is not None and behavior_elem.attrib.get("pushIn") == "YES":
            obj["NSAuxButtonType"] = 7 if buttonType == "square" else 2
        else:
            obj["NSAuxButtonType"] = 0
    else:
        obj["NSAuxButtonType"] = aux_type_map[buttonType]

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
        obj["NSFrameSize"] = size_string(w, h)
    else:
        obj["NSFrame"] = frame_string(x, y, w, h)

def make_image(name: str, parent: NibObject, ctx: "ArchiveContext") -> NibObject:
    obj = NibObject("NSCustomResource", parent)
    obj["NSResourceName"] = NibString.intern(name)
    obj["NSClassName"] = NibString.intern("NSImage")
    res = ctx.imageResources.get(name)
    catalog = ctx.imageCatalog.get(name)
    is_system = name.startswith("NS") or catalog == "system"
    if catalog:
        obj["NSCatalogName"] = NibString.intern(catalog)
    if is_system:
        obj["IBNamespaceID"] = NibString.intern("system")
    else:
        obj["IBNamespaceID"] = NibNil()
    if is_system and ctx.isStoryboard:
        size_str = "{32, 32}"
    elif catalog == "system":
        size_str = "{32, 32}"
    elif res and is_system:
        w = min(int(float(res[0])), 32)
        h = min(int(float(res[1])), 32)
        size_str = f"{{{w}, {h}}}"
    elif res:
        size_str = f"{{{res[0]}, {res[1]}}}"
    else:
        size_str = "{32, 32}"
    design_size = NibObject("NSValue", obj)
    design_size["NS.sizeval"] = NibString.intern(size_str)
    design_size["NS.special"] = 2
    obj["IBDesignSize"] = design_size
    obj["IBDesignImageConfiguration"] = NibNil()
    return obj

def _apply_plist_color(color: NibObject, parent: NibObject, plist_objects: list) -> None:
    """Apply extended color info from the plist if available."""
    for o in plist_objects:
        if isinstance(o, dict) and "NSComponents" in o and "NSCustomColorSpace" in o:
            if isinstance(o.get("NSComponents"), bytes):
                color["NSComponents"] = NibInlineString(o["NSComponents"])
            cs_uid = o.get("NSCustomColorSpace")
            if cs_uid is not None and hasattr(cs_uid, 'data'):
                cs_obj = plist_objects[cs_uid.data]
                if isinstance(cs_obj, dict):
                    cs = NibObject("NSColorSpace", parent)
                    if "NSID" in cs_obj:
                        cs["NSID"] = cs_obj["NSID"]
                    if "NSModel" in cs_obj:
                        cs["NSModel"] = cs_obj["NSModel"]
                    icc_uid = cs_obj.get("NSICC")
                    if icc_uid is not None and hasattr(icc_uid, 'data'):
                        icc_data = plist_objects[icc_uid.data]
                        if isinstance(icc_data, bytes):
                            cs["NSICC"] = NibData(icc_data)
                    color["NSCustomColorSpace"] = cs
            if "NSWhite" in o and isinstance(o["NSWhite"], bytes):
                white_val = o["NSWhite"]
                if white_val.startswith(b"0"):
                    color["NSLinearExposure"] = NibInlineString(b"1")
            break

def make_inline_image(name: str, parent: NibObject, ctx: "ArchiveContext") -> NibObject:
    """Build an inline NSImage with embedded TIFF data, falling back to make_image
    (NSCustomResource) for system images or images without bitmap data."""
    res = ctx.imageResources.get(name)
    tiff_data = ctx.imageData.get(name)
    if res is None or name.startswith("NS") or tiff_data is None:
        return make_image(name, parent, ctx)
    plist_info = ctx.imagePlistData.get(name, {})
    tiff_reps = plist_info.get("tiff_reps", [tiff_data])
    plist_objects = plist_info.get("plist_objects", [])

    image_flags = 0x20c00000
    image_size = f"{{{res[0]}, {res[1]}}}"
    if len(plist_objects) > 1 and isinstance(plist_objects[1], dict):
        root_obj = plist_objects[1]
        if "NSImageFlags" in root_obj:
            image_flags = root_obj["NSImageFlags"]
        ns_size_uid = root_obj.get("NSSize")
        if ns_size_uid is not None and hasattr(ns_size_uid, 'data'):
            size_str = plist_objects[ns_size_uid.data]
            if isinstance(size_str, str):
                image_size = size_str

    obj = NibObject("NSImage", parent)
    obj["NSImageFlags"] = image_flags
    obj["NSSize"] = NibString.intern(image_size)

    rep_arrays = []
    for tiff in tiff_reps:
        bitmap_rep = NibObject("NSBitmapImageRep", obj)
        bitmap_rep["NSTIFFRepresentation"] = NibData(tiff)
        bitmap_rep["NSInternalLayoutDirection"] = 0
        num_zero = NibObject("NSNumber", obj)
        num_zero["NS.intval"] = 0
        rep_arrays.append(NibList([num_zero, bitmap_rep]))
    obj["NSReps"] = NibMutableList(rep_arrays)

    color = NibObject("NSColor", obj)
    color["NSColorSpace"] = 3
    color["NSWhite"] = NibInlineString(b"0 0\x00")
    _apply_plist_color(color, obj, plist_objects)
    obj["NSColor"] = color
    obj["NSResizingMode"] = 0
    obj["NSTintColor"] = NibNil()
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

_SYSTEM_COLOR_TABLE: dict[str, tuple] = {
    # name: (kind, *args)
    # gray:        (components, white)
    # rgb:         (components, rgb)
    # custom_gray: (sub_name, components, white)
    # custom_rgb:  (sub_name, components, rgb)
    'controlColor':              ('gray', b'0.6666666667 1', b'0.602715373\x00'),
    'controlTextColor':          ('gray', b'0 1', b'0\x00'),
    'controlBackgroundColor':    ('gray', b'0.6666666667 1', b'0.602715373\x00'),
    'textColor':                 ('gray', b'0 1', b'0\x00'),
    'textBackgroundColor':       ('gray', b'1 1', b'1\x00'),
    'labelColor':                ('gray', b'0 1', b'0\x00'),
    'selectedTextBackgroundColor': ('gray', b'0.6666666667 1', b'0.602715373\x00'),
    'selectedTextColor':         ('gray', b'0 1', b'0\x00'),
    'gridColor':                 ('gray', b'0.5 1', b'0.4246723652\x00'),
    'headerTextColor':           ('gray', b'0 1', b'0\x00'),
    'headerColor':               ('gray', b'1 1', b'1\x00'),
    'windowBackgroundColor':     ('gray', b'0.5 1', b'0.4246723652\x00'),
    'secondaryLabelColor':       ('gray', b'0.3333333333 1', b'0.2637968361\x00'),
    'disabledControlTextColor':  ('gray', b'0.3333333333 1', b'0.2637968361\x00'),
    'linkColor':                 ('rgb', '0 0 1 1', b'0 0 0.9981992245\x00'),
    'systemRedColor':            ('rgb', b'1 0 0 1', b'0.9859541655 0 0.02694000863\x00'),
    'controlAccentColor':        ('rgb', b'0 0 1 1', b'0 0 0.9981992245\x00'),
    'textInsertionPointColor':   ('custom_rgb', 'systemBlueColor', '0 0 1 1', b'0 0 0.9981992245\x00'),
    '_sourceListBackgroundColor': ('custom_gray', 'controlBackgroundColor', '0.6666666667 1', b'0.602715373\x00'),
}

def _system_gray_color(name, components, white):
    return NibObject('NSColor', None, {
        'NSCatalogName': NibString.intern('System'),
        'NSColor': NibObject('NSColor', None, {
            'NSColorSpace': 3,
            'NSComponents': NibInlineString(components),
            'NSCustomColorSpace': GENERIC_GREY_COLOR_SPACE,
            'NSWhite': NibInlineString(white),
            'NSLinearExposure': NibInlineString(b'1'),
            }),
        'NSColorName': NibString.intern(name),
        'NSColorSpace': 6,
        })

def _system_rgb_color(name, components, rgb):
    return NibObject("NSColor", None, {
        "NSCatalogName": NibString.intern("System"),
        "NSColorName": NibString.intern(name),
        "NSColorSpace": 6,
        "NSColor": NibObject("NSColor", None, {
            "NSColorSpace": 1,
            "NSComponents": NibInlineString(components),
            "NSRGB": NibInlineString(rgb),
            "NSCustomColorSpace": RGB_COLOR_SPACE,
            "NSLinearExposure": NibInlineString(b'1'),
        }),
    })

def _system_custom_gray_color(name, sub_name, components, white):
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
                "NSColorSpace": 3,
                "NSWhite": NibInlineString(white),
                "NSCustomColorSpace": GENERIC_GREY_COLOR_SPACE,
                "NSLinearExposure": NibInlineString(b'1'),
            }),
        })
    })

def _system_custom_rgb_color(name, sub_name, components, rgb):
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
                "NSLinearExposure": NibInlineString(b'1'),
            }),
        })
    })

_SYSTEM_COLOR_BUILDERS = {
    'gray': _system_gray_color,
    'rgb': _system_rgb_color,
    'custom_gray': _system_custom_gray_color,
    'custom_rgb': _system_custom_rgb_color,
}

def makeSystemColor(name):
    entry = _SYSTEM_COLOR_TABLE.get(name)
    if entry is None:
        raise Exception(f"unknown name {name}")
    kind, *args = entry
    return _SYSTEM_COLOR_BUILDERS[kind](name, *args)

def design_size_for_image(name):
    if name == "NSAddTemplate":
        return "{18, 16}"
    elif name == "NSRemoveTemplate":
        return "{18, 4}"
    elif name == "NSAdvanced":
        return "{32, 32}"
    elif name == "NSGoLeftTemplate":
        return "{12, 16}"
    elif name == "NSGoRightTemplate":
        return "{12, 16}"
    else:
        raise Exception(f"unknown image resource '{name}'")

@dataclass
class PropSchema:
    prop: str
    attrib: Optional[str] = None
    const: Optional[Any] = None
    default: Optional[Any] = None
    map: Optional[dict[str | None, Any]] = None
    filter: Optional[Callable[..., Any]] = None
    skip_default: Optional[bool] = True
    or_mask: Optional[int] = None

def handle_props(_ctx: ArchiveContext, elem: Element, obj: NibObject, props: list[PropSchema]) -> None:
    for prop in props:
        is_default = False
        if prop.const is not None:
            val = prop.const
        elif prop.or_mask is not None:
            do_set = False
            if prop.map is not None:
                if prop.map[elem.attrib.get(prop.attrib, prop.default)]:
                    do_set = True
            else:
                do_set = True
            if do_set:
                val = obj.get(prop.prop) or 0
                val |= prop.or_mask
            else:
                continue
        elif prop.map is not None:
            try:
                val = prop.map[elem.attrib.get(prop.attrib, prop.default)]
            except KeyError:
                raise Exception(f"Not found key '{elem.attrib.get(prop.attrib, prop.default)}' for {prop}")
            is_default = (prop.default in prop.map and val == prop.map[prop.default])
        elif prop.attrib is not None:
            is_default = elem.attrib.get(prop.attrib, prop.default) == prop.default
            val = elem.attrib.get(prop.attrib, prop.default if prop.default is not None else NibNil())
        elif prop.default is not None:
            if obj.get(prop.prop) is None:
                obj[prop.prop] = prop.default
            continue
        else:
            raise Exception("don't know what to do with prop")

        if prop.filter:
            val = prop.filter(val)

        if ((is_default and not prop.skip_default) or (not is_default)) and val is not None:
            obj[prop.prop] = val

MAP_YES_NO = {
    "YES": True,
    "NO": False,
}

MAP_FOCUS_RING = {"none": vFlags.FOCUS_RING_NONE, "exterior": vFlags.FOCUS_RING_EXTERIOR}

MAP_TABLE_STYLE = {
    None: None,
    "fullWidth": 1,
    "inset": 2,
    "sourceList": 3,
    "plain": 4,
}

MAP_TABLE_HIGHLIGHT_STYLE = {
    None: None,
    "sourceList": 1,
}

def hugging_priority_string(h, v) -> NibString:
    return NibString.intern(f"{{{h}, {v}}}")

def point_string(x, y) -> NibString:
    return NibString.intern(f"{{{x}, {y}}}")

def rect_string(x, y, w, h) -> NibString:
    return NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")
