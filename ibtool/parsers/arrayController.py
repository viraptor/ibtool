from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema
from ..parsers_base import parse_children


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSArrayController", elem, parent, False)

    parse_children(ctx, elem, obj)

    obj["_NSManagedProxy"] = NibObject("_NSManagedProxy", None)
    handle_props(ctx, elem, obj, [
        PropSchema("NSFilterRestrictsInsertion", const=True),
        PropSchema("NSClearsFilterPredicateOnInsertion", const=True),
    ])

    return obj
