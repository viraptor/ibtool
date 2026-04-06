from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children
from ..constants import sFlagsScroller

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSScroller", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    obj["NSNextResponder"] = obj.xib_parent()
    obj["NSAction"] = NibString.intern("_doScroller:")
    obj["NSControlAction"] = NibString.intern("_doScroller:")
    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    obj["NSControlContinuous"] = False
    obj["NSControlSendActionMask"] = 4
    obj["NSControlSize"] = 0
    obj["NSControlTarget"] = parent
    obj["NSTarget"] = parent
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = 0
    obj["NSControlTextAlignment"] = 0
    obj["NSControlLineBreakMode"] = 0
    if ctx.toolsVersion >= 11762 and elem.attrib.get("wantsLayer") == "YES":
        obj["NSViewIsLayerTreeHost"] = True
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    if (cur_value := elem.attrib.get("doubleValue")) is not None:
        obj["NSCurValue"] = float(cur_value)
    s_flags = 0
    s_flags |= {
        None: sFlagsScroller.CONTROL_SIZE_REGULAR,
        "small": sFlagsScroller.CONTROL_SIZE_SMALL,
        "mini": sFlagsScroller.CONTROL_SIZE_MINI,
        "regular": sFlagsScroller.CONTROL_SIZE_REGULAR,
        "large": sFlagsScroller.CONTROL_SIZE_LARGE,
        "extraLarge": sFlagsScroller.CONTROL_SIZE_EXTRA_LARGE,
    }.get(elem.attrib.get("controlSize"), 0)
    # Store the scroller width and standard width for scrollView frame computation
    frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
    if frame:
        obj.extraContext["scroller_width"] = frame[2] if len(frame) == 4 else frame[0]
    obj.extraContext["standard_scroller_width"] = {
        "small": 13, "mini": 11,
    }.get(elem.attrib.get("controlSize"), 17)

    if elem.attrib["horizontal"] == "YES":
        parent["NSHScroller"] = obj
        s_flags |= sFlagsScroller.HORIZONTAL
    else:
        parent["NSVScroller"] = obj
    obj.setIfNotDefault("NSsFlags", s_flags, 0)
    return obj
