from ..models import ArchiveContext, NibObject, XibObject
from ..constants import WTFlags
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert isinstance(parent, XibObject)
    assert elem.attrib.get("key") == "initialPositionMask"

    struts = {
        "left": elem.attrib.get("leftStrut", "NO") == "YES",
        "right": elem.attrib.get("rightStrut", "NO") == "YES",
        "bottom": elem.attrib.get("bottomStrut", "NO") == "YES",
        "top": elem.attrib.get("topStrut", "NO") == "YES",
    }
    if struts["bottom"] and struts["left"] and struts["top"] and struts["right"]:
        flags = WTFlags.STRUTS_ALL
    elif struts["bottom"] and struts["left"]:
        flags = WTFlags.STRUTS_BOTTOM_LEFT
    elif struts["bottom"] and struts["right"]:
        flags = WTFlags.STRUTS_BOTTOM_RIGHT
    elif struts["top"] and struts["left"]:
        flags = WTFlags.STRUTS_TOP_LEFT
    elif struts["top"] and struts["right"]:
        flags = WTFlags.STRUTS_TOP_RIGHT
    elif struts["left"]:
        flags = WTFlags.STRUTS_LEFT
    elif struts["right"]:
        flags = WTFlags.STRUTS_RIGHT
    elif struts["bottom"]:
        flags = WTFlags.STRUTS_BOTTOM
    elif struts["top"]:
        flags = WTFlags.STRUTS_TOP
    else:
        flags = WTFlags.STRUTS_MASK

    parent.flagsAnd("NSWTFlags", ~WTFlags.STRUTS_MASK) # clear the default
    parent.flagsOr("NSWTFlags", flags)
    parent.extraContext["initialPositionMask"] = struts
    #parent["NSWindowPositionMask"] = value
