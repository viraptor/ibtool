# xcode's broken - this is to catch:
# <nil key="backgroundColor"/>

from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert elem.tag == "nil", elem.tag
    assert elem.attrib == {'key': 'backgroundColor'}, elem.attrib
