from ..models import ArchiveContext, NibObject, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    if parent is not None:
        parent["NSStackViewEdgeInsets.top"] = NibFloat(float(elem.attrib.get("top", "0")))
        parent["NSStackViewEdgeInsets.left"] = NibFloat(float(elem.attrib.get("left", "0")))
        parent["NSStackViewEdgeInsets.bottom"] = NibFloat(float(elem.attrib.get("bottom", "0")))
        parent["NSStackViewEdgeInsets.right"] = NibFloat(float(elem.attrib.get("right", "0")))
