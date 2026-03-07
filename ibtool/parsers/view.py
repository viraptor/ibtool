from .helpers import parse_interfacebuilder_properties, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..models import ArchiveContext, XibObject, NibString, NibMutableList
from xml.etree.ElementTree import Element
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: XibObject, **kwargs) -> XibObject:
    obj = XibObject(ctx, "NSView", elem, parent)
    ctx.extraNibObjects.append(obj)
    obj.setrepr(elem)

    key = elem.get("key")
    is_box_content = False
    if key == "contentView":
        if parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
            obj["NSFrameSize"] = NibString.intern("{0, 0}")
        elif parent.originalclassname() == "NSBox":
            parent["NSContentView"] = obj
            parent["NSSubviews"] = NibMutableList([obj])
            obj["NSSuperview"] = parent
            is_box_content = True
            # Store box outer size so subviews' frame() uses it as parent size
            box_frame = parent.extraContext.get("NSFrame") or parent.extraContext.get("NSFrameSize")
            if box_frame:
                bw = box_frame[2] if len(box_frame) == 4 else box_frame[0]
                bh = box_frame[3] if len(box_frame) == 4 else box_frame[1]
                obj.extraContext["box_content_size"] = (bw, bh)
                obj.extraContext["box_design_size"] = (int(content_rect.attrib["width"]), int(content_rect.attrib["height"])) if (content_rect := elem.find('rect[@key="frame"]')) is not None else (bw, bh)
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

    _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(parent is None))
    if is_box_content:
        # Box content views should point to the box, not NibNil
        obj["NSNextResponder"] = parent
        # Override frame: box content view uses box's outer size at position (0,0)
        box_frame = parent.extraContext.get("NSFrame") or parent.extraContext.get("NSFrameSize")
        if box_frame:
            bw = box_frame[2] if len(box_frame) == 4 else box_frame[0]
            bh = box_frame[3] if len(box_frame) == 4 else box_frame[1]
            obj["NSFrameSize"] = NibString.intern(f"{{{bw}, {bh}}}")
            if obj.get("NSFrame"):
                del obj["NSFrame"]
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if isMainView:
        ctx.isParsingStoryboardView = False

    return obj

