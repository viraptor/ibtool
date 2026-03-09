from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children

def containing_clip_view(ctx: ArchiveContext, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSClipView", None, parent)
    # Header clip view should not be a top-level object
    ctx.extraNibObjects.remove(obj)
    obj["NSNextResponder"] = parent
    obj["NSSuperview"] = parent
    obj["NSAutomaticallyAdjustsContentInsets"] = True
    obj["NSSubviews"] = NibMutableList([])
    # Frame will be computed after header view is parsed
    obj["NSFrame"] = NibString.intern("{{1, 1}, {238, 20}}")
    return obj


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    key = elem.attrib.get("key")

    if key == "headerView":
        assert parent.originalclassname() == "NSScrollView"

        clip_view = containing_clip_view(ctx, parent)

        obj = make_xib_object(ctx, "NSTableHeaderView", elem, parent)
        # Mark header view to skip parent insets in frame() computation
        obj.extraContext["skip_parent_insets"] = True

        with __handle_view_chain(ctx, obj):
            parse_children(ctx, elem, obj)

        # Compute header clip view frame from scroll view dimensions and header height
        header_frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if header_frame:
            header_h = header_frame[3] if len(header_frame) == 4 else header_frame[1]
        else:
            header_h = 20
        sv_frame = parent.extraContext.get("NSFrame") or parent.extraContext.get("NSFrameSize")
        insets = parent.extraContext.get("insets", (0, 0))
        border = insets[0] // 2
        if sv_frame:
            sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
            clip_w = sv_w - 2 * border
            clip_view["NSFrame"] = NibString.intern(f"{{{{{border}, {border}}}, {{{clip_w}, {header_h}}}}}")

        table_view = parent["NSContentView"]["NSSubviews"]._items[0]
        assert table_view.originalclassname() in ("NSTableView", "NSOutlineView"), table_view.originalclassname()
        table_view["NSHeaderView"] = obj

        obj["NSNextResponder"] = clip_view
        obj["NSSuperview"] = clip_view
        obj["NSTableView"] = table_view
        clip_view["NSNextKeyView"] = obj
        clip_view["NSDocView"] = obj
        clip_view["NSSubviews"].addItem(obj)
        parent["NSHeaderClipView"] = clip_view
        handle_props(ctx, elem, obj, [
            PropSchema(prop="NSViewIsLayerTreeHost", attrib="wantsLayer", map=MAP_YES_NO, default="NO", skip_default=True)
        ])
    else:
        raise ValueError(f"Unknown table header view key: {key}")

    return obj
