from ..models import ArchiveContext, NibObject, NibString, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    if parent is None:
        return
    strings = [NibString.intern(s.text) for s in elem.findall("string") if s.text]
    parent["NSDeclaredKeys"] = NibMutableList(strings)
