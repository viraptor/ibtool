from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element
from typing import Optional

ELEMENT_FLAGS = {
    "yearMonth": 0xc0,
    "yearMonthDay": 0xe0,
    "era": 0x100,
    "year": 0x40,
    "month": 0x80,
    "day": 0x20,
    "hour": 0x4,
    "minute": 0x8,
    "second": 0x10,
    "hourMinute": 0xc,
    "hourMinuteSecond": 0x1c,
    "timeZone": 0x2,
}

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    flags = 0
    for attr, bit in ELEMENT_FLAGS.items():
        if elem.attrib.get(attr) == "YES":
            flags |= bit
    if flags and parent is not None:
        parent["NSDatePickerElements"] = flags
