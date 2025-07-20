from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    parent["gridlines"] = int(elem.attrib.get("horizontal") == "YES") + int(elem.attrib.get("vertical") == "YES")*2
