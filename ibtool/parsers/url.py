from ..models import ArchiveContext
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional["NibObject"]) -> None:
    key = elem.attrib.get("key")
    url_string = elem.attrib.get("string", "")
    if key == "url" and parent is not None:
        parent.extraContext["url_string"] = url_string
