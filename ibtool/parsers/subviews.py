from ..models import ArchiveContext, NibObject, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    views = parse_children(ctx, elem, parent)
    if parent.originalclassname() == "NSCustomView":
        parent["NSSubviews"] = NibMutableList(reversed(views))
    else:
        parent["NSSubviews"] = NibMutableList(views)
