from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSUserDefaultsController", elem, parent, False)

    parse_children(ctx, elem, obj)

    if elem.attrib.get("representsSharedInstance") == "YES":
        obj["NSSharedInstance"] = True
    else:
        obj["NSAppliesImmediately"] = elem.attrib.get("appliesImmediately", "YES") != "NO"

    return obj
