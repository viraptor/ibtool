from ..models import ArchiveContext, NibObject, NibMutableList, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent.originalclassname() in ("NSOutlineView", "NSTableView")

    columns = parse_children(ctx, elem, parent)

    # Auto-generate identifiers for columns that don't have explicit ones
    for i, col in enumerate(columns):
        ident = col.get("NSIdentifier")
        if isinstance(ident, NibString) and ident._text == "":
            col["NSIdentifier"] = NibString.intern(f"AutomaticTableColumnIdentifier.{i}")

    parent["NSTableColumns"] = NibMutableList(columns)
