from .helpers import parse_interfacebuilder_properties, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..models import ArchiveContext, XibObject, NibString
from xml.etree.ElementTree import Element
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: XibObject, **kwargs) -> XibObject:
    obj = XibObject(ctx, "NSView", elem, parent)
    ctx.extraNibObjects.append(obj)
    obj.setrepr(elem)

    key = elem.get("key")
    if key == "contentView":
        if parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
            obj["NSFrameSize"] = NibString.intern("{0, 0}")
        elif parent.originalclassname() == "NSBox":
            parent["NSContentView"] = obj
            obj["NSSuperview"] = parent
        else:
            raise Exception(
                "Unhandled class '%s' to take NSView with key 'contentView'"
                % (parent.originalclassname())
            )
    elif key is None:
        pass
    else:
        raise Exception(f"view in unknown key {key} (parent {parent.repr()})")

    isMainView = key == "view"  # and isinstance(parent, XibViewController)?

    # Parse these props first, in case any of our children point to us.
    parse_interfacebuilder_properties(ctx, elem, parent, obj)
    parse_children(ctx, elem, obj)

    _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(key == "contentView"))
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if isMainView:
        ctx.isParsingStoryboardView = False

    return obj

