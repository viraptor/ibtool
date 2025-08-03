from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSlider", elem, parent)

    parse_children(ctx, elem, obj)
    
    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSEnabled", attrib="enabled", default="YES", map=MAP_YES_NO, skip_default=False),
        PropSchema(prop="NSSubviews", const=NibMutableList()),
        PropSchema(prop="NSSuperview", const=obj.xib_parent()),
        PropSchema(prop="NSControlSendActionMask", const=70),
        PropSchema(prop="NSControlUsesSingleLineMode", const=False),
        PropSchema(prop="NSAllowsLogicalLayoutDirection", const=False),
    ])

    return obj
