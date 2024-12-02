from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() in ("NSButtonCell", "NSPopUpButtonCell"), parent.originalclassname()
    maskmap = {
        "doesNotDimImage": 1<<12,
        "lightByGray": 1<<25,
        "lightByBackground": 1<<26,
        "lightByContents": 1<<27,
        "changeGray": 1<<28,
        "changeBackground": 1<<29,
        "changeContents": 1<<30,
        "pushIn": 0xffffffff00000000 + (1<<31),
    }
    value = sum((elem.attrib.get(attr) == "YES") * val for attr, val in maskmap.items())
    parent.flagsOr("NSButtonFlags", value)
