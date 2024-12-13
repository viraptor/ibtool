from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None
    assert parent.originalclassname() == "NSWindowTemplate", parent.originalclassname()
    assert elem.attrib.get("key") == "collectionBehavior", elem.attrib.get("key")

    can_join_all_spaces = elem.attrib.get("canJoinAllSpaces") == "YES"
    transient = elem.attrib.get("transient") == "YES"
