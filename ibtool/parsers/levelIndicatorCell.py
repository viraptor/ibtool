from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_options, __xibparser_cell_flags
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    key = elem.attrib["key"]

    obj = make_xib_object(ctx, "NSLevelIndicatorCell", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)

    INDICATOR_STYLE_MAP = {
        "relevancy": 0,
        "continuousCapacity": 1,
        "discreteCapacity": 2,
        "rating": 3,
    }

    if key == "dataCell":
        __xibparser_cell_flags(elem, obj, parent)
        table_view = parent.get("NSTableView") if parent.originalclassname() == "NSTableColumn" else parent
        obj["NSControlView"] = table_view
        if (cv := elem.attrib.get("criticalValue")) is not None:
            obj["NSCriticalValue"] = float(cv)
        if (wv := elem.attrib.get("warningValue")) is not None:
            obj["NSWarningValue"] = float(wv)
        if (mv := elem.attrib.get("maxValue")) is not None:
            obj["NSMaxValue"] = float(mv)
        obj["NSIndicatorStyle"] = INDICATOR_STYLE_MAP.get(elem.attrib.get("levelIndicatorStyle"), 0)
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

