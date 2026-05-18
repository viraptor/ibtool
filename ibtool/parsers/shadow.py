from ..models import ArchiveContext, NibObject
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert elem.attrib.get("key") == "shadow", elem.attrib.get("key")
    shadow = NibObject("NSShadow", None)
    parse_children(ctx, elem, shadow)
    parent["NSViewShadow"] = shadow
