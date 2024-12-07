from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTableColumn", elem, parent, view_attributes=False)

    parse_children(ctx, elem, obj)

    obj["NSIdentifier"] = NibString.intern(elem.attrib.get("identifier", ""))
    if max_width := elem.attrib.get("maxWidth"):
        obj["NSMaxWidth"] = float(max_width)
    if min_width := elem.attrib.get("minWidth"):
        obj["NSMinWidth"] = float(min_width)
    obj["NSTableView"] = parent
    if width := elem.attrib.get("width"):
        obj["NSWidth"] = float(width)

    if parent.originalclassname() == "NSTableView":
        parent["NSTableViewArchivedReusableViewsKey"].addItem(NibString.intern(elem.attrib.get("identifier", "")))
        parent["NSTableViewArchivedReusableViewsKey"].addItem(NibObject("NSNib", None, {
            "NSNibFileData": NibNil(), # NibObject("NSData", None, {}),
            "NSNibFileImages": NibNil(),
            "NSNibFileIsKeyed": True,
            "NSNibFileSounds": NibNil(),
            "NSNibFileUseParentBundle": True,
        }))
        obj["NSResizingMask"] = 3 # reason unknown

    return obj
