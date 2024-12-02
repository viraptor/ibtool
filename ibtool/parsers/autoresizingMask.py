from ..models import ArchiveContext, XibObject
from xml.etree.ElementTree import Element
from ..constants import vFlags

def parse(_ctx: ArchiveContext, elem: Element, parent: XibObject) -> None:
    flexibleMaxX = vFlags.MAX_X_MARGIN if elem.attrib.get("flexibleMaxX", "NO") == "YES" else 0
    flexibleMaxY = vFlags.MAX_Y_MARGIN if elem.attrib.get("flexibleMaxY", "NO") == "YES" else 0
    flexibleMinX = vFlags.MIN_X_MARGIN if elem.attrib.get("flexibleMinX", "NO") == "YES" else 0
    flexibleMinY = vFlags.MIN_Y_MARGIN if elem.attrib.get("flexibleMinY", "NO") == "YES" else 0
    widthSizable = vFlags.WIDTH_SIZABLE if elem.attrib.get("widthSizable", "NO") == "YES" else 0
    heightSizable = vFlags.HEIGHT_SIZABLE if elem.attrib.get("heightSizable", "NO") == "YES" else 0
    parent.flagsOr("NSvFlags", flexibleMaxX | flexibleMaxY | flexibleMinX | flexibleMinY | widthSizable | heightSizable)
    parent.extraContext["parsed_autoresizing"] = {
        "flexibleMaxX": bool(flexibleMaxX),
        "flexibleMaxY": bool(flexibleMaxY),
        "flexibleMinX": bool(flexibleMinX),
        "flexibleMinY": bool(flexibleMinY),
        "widthSizable": bool(widthSizable),
        "heightSizable": bool(heightSizable),
    }
