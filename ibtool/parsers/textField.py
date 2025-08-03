from ..models import ArchiveContext, NibObject, XibObject, NibNil
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSTextField", elem, parent)

    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj.setIfEmpty("NSFrame", NibNil())
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsWritingTools"] = True
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    obj["NSControlUsesSingleLineMode"] = False
    obj.setIfEmpty("NSControlLineBreakMode", 0)
    obj["NSControlSendActionMask"] = 4
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    if elem.attrib.get("textCompletion") == "NO":
        obj["NSCell"]["NSAutomaticTextCompletionDisabled"] = True
    if "verticalHuggingPriority" in obj.extraContext or "horizontalHuggingPriority" in obj.extraContext:
        v, h = obj.extraContext.get("verticalHuggingPriority", 250), obj.extraContext.get("horizontalHuggingPriority", 250)
        #obj["NSHuggingPriority"] = f"{{{h}, {v}}}"
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
