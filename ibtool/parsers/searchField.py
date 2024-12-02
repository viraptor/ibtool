from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSearchField", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    if elem.attrib.get('allowsCharacterPickerTouchBarItem') == "YES":
        obj.extraContext["allowsCharacterPickerTouchBarItem"] = True

    parse_children(ctx, elem, obj)
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlContinuous"] = False
    obj["NSEnabled"] = True
    obj["NSControlSendActionMask"] = 4
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = -1
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    obj["NSvFlags"] = vFlags.DEFAULT_VFLAGS_AUTOLAYOUT

    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    return obj
