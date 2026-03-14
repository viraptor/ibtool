from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSecureTextField", elem, parent)

    obj["NSSuperview"] = obj.xib_parent()
    obj["NSNextResponder"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    x, y, w, h = obj.frame()
    if x == 0 and y == 0:
        obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        obj["NSFrame"] = NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsWritingTools"] = True
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj.setIfEmpty("NSControlRefusesFirstResponder", elem.attrib.get("refusesFirstResponder", "NO") == "YES")
    obj["NSControlUsesSingleLineMode"] = obj.extraContext.get("usesSingleLineMode", False)
    obj.setIfEmpty("NSControlLineBreakMode", 0)
    obj["NSControlSendActionMask"] = 4
    pmlw = elem.attrib.get("preferredMaxLayoutWidth")
    if pmlw is not None and float(pmlw) != 0:
        obj["NSPreferredMaxLayoutWidth"] = float(pmlw)
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    obj["NSTextFieldAllowsWritingToolsAffordance"] = False
    obj["NS.resolvesNaturalAlignmentWithBaseWritingDirection"] = False
    h = obj.extraContext.get("horizontalHuggingPriority", "250")
    v = obj.extraContext.get("verticalHuggingPriority", "750")
    if h != "250" or v != "750":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
