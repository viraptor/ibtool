from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children

DIVIDER_THICKNESS = {
    None: 9,
    "thick": 9,
    "paneSplitter": 9,
    "thin": 1,
}

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSplitView", elem, parent)

    parse_children(ctx, elem, obj)

    obj["NSSuperview"] = obj.xib_parent()

    is_vertical = elem.attrib.get("vertical") == "YES"
    divider_style = elem.attrib.get("dividerStyle")
    divider_thickness = DIVIDER_THICKNESS.get(divider_style, 9)

    if is_vertical:
        obj["NSIsVertical"] = True

    # Recalculate subview frames based on split orientation
    subviews = obj.get("NSSubviews")
    if subviews and len(subviews) > 0:
        sv_frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame:
            sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
            sv_h = sv_frame[3] if len(sv_frame) == 4 else sv_frame[1]
            n = len(subviews)
            total_dividers = (n - 1) * divider_thickness

            if is_vertical:
                # Vertical split: divide width
                available = sv_w - total_dividers
                base_size = available // n
                remainder = available - base_size * n
                pos = 0
                for i, subview in enumerate(subviews):
                    w = base_size + (1 if i < remainder else 0)
                    subview["NSViewClipsToBoundsKeyName"] = True
                    if pos == 0:
                        subview["NSFrameSize"] = NibString.intern(f"{{{w}, {sv_h}}}")
                        if subview.get("NSFrame"):
                            del subview["NSFrame"]
                        subview.extraContext.pop("NSFrame", None)
                        subview.extraContext["NSFrameSize"] = (w, sv_h)
                    else:
                        subview["NSFrame"] = NibString.intern(f"{{{{{pos}, 0}}, {{{w}, {sv_h}}}}}")
                        if subview.get("NSFrameSize"):
                            del subview["NSFrameSize"]
                        subview.extraContext.pop("NSFrameSize", None)
                        subview.extraContext["NSFrame"] = (pos, 0, w, sv_h)
                    pos += w + divider_thickness
            else:
                # Horizontal split: divide height
                available = sv_h - total_dividers
                base_size = available // n
                remainder = available - base_size * n
                pos = 0
                for i, subview in enumerate(subviews):
                    h = base_size + (1 if i < remainder else 0)
                    subview["NSViewClipsToBoundsKeyName"] = True
                    if pos == 0:
                        subview["NSFrameSize"] = NibString.intern(f"{{{sv_w}, {h}}}")
                        if subview.get("NSFrame"):
                            del subview["NSFrame"]
                        subview.extraContext.pop("NSFrame", None)
                        subview.extraContext["NSFrameSize"] = (sv_w, h)
                    else:
                        subview["NSFrame"] = NibString.intern(f"{{{{0, {pos}}}, {{{sv_w}, {h}}}}}")
                        if subview.get("NSFrameSize"):
                            del subview["NSFrameSize"]
                        subview.extraContext.pop("NSFrameSize", None)
                        subview.extraContext["NSFrame"] = (0, pos, sv_w, h)
                    pos += h + divider_thickness
    else:
        if subviews:
            for subview in subviews:
                subview["NSViewClipsToBoundsKeyName"] = True

    handle_props(ctx, elem, obj, [
    ])

    return obj
