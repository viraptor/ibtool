from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None
    assert parent.originalclassname() == "NSWindowTemplate", parent.originalclassname()
    assert elem.attrib.get("key") == "collectionBehavior", elem.attrib.get("key")

    value = 0
    if elem.attrib.get("canJoinAllSpaces") == "YES":
        value |= 1
    if elem.attrib.get("transient") == "YES":
        value |= 8
    if elem.attrib.get("ignoresCycle") == "YES":
        value |= 64
    if elem.attrib.get("fullScreenPrimary") == "YES":
        value |= 128
    if value:
        parent["NSWindowCollectionBehavior"] = value
