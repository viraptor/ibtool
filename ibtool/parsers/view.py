from .helpers import parse_interfacebuilder_properties, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing, frame_string, size_string
from ..parsers_base import parse_children
from ..models import ArchiveContext, XibObject, NibString, NibMutableList
from xml.etree.ElementTree import Element
from ..constants import vFlags

VIEW_DEFAULT_H_HUG = "250"
VIEW_DEFAULT_V_HUG = "250"

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
            if parent.extraContext.get("fullSizeContentView"):
                if window_size := parent.extraContext.get("NSFrameSize"):
                    obj.extraContext["override_frame_size"] = window_size
        elif parent.originalclassname() == "NSBox":
            parent["NSContentView"] = obj
            parent["NSSubviews"] = NibMutableList([obj])
            obj["NSSuperview"] = parent
            is_box_content = True
            # Store box outer size so subviews' frame() uses it as parent size
            box_raw = parent.raw_frame()
            if box_raw:
                bw, bh = box_raw[2], box_raw[3]
                # Titled boxes have a 12px title area
                title_offset = 12 if parent.extraContext.get("titlePosition") != "noTitle" else 0
                content_h = bh - title_offset
                obj.extraContext["box_content_size"] = (bw, content_h)
                # Compute offsets between computed and XIB content rect
                content_rect = elem.find('rect[@key="frame"]')
                if content_rect is not None:
                    xib_w = int(content_rect.attrib["width"])
                    xib_h = int(content_rect.attrib["height"])
                    x_offset = bw - xib_w
                    y_offset = content_h - xib_h
                    if x_offset != 0:
                        obj.extraContext["box_child_x_offset"] = x_offset
                    if y_offset != 0:
                        obj.extraContext["box_child_y_offset"] = y_offset
                    obj.extraContext["box_xib_size"] = (xib_w, xib_h)
        else:
            raise Exception(
                "Unhandled class '%s' to take NSView with key 'contentView'"
                % (parent.originalclassname())
            )
    elif key is None or key == "view":
        obj["NSSuperview"] = parent
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
        # Override frame using pre-computed box content size
        if box_size := obj.extraContext.get("box_content_size"):
            obj["NSFrameSize"] = size_string(box_size[0], box_size[1])
            if obj.get("NSFrame"):
                del obj["NSFrame"]
        # Adjust child coordinates and sizes for autoresizing when content view size differs from XIB
        x_off = obj.extraContext.get("box_child_x_offset", 0)
        y_off = obj.extraContext.get("box_child_y_offset", 0)
        xib_size = obj.extraContext.get("box_xib_size")
        if (x_off or y_off) and xib_size:
            subviews = obj.get("NSSubviews")
            if subviews:
                for child in subviews:
                    child_frame = child.extraContext.get("NSFrame") if hasattr(child, 'extraContext') else None
                    if not child_frame:
                        continue
                    cx, cy, cw, ch = child_frame
                    ar = child.extraContext.get("parsed_autoresizing") if hasattr(child, 'extraContext') else None
                    changed = False
                    if ar and isinstance(ar, dict):
                        if x_off and ar.get("widthSizable"):
                            cw += x_off
                            changed = True
                        if x_off and ar.get("flexibleMinX"):
                            if ar.get("flexibleMaxX"):
                                left_margin = cx
                                right_margin = xib_size[0] - cx - child_frame[2]
                                total = left_margin + right_margin
                                dx = int(x_off * left_margin / total) if total else 0
                            else:
                                dx = x_off
                            cx += dx
                            changed = True
                        if y_off and ar.get("flexibleMinY"):
                            if ar.get("flexibleMaxY"):
                                bot_margin = cy
                                top_margin = xib_size[1] - cy - ch
                                total = bot_margin + top_margin
                                dy = int(y_off * bot_margin / total) if total else 0
                            else:
                                dy = y_off
                            cy += dy
                            changed = True
                    elif y_off:
                        cy += y_off
                        changed = True
                    if changed:
                        child.set_nib_frame(cx, cy, cw, ch)
        # Box content views are width+height sizable, skip default autolayout flags
        obj.flagsOr("NSvFlags", vFlags.WIDTH_SIZABLE | vFlags.HEIGHT_SIZABLE)
        obj.extraContext["parsed_autoresizing"] = True
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if isMainView:
        ctx.isParsingStoryboardView = False

    h = elem.attrib.get("horizontalHuggingPriority", VIEW_DEFAULT_H_HUG)
    v = elem.attrib.get("verticalHuggingPriority", VIEW_DEFAULT_V_HUG)
    if h != VIEW_DEFAULT_H_HUG or v != VIEW_DEFAULT_V_HUG:
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    if override := obj.extraContext.get("override_frame_size"):
        w, h = override
        obj["NSFrameSize"] = size_string(w, h)
        if obj.get("NSFrame"):
            del obj["NSFrame"]

    return obj

