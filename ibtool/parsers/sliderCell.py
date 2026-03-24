from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, __xibparser_cell_options, handle_props, PropSchema
from ..parsers_base import parse_children
from ..constants import CellFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSliderCell", elem, parent, False)

    parse_children(ctx, elem, obj)

    __xibparser_cell_options(elem, obj, parent)

    continuous = elem.attrib.get("continuous", "NO") == "YES"
    has_font = elem.find("font") is not None

    props = [
        PropSchema(prop="NSTickMarkPosition", attrib="tickMarkPosition", default="below", map={"above": 1, "below": 0}, skip_default=False),
        PropSchema(prop="NSValue", attrib="doubleValue", default="0", filter=float, skip_default=False),
        PropSchema(prop="NSMaxValue", attrib="maxValue", filter=float, default=1.0, skip_default=False),
        PropSchema(prop="NSMinValue", attrib="minValue", filter=float, default=0.0, skip_default=False),
        PropSchema(prop="NSVertical", const=False), # TODO
        PropSchema(prop="NSNumberOfTickMarks", attrib="numberOfTickMarks", default="0", filter=int, skip_default=False),
        PropSchema(prop="NSAllowsTickMarkValuesOnly", attrib="allowsTickMarkValuesOnly", default="NO", map={"YES": True, "NO": False}, skip_default=False),
        PropSchema(prop="NSAltIncValue", attrib="altIncrementValue", default="0.0", filter=float, skip_default=False),
        PropSchema(prop="NSControlView", const=parent),
    ]
    if has_font:
        props.append(PropSchema(prop="NSCellFlags", or_mask=CellFlags.TYPE_TEXT_CELL))
    if continuous:
        props.append(PropSchema(prop="NSCellFlags", or_mask=CellFlags.ACTION_ON_MOUSE_DOWN | CellFlags.ACTION_ON_MOUSE_DRAG))
    handle_props(ctx, elem, obj, props)

    if identifier := elem.attrib.get("identifier"):
        obj["NSCellIdentifier"] = NibString.intern(identifier)

    parent["NSCell"] = obj

    return obj
