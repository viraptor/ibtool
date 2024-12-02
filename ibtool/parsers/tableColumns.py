from ..models import ArchiveContext, NibObject, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent.originalclassname() in ("NSOutlineView", "NSTableView")

    columns = parse_children(ctx, elem, parent)
    parent["NSTableColumns"] = NibMutableList(columns)
