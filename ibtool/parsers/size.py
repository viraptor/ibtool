from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    if elem.attrib["key"] == "maxSize":
        parent["NSMaxSize"] = f'{{{elem.attrib["width"]}, {elem.attrib["height"]}}}'
    if elem.attrib["key"] == "intercellSpacing":
        if (width := elem.attrib.get("width")) is not None:
            parent["NSIntercellSpacingWidth"] = float(width)
        if (height := elem.attrib.get("height")) is not None:
            parent["NSIntercellSpacingHeight"] = float(height)
    parent.extraContext[elem.attrib["key"]] = (elem.attrib["width"], elem.attrib["height"])
