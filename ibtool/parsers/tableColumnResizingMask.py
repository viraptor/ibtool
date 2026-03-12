from ..models import ArchiveContext, XibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: XibObject) -> None:
    assert parent.originalclassname() == "NSTableColumn"
    assert elem.attrib.get("key") == "resizingMask"

    resizing_mask = 0
    if elem.attrib.get("resizeWithTable", "NO") == "YES":
        resizing_mask |= 1
    if elem.attrib.get("userResizable", "NO") == "YES":
        resizing_mask |= 2
    if resizing_mask:
        parent["NSIsResizeable"] = True
    parent.setIfNotDefault("NSResizingMask", resizing_mask, 0)
