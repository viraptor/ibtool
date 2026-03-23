from ..models import ArchiveContext, NibObject, NibMutableList, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent.originalclassname() in ("NSOutlineView", "NSTableView")

    # Pre-compute auto identifiers for columns with empty identifier,
    # so cell view template compilation uses the correct identifier.
    for i, col_elem in enumerate(elem):
        if col_elem.tag == "tableColumn" and col_elem.attrib.get("identifier", "") == "":
            col_elem.set("_autoIdentifier", f"AutomaticTableColumnIdentifier.{i}")

    columns = parse_children(ctx, elem, parent)

    for i, col in enumerate(columns):
        ident = col.get("NSIdentifier")
        if isinstance(ident, NibString) and ident._text == "":
            col["NSIdentifier"] = NibString.intern(f"AutomaticTableColumnIdentifier.{i}")

    parent["NSTableColumns"] = NibMutableList(columns)
