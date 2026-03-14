from ..models import ArchiveContext, NibObject, XibId
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    xibid = elem.attrib.get("id")
    if xibid and parent is not None:
        key = elem.attrib.get("key")
        if key == "safeArea":
            ctx.addObject(XibId(xibid), parent)
        elif key == "layoutMargins":
            ctx.addObject(XibId(xibid), parent)
