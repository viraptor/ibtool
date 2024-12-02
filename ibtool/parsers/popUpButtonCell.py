from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_options, __xibparser_button_flags
from ..parsers_base import parse_children
from ..constants import ButtonFlags, CellFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None
    obj = make_xib_object(ctx, "NSPopUpButtonCell", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)
    __xibparser_cell_options(elem, obj, parent)
    obj["NSAlternateContents"] = NibString.intern("")
    obj["NSAltersState"] = True
    obj["NSBezelStyle"] = 13
    obj["NSContents"] = NibString.intern("")
    obj["NSControlView"] = parent
    obj["NSKeyEquivalent"] = NibString.intern("")
    obj["NSPeriodicDelay"] = 400
    obj["NSPeriodicInterval"] = 75
    obj["NSPreferredEdge"] = 1
    obj["NSPullDown"] = True
    __xibparser_button_flags(elem, obj, parent)
    obj.flagsOr("NSButtonFlags", ButtonFlags.IMAGE_ABOVE)
    obj.flagsOr("NSCellFlags", CellFlags.BEZELED)

    obj["NSMenuItemRespectAlignment"] = True

    parent["NSCell"] = obj
    return obj
