from ..models import ArchiveContext, NibObject, NibMutableList, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, makeSystemColor, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags, CellFlags, CellFlags2

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    obj = make_xib_object(ctx, "NSBox", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    obj["NSBorderType"] = {
        "separator": 3,
    }[elem.attrib.get("boxType")]
    obj["NSBoxType"] = 2
    obj["NSSubviews"] = NibMutableList([])
    obj["NSTitleCell"] = NibObject("NSTextFieldCell", None, {
        "NSBackgroundColor": makeSystemColor("textBackgroundColor"),
        "NSCellFlags": CellFlags.UNKNOWN_TEXT_FIELD,
        "NSCellFlags2": CellFlags2.TEXT_ALIGN_CENTER,
        "NSContents": NibString.intern("Title"),
        "NSControlSize2": 0,
        "NSSupport": NibObject("NSFont", None, {
            "NSName": NibString.intern(".AppleSystemUIFont"),
            "NSSize": 11.0,
            "NSfFlags": 3100,
        }),
        "NSTextColor": makeSystemColor("labelColor"),
    })
    obj["NSTitlePosition"] = 2
    obj["NSTransparent"] = False
    if "verticalHuggingPriority" in obj.extraContext or "horizontalHuggingPriority" in obj.extraContext:
        v, h = obj.extraContext.get("verticalHuggingPriority", 250), obj.extraContext.get("horizontalHuggingPriority", 250)
        obj["NSHuggingPriority"] = f"{{{h}, {v}}}"
    obj["NSOffsets"] = NibString.intern("{5, 5}")
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
