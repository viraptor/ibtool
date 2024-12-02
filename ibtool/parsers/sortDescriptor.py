from ..models import ArchiveContext, NibObject, NibProxyObject, XibId
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibProxyObject:
    assert elem.attrib["key"] == "sortDescriptorPrototype"
