from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableSet, NibString
from ..parsers.helpers import make_xib_object
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element
from typing import Optional
from ..constants import vFlags, CONTROL_SIZE_MAP, CONTROL_SIZE_MAP2

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSColorWell", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    obj["NSNextResponder"] = obj.xib_parent()
    obj.setIfEmpty("NSFrame", NibNil())
    obj["NSEnabled"] = True
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    obj["NSControlUsesSingleLineMode"] = False
    obj.setIfEmpty("NSControlLineBreakMode", 0)
    obj["NSControlWritingDirection"] = 0
    obj["NSControlSendActionMask"] = 4
    obj["NSIsBordered"] = True
    obj["NSControlTextAlignment"] = 0
    control_size = elem.attrib.get("controlSize")
    obj["NSControlSize"] = CONTROL_SIZE_MAP[control_size]
    obj["NSControlSize2"] = CONTROL_SIZE_MAP2[control_size]
    obj["NSDragTypes"] = NibMutableSet([
        NibString.intern("NSColor pasteboard type")
    ])
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    return obj

