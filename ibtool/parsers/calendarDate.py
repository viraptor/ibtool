from . import date
from ..models import ArchiveContext
from xml.etree.ElementTree import Element
from typing import Optional

def parse(ctx: ArchiveContext, elem: Element, parent: Optional["NibObject"]) -> None:
    date.parse(ctx, elem, parent)
