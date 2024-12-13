from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_options
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    key = elem.attrib["key"]

    obj = make_xib_object(ctx, "NSLevelIndicatorCell", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)

    if key == "dataCell":
        parent["NSDataCell"] = obj

    elif key == "cell":
        parent["NSCell"] = obj
        __xibparser_cell_options(elem, obj, parent)
        obj["NSControlView"] = obj.xib_parent()
        obj["NSCriticalValue"] = float(elem.attrib.get("criticalValue"))
        obj["NSWarningValue"] = float(elem.attrib.get("warningValue"))
        obj["NSMaxValue"] = float(elem.attrib.get("maxValue"))
        obj["NSIndicatorStyle"] = 2

    else:
        raise Exception(f"Unknown key for levelIndicatorCell: {key}")
        

    return obj

