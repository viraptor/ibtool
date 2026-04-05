from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableSet
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSPathControl", elem, parent)

    obj["NSSuperview"] = obj.xib_parent()
    obj["NSNextResponder"] = obj.xib_parent()

    drag_types = NibMutableSet([
        NibString.intern("Apple URL pasteboard type"),
        NibString.intern("NSFilenamesPboardType"),
    ])
    obj["NSDragTypes"] = drag_types

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
    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
    obj.setIfNotDefault("NSControlAllowsExpansionToolTips", elem.attrib.get("allowsExpansionToolTips") == "YES", False)
    obj["NSControlSize"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlTextAlignment"] = 0
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
