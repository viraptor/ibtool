from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element
from typing import Optional

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibObject:
    assert elem.attrib["key"] == "sortDescriptorPrototype"

    obj = NibObject("NSSortDescriptor", parent)
    obj["NSKey"] = NibString.intern(elem.attrib["sortKey"])
    obj["NSAscending"] = elem.attrib.get("ascending", "YES") == "YES"
    obj["NSSelector"] = NibString.intern(elem.attrib["selector"])
    obj["NSReverseNullOrder"] = False
    parent["NSSortDescriptorPrototype"] = obj
    return obj
