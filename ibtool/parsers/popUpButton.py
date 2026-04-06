from ..models import ArchiveContext, NibObject, NibString, XibObject, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSPopUpButton", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    if ctx.isStoryboard:
        from ..text_measure import compute_intrinsic_width, _available
        if _available:
            iw = compute_intrinsic_width(elem)
            if iw is not None:
                rf = obj.raw_frame()
                if rf is not None:
                    x, y, w, h = rf
                    if w != iw and abs(w - iw) <= 2:
                        obj.set_nib_frame(x, y, iw, h)
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    obj["NSControlSendActionMask"] = 4
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSEnabled"] = True
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if ctx.toolsVersion >= 21000:
        h = elem.attrib.get("horizontalHuggingPriority", "250")
        v = elem.attrib.get("verticalHuggingPriority", "250")
        if h != "250" or v != "750":
            obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    return obj
