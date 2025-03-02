from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord, NibFloat, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import design_size_for_image
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: XibObject) -> NibObject:
    assert parent is not None

    obj = NibObject("NSSegmentItem", parent)
    if width := elem.attrib.get("width"):
        obj["NSSegmentItemWidth"] = float(width)
    
    if not any(x.attrib.get("key") == "label" for x in elem.findall("nil")):
        obj["NSSegmentItemLabel"] = elem.attrib.get("label", NibString.intern("")) 

    obj.setIfNotDefault("NSSegmentItemSelected", elem.attrib.get("selected", "NO") == "YES", False)
    obj["NSSegmentItemImageScaling"] = {
        None: 0,
        "proportionallyUpOrDown": 3,
        "axesIndependently": 1,
        "none": 2,
    }[elem.attrib.get("imageScaling")]
    if image := elem.attrib.get("image"):
        obj["NSSegmentItemImage"] = NibObject("NSCustomResource", obj, {
            "NSClassName": "NSImage",
            "NSResourceName": elem.attrib.get("image"),
            "IBNamespaceID": "system",
            "IBDesignSize": NibObject("NSValue", obj, {
                "NS.sizeval": design_size_for_image(elem.attrib.get("image")),
                "NS.special": 2,
            }),
            "IBDesignImageConfiguration": NibNil(),
        })
    if (tag := elem.attrib.get("tag")):
        obj["NSSegmentItemTag"] = int(tag)
    return obj
