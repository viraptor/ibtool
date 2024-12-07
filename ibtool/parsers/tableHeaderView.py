from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain
from ..parsers_base import parse_children

def containing_clip_view(ctx: ArchiveContext, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSClipView", None, parent)
    obj["NSNextResponder"] = parent
    obj["NSSuperview"] = parent
    obj["NSAutomaticallyAdjustsContentInsets"] = True
    obj["NSSubviews"] = NibMutableList([])
    obj["NSFrame"] = NibString.intern("{{1, 1}, {238, 20}}")
    return obj


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    key = elem.attrib.get("key")

    if key == "headerView":
        assert parent.originalclassname() == "NSScrollView"

        clip_view = containing_clip_view(ctx, parent)

        obj = make_xib_object(ctx, "NSTableHeaderView", elem, clip_view)

        with __handle_view_chain(ctx, obj):
            parse_children(ctx, elem, obj)

        table_view = parent["NSContentView"]["NSSubviews"]._items[0]
        assert table_view.originalclassname() == "NSTableView"
        table_view["NSHeaderView"] = obj

        obj["NSNextResponder"] = clip_view
        obj["NSSuperview"] = clip_view
        obj["NSTableView"] = table_view
        obj["NSViewIsLayerTreeHost"] = True
        clip_view["NSNextKeyView"] = obj
        clip_view["NSDocView"] = obj
        clip_view["NSSubviews"].addItem(obj)
        parent["NSHeaderClipView"] = clip_view

    else:
        raise ValueError(f"Unknown table header view key: {key}")

    return obj
