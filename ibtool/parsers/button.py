from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString
from ..parsers.helpers import make_xib_object
from ..parsers_base import parse_children
from .helpers import _xibparser_common_translate_autoresizing
from xml.etree.ElementTree import Element
from typing import Optional
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSButton", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj["NSNextResponder"] = obj.xib_parent()
    if obj.get("NSFrameSize") is None:
        obj.setIfEmpty("NSFrame", NibNil())
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    obj["NSControlUsesSingleLineMode"] = False
    obj.setIfEmpty("NSControlLineBreakMode", 0)
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    h = obj.extraContext.get("horizontalHuggingPriority")
    v = obj.extraContext.get("verticalHuggingPriority")
    if h is not None or v is not None:
        hp = h or "250"
        vp = v or "250"
        cell = obj.get("NSCell")
        bezel = cell.get("NSBezelStyle") if cell and not isinstance(cell, NibNil) else None
        default_hp, default_vp = ("750", "750") if bezel in (5, 9, 14) else ("250", "750")
        in_cell_view = False
        p = obj.xib_parent()
        while p is not None:
            if hasattr(p, 'originalclassname') and p.originalclassname() == "NSTableCellView":
                in_cell_view = True
                break
            p = p.xib_parent() if hasattr(p, 'xib_parent') else None
        _SUPPRESS_DEFAULT_HUGGING_BEZELS = (None, 1, 11, 12, 13)
        is_check_or_radio = obj.extraContext.get("button_type") in ("check", "radio")
        is_swapper = obj.classname() == "NSClassSwapper"
        is_bevel = obj.extraContext.get("button_type") == "bevel"
        if hp != default_hp or vp != default_vp or in_cell_view or is_check_or_radio or is_bevel or (bezel not in _SUPPRESS_DEFAULT_HUGGING_BEZELS and not is_swapper):
            obj["NSHuggingPriority"] = NibString.intern(f"{{{hp}, {vp}}}")
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    return obj

