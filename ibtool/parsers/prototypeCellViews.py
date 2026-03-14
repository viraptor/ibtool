from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    children = parse_children(ctx, elem, parent)

    if len(children) == 1:
        parent.extraContext["prototypeCellView"] = children[0]
    elif len(children) > 1:
        parent.extraContext["prototypeCellViews"] = children
