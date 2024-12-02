from ..models import ArchiveContext, NibObject, XibObject, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import __xibparser_cell_options, make_system_image
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None
    assert parent.originalclassname() in ("NSImageView", "NSTableColumn"), parent.originalclassname()

    key = elem.attrib["key"]

    obj = XibObject(ctx, "NSImageCell", elem, parent)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    parse_children(ctx, elem, obj)

    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)

        alignment_value = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
        obj["NSAlign"] = alignment_value
        obj["NSAnimates"] = elem.attrib.get("animates", "NO") == "YES"
        obj["NSContents"] = NibNil()
        obj["NSControlView"] = parent
        obj["NSScale"] = {
            "proportionallyDown": 0,
            "axesIndependently": 1,
            "none": 2,
            "proportionallyUpOrDown": 3,
        }[elem.attrib.get("imageScaling", "none")]
        obj["NSStyle"] = 0
        if image_name := elem.attrib.get("image"):
            obj["NSContents"] = make_system_image(image_name, obj)
        parent["NSCell"] = obj

    elif key == "dataCell":
        parent["NSDataCell"] = obj

    else:
        raise Exception(f"Unknown key for imageCell: {key}")
        

    return obj

