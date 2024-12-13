from ..models import ArchiveContext, NibObject, XibObject, NibString, XibId, NibNil
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSCustomFormatter", elem, parent)

    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    obj.setIfEmpty("NSFrame", NibNil())

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
