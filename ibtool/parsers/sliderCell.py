from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, __xibparser_cell_options, handle_props, PropSchema
from ..parsers_base import parse_children
from ..constants import CellFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSliderCell", elem, parent, False)

    parse_children(ctx, elem, obj)

    __xibparser_cell_options(elem, obj, parent)

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSTickMarkPosition", attrib="tickMarkPosition", map={"above": 1}),
        PropSchema(prop="NSValue", attrib="doubleValue", filter=float),
        PropSchema(prop="NSMaxValue", attrib="maxValue", filter=float, default=1.0),
        PropSchema(prop="NSMinValue", attrib="minValue", filter=float, default=0.0),
        PropSchema(prop="NSVertical", const=False), # TODO
        PropSchema(prop="NSNumberOfTickMarks", const=0), # TODO
        PropSchema(prop="NSAllowsTickMarkValuesOnly", const=False), # TODO
        PropSchema(prop="NSAltIncValue", const=0.0), # TODO
        PropSchema(prop="NSControlView", const=parent),
        PropSchema(prop="NSCellFlags", or_mask=CellFlags.ACTION_ON_MOUSE_DOWN | CellFlags.ACTION_ON_MOUSE_DRAG),
    ])

    parent["NSCell"] = obj

    return obj
