from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from .helpers import __xibparser_cell_flags, __xibparser_cell_options, handle_props, PropSchema
from ..parsers_base import parse_children

DATE_PICKER_STYLE_MAP = {
    "textFieldAndStepper": 0,
    "clockAndCalendar": 1,
    "textField": 2,
}

DATE_PICKER_MODE_MAP = {
    "single": 0,
    "range": 1,
}

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSDatePickerCell", elem, parent)
    ctx.extraNibObjects.append(obj)

    key = elem.attrib.get("key")
    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)

        obj["NSSupport"] = NibNil()
        obj["NSControlView"] = obj.xib_parent()
        obj["NSDatePickerUseCurrentDateDuringDecoding"] = False
        obj["NSTimeInterval"] = 0.0

        parse_children(ctx, elem, obj)
        parent["NSCell"] = obj

    return obj
