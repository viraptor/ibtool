from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSLevelIndicator", elem, parent)

    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    obj.setIfEmpty("NSFrame", NibNil())
    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    obj["NSControlContinuous"] = False
    obj["NSControlSendActionMask"] = 4
    obj["NSControlTextAlignment"] = 0
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = -1
    obj["NSEnabled"] = True

    h = obj.extraContext.get("horizontalHuggingPriority", "250")
    v = obj.extraContext.get("verticalHuggingPriority", "750")
    if h != "250" or v != "750":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
