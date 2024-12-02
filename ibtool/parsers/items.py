from ..models import ArchiveContext, NibObject, NibMutableList
from xml.etree.ElementTree import Element
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() == "NSMenu"
    children = parse_children(ctx, elem, parent)
    parent["NSMenuItems"] = NibMutableList(children)
