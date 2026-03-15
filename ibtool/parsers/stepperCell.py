from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children
from ..constants import CellFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSStepperCell", elem, parent)
    ctx.extraNibObjects.append(obj)

    parse_children(ctx, elem, obj)

    autorepeat = elem.attrib.get("autorepeat", "YES") == "YES"
    obj.extraContext["autorepeat"] = autorepeat

    if autorepeat:
        cell_flags = CellFlags.ACTION_ON_MOUSE_DOWN | CellFlags.DONT_ACT_ON_MOUSE_UP
        continuous = elem.attrib.get("continuous", "YES") != "NO"
        if continuous:
            cell_flags |= CellFlags.CONTINUOUS
            obj.extraContext["continuous"] = True
        obj["NSCellFlags"] = cell_flags
    else:
        obj["NSCellFlags"] = 0
    obj["NSCellFlags2"] = 0

    obj["NSControlView"] = parent

    obj.setIfNotDefault("NSValue", float(elem.attrib.get("doubleValue", "0")), 0.0)
    obj.setIfNotDefault("NSMinValue", float(elem.attrib.get("minValue", "0")), 0.0)
    obj.setIfNotDefault("NSMaxValue", float(elem.attrib.get("maxValue", "100")), 0.0)
    obj["NSIncrement"] = float(elem.attrib.get("increment", "1"))

    if autorepeat:
        if "valueWraps" in elem.attrib:
            obj["NSValueWraps"] = elem.attrib["valueWraps"] == "YES"
        obj["NSAutorepeat"] = True

    parent["NSCell"] = obj

    return obj
