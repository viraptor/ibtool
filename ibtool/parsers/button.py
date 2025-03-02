from ..models import ArchiveContext, NibObject, XibObject, NibNil
from ..parsers.helpers import make_xib_object
from ..parsers_base import parse_children
from .helpers import _xibparser_common_translate_autoresizing
from xml.etree.ElementTree import Element
from typing import Optional
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSButton", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj["NSNextResponder"] = obj.xib_parent()
    obj.setIfEmpty("NSFrame", NibNil())
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    obj["NSControlUsesSingleLineMode"] = False
    obj.setIfEmpty("NSControlLineBreakMode", 0)
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    return obj

