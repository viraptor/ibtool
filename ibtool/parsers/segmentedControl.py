from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSSegmentedControl", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    
    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)

    obj["NSEnabled"] = elem.attrib.get("enabled", "YES") == "YES"
    obj["NSControlSendActionMask"] = 4
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSSubviews"] = NibMutableList([])
    obj["NSvFlags"] = vFlags.DEFAULT_VFLAGS_AUTOLAYOUT

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    return obj
