from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    key = elem.attrib.get("key")
    if key == "date" and parent is not None:
        time_interval = float(elem.attrib.get("timeIntervalSinceReferenceDate", "0"))
        date_obj = NibObject("NSDate")
        date_obj["NS.time"] = time_interval
        if parent.classname() == "NSDatePickerCell":
            parent["NSContents"] = date_obj
        else:
            parent["NSDate"] = date_obj
