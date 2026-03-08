from ..models import ArchiveContext, NibObject, XibObject, NibNil
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSDrawer", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSDelegate", const=NibNil()),
        PropSchema(prop="NSLeadingOffset", default=0.0, attrib="leadingOffset", filter=float, skip_default=False),
        PropSchema(prop="NSTrailingOffset", attrib="trailingOffset", filter=float),
        PropSchema(prop="NSNextResponder", const=NibNil()),
        PropSchema(prop="NSNibTouchBar", const=NibNil()),
        PropSchema(prop="NSParentWindow", const=NibNil()),
        PropSchema(prop="NSPreferredEdge", attrib="preferredEdge", default="maxX", map={"minX": 0, "minY": 1, "maxX": 2, "maxY": 3}, skip_default=False),
    ])

    return obj
