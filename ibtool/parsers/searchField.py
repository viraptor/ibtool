from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSSearchField", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    if elem.attrib.get('allowsCharacterPickerTouchBarItem') == "YES":
        obj.extraContext["allowsCharacterPickerTouchBarItem"] = True
    if elem.attrib.get("textCompletion") == "NO":
        obj.extraContext["textCompletionDisabled"] = True

    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    x, y, w, h = obj.frame()
    if x == 0 and y == 0:
        obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        obj["NSFrame"] = NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")
    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    obj["NSEnabled"] = True
    obj["NSControlSendActionMask"] = 4
    obj["NSControlUsesSingleLineMode"] = obj.extraContext.get("usesSingleLineMode", False)
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    obj["NSAllowsWritingTools"] = False
    obj["NS.resolvesNaturalAlignmentWithBaseWritingDirection"] = False
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    obj["NSTextFieldAllowsWritingToolsAffordance"] = False

    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    return obj
