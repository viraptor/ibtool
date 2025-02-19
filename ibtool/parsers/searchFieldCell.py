from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibMutableDictionary, NibNSNumber, NibInlineString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_options
from ..parsers_base import parse_children
from ..constants import ButtonFlags, CellFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None
    assert parent.originalclassname() == "NSSearchField"
    obj = make_xib_object(ctx, "NSSearchFieldCell", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)
    __xibparser_cell_options(elem, obj, parent)
    obj["NSAutomaticTextCompletionStored"] = True
    obj["NSCancelButtonCell"] = NibObject("NSButtonCell", None, {
        "NSAccessibilityOverriddenAttributes": NibMutableList([
            NibMutableDictionary([
                NibString.intern("AXDescription"),
                NibString.intern("cancel"),
                NibString.intern("NSAccessibilityEncodedAttributesValueType"),
                NibNSNumber(1),
            ])
        ]),
        "NSAction": NibString.intern("_searchFieldCancel:"),
        "NSAuxButtonType": 5,
        "NSBezelStyle": 0,
        "NSButtonFlags": ButtonFlags.HIGHLIGHT_CONTENTS_CELL | ButtonFlags.INSET_2 | ButtonFlags.IMAGE_ONLY,
        "NSButtonFlags2": 0,
        "NSCellFlags": CellFlags.STATE_ON,
        "NSCellFlags2": 0,
        "NSControlSize2": 0,
        "NSKeyEquivalent": NibString.intern(''),
        "NSPeriodicDelay": 400,
        "NSPeriodicInterval": 75,
        "NSTarget": obj,
        "NSControlView": obj.xib_parent(),
    })
    obj["NSSearchButtonCell"] = NibObject("NSButtonCell", None, {
        "NSAction": NibString.intern("_searchFieldSearch:"),
        "NSAuxButtonType": 5,
        "NSBezelStyle": 0,
        "NSButtonFlags": ButtonFlags.HIGHLIGHT_CONTENTS_CELL | ButtonFlags.INSET_2 | ButtonFlags.IMAGE_ONLY,
        "NSButtonFlags2": 0,
        "NSCellFlags": 0,
        "NSCellFlags2": 0,
        "NSControlSize2": 0,
        "NSKeyEquivalent": NibString.intern(''),
        "NSPeriodicDelay": 400,
        "NSPeriodicInterval": 75,
        "NSTarget": obj,
        "NSContents": NibString.intern('search'),
        "NSControlView": obj.xib_parent(),
    })
    if parent.extraContext.get("allowsCharacterPickerTouchBarItem"):
        obj["NSCharacterPickerEnabled"] = True
    obj["NSContents"] = NibString.intern('')
    obj["NSControlView"] = parent
    obj["NSMaximumRecents"] = 255
    obj["NSTextBezelStyle"] = 1
    obj["NSSearchFieldFlags"] = NibInlineString(b"\x16\x00\x00\x00")
    if placeholder_string := elem.attrib.get("placeholderString"):
        obj["NSPlaceholderString"] = placeholder_string

    parent["NSCell"] = obj
    return obj
