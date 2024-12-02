from ..models import ArchiveContext, NibObject, XibId, NibString
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    etype = elem.attrib.get("eventType")

    maskmap = {
        None: None,
        "touchDown": 1 << 0,
        "touchDownRepeat": 1 << 1,
        "touchDragInside": 1 << 2,
        "touchDragOutside": 1 << 3,
        "touchDragEnter": 1 << 4,
        "touchDragExit": 1 << 5,
        "touchUpInside": 1 << 6,
        "touchUpOutside": 1 << 7,
        "touchCancel": 1 << 8,
        "valueChanged": 1 << 12,
        "editingDidBegin": 1 << 16,
        "editingChanged": 1 << 17,
        "editingDidEnd": 1 << 18,
        "editingDidEndOnExit": 1 << 19,
    }

    mask = maskmap[etype]

    obj = NibObject("NSNibControlConnector", parent)
    obj["NSLabel"] = elem.attrib["selector"]
    obj["NSSource"] = parent
    obj["NSDestination"] = XibId(elem.attrib.get("target"))
    if trigger := elem.attrib.get("trigger"):
        obj["NSTrigger"] = NibString.intern(trigger)
        obj.setclassname("NSNibAuxiliaryActionConnector")
    else:
        obj["NSEventMask"] = mask # TODO

    ctx.connections.append(obj)
