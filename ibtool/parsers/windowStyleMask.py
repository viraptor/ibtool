from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    maskmap = {
        "titled": 1 << 0,
        "closable": 1 << 1,
        "miniaturizable": 1 << 2,
        "resizable": 1 << 3,
    }
    value = sum((elem.attrib.get(attr, "NO") == "YES") * val for attr, val in maskmap.items())
    parent["NSWindowStyleMask"] = value
