from ..models import ArchiveContext, XibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: XibObject) -> None:
    key = elem.attrib.get("key")
    w = int(elem.attrib["width"])
    h = int(elem.attrib["height"])
    if key == "contentRect":
        assert parent.originalclassname() == "NSWindowTemplate"
        x = int(elem.attrib["x"])
        y = int(elem.attrib["y"])
        parent.extraContext["NSWindowRect"] = (x, y, w, h)
    elif key == "screenRect":
        assert parent.originalclassname() == "NSWindowTemplate"
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        parent.extraContext["NSScreenRect"] = (x, y, w, h)
    elif key == "frame":
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        if x == 0 and y == 0:
            parent["NSFrameSize"] = "{" + str(w) + ", " + str(h) + "}"
            parent.extraContext["NSFrameSize"] = (w, h)
        else:
            parent["NSFrame"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
            parent.extraContext["NSFrame"] = (x, y, w, h)
    else:
        raise Exception(f"unknown rect key {key}")
