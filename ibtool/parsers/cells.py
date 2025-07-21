from ..models import ArchiveContext, NibObject, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    views = parse_children(ctx, elem, parent)
    parent["NSNumCols"] = len(views)
    if len(views) > 0:
        parent["NSNumRows"] = len(views[0])
    parent["NSCells"] = NibMutableList([cell for column in views for cell in column])
