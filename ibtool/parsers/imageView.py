from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList
from ..constants import vFlags
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, default_drag_types, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSImageView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlContinuous"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSDragTypes"] = default_drag_types()
    obj["NSEditable"] = True
    obj["NSEnabled"] = True
    obj["NSImageViewPlaceholderPrecedence"] = 0
    obj["NSControlSendActionMask"] = 4
    obj.setIfEmpty("NSSubviews", NibMutableList([]))
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    return obj

