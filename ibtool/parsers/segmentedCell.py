from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, _xibparser_common_translate_autoresizing, __xibparser_cell_options
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    assert parent is not None
    assert parent.originalclassname() in ("NSSegmentedControl"), parent.originalclassname()

    key = elem.attrib["key"]

    obj = XibObject(ctx, "NSSegmentedCell", elem, parent)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    parse_children(ctx, elem, obj)

    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)

        obj["NSControlView"] = parent
        segment_style = elem.attrib.get("style")
        obj["NSSegmentStyle"] = {
            "rounded": 1,
            "texturedRounded": 2,
            "roundRect": 3,
            "texturedSquare": 4,
            "capsule": 5,
            "smallSquare": 6,
            "separated": 9,
        }[segment_style]
        if segment_style == "separated":
            obj["NSSegmentStyleSeparated"] = 1

        tracking_mode = {
            "selectOne": 0,
            "selectAny": 1,
            "momentary": 2,
            "momentaryAccelerator": 3,
        }[elem.attrib.get("trackingMode")]
        obj.setIfNotDefault("NSTrackingMode", tracking_mode, 0)
        
        if tracking_mode in (0, 1):
            for i, seg in enumerate(obj["NSSegmentImages"].items()):
                if seg.get("NSSegmentItemSelected"):
                    obj["NSSelectedSegment"] = i
        obj.setIfEmpty("NSSelectedSegment", -1)

        distribution = {
            "fit": 0,
            "fill": 1,
            "fillEqually": 2,
            "fillProportionally": 2,
        }[elem.attrib.get("segmentDistribution", "fit")]
        obj.setIfNotDefault("NSSegmentDistribution", distribution, None)
        parent["NSCell"] = obj
        return obj
    else:
        raise Exception(f"Unknown key for segmentedCell: {key}")

