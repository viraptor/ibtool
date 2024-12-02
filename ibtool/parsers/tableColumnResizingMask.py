from ..models import ArchiveContext, XibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: XibObject) -> None:
    assert parent.originalclassname() == "NSTableColumn"
    assert elem.attrib.get("key") == "resizingMask"

    resize_with_table = elem.attrib.get("resizeWithTable", "NO") == "YES"
    if resize_with_table:
        parent["NSResizingMask"] = 1
        parent["NSIsResizeable"] = True
