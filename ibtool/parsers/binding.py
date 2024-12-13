from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None

    destination = elem.attrib.get("destination")
    name = elem.attrib.get("name")
    keyPath = elem.attrib.get("keyPath")
    previousBinding = elem.attrib.get("previousBinding")

    data = [x for x in elem.iter("dictionary")]
    assert len(data) in (0, 1), len(data)

