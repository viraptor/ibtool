from ..models import ArchiveContext, NibObject, XibObject, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSPopUpButton", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlContinuous"] = False
    obj["NSControlSendActionMask"] = 4
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = -1
    obj["NSEnabled"] = True
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
