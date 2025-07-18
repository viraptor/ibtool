from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSearchField", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    if elem.attrib.get('allowsCharacterPickerTouchBarItem') == "YES":
        obj.extraContext["allowsCharacterPickerTouchBarItem"] = True

    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSEnabled"] = True
    obj["NSControlSendActionMask"] = 4
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    obj["NSAllowsWritingTools"] = False
    obj["NSvFlags"] = vFlags.DEFAULT_VFLAGS_AUTOLAYOUT

    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    return obj
