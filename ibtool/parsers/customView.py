from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from ..constants import vFlags
from .helpers import parse_interfacebuilder_properties, __handle_view_chain, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = XibObject(ctx, "NSCustomView", elem, parent)
    ctx.extraNibObjects.append(obj)
    obj.setrepr(elem)
    obj["NSSuperview"] = obj.xib_parent()
    obj.setIfEmpty("NSClassName", "NSView")

    # Parse these props first, in case any of our children point to us.
    parse_interfacebuilder_properties(ctx, elem, parent, obj)
    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)

    _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(parent is None))
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    if obj.get("NSNextKeyView"):
        del obj["NSNextKeyView"]

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if elem.attrib.get("clipsToBounds") == "YES":
        obj["NSViewClipsToBoundsKeyName"] = True

    return obj

