from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    if elem.attrib["key"] == "maxSize":
        parent["NSMaxSize"] = f'{{{elem.attrib["width"]}, {elem.attrib["height"]}}}'
    parent.extraContext[elem.attrib["key"]] = (elem.attrib["width"], elem.attrib["height"])
