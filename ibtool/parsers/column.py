from ..models import ArchiveContext, NibObject, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> list[NibObject]:
    assert parent is not None
    views = parse_children(ctx, elem, parent)
    return views
