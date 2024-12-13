from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None

    description = elem.attrib.get("description")
