from ..models import ArchiveContext, NibObject, NibMutableList, NibString, NibNil
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, makeSystemColor, _xibparser_common_translate_autoresizing, handle_props, PropSchema
from ..parsers_base import parse_children
from ..constants import vFlags, CellFlags, CellFlags2

BOX_TITLE_POSITION_MAP = {
    "noTitle": 0,
    None: 2,
}

BOX_BORDER_TYPE_MAP = {
    "separator": 3,
    None: 3,
}

BOX_TYPE_MAP = {
    None: 0,
    "separator": 2,
}

BOX_USING_CONTENT_VIEW_MAP = {
    None: True,
    "separator": False,
}

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    obj = make_xib_object(ctx, "NSBox", elem, parent)
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSSuperview", const=obj.xib_parent()),
        PropSchema(prop="NSBoxType", attrib="boxType", default=None, map=BOX_TYPE_MAP, skip_default=False),
        PropSchema(prop="NSBorderType", attrib="boxType", default=None, map=BOX_BORDER_TYPE_MAP, skip_default=False),
        PropSchema(prop="IBNSBoxIsUsingDocumentContentView", attrib="boxType", default=None, map=BOX_USING_CONTENT_VIEW_MAP),
        PropSchema(prop="NSTitlePosition", attrib="titlePosition", default=None, map=BOX_TITLE_POSITION_MAP, skip_default=False),
        PropSchema(prop="NSTransparent", const=False),
        PropSchema(prop="NSOffsets", const=NibString.intern("{0, 0}")),
        PropSchema(prop="NSSubviews", default=NibMutableList([])),
    ])
    
    if tf := obj.extraContext.get("titleFont"):
        font = tf
    else:
        font = NibObject("NSFont", None, {
            "NSName": NibString.intern(".AppleSystemUIFont"),
            "NSSize": 11.0,
            "NSfFlags": 0xc1c,
        })

    obj["NSTitleCell"] = NibObject("NSTextFieldCell", None, {
        "NSBackgroundColor": makeSystemColor("textBackgroundColor"),
        "NSCellFlags": CellFlags.UNKNOWN_TEXT_FIELD,
        "NSCellFlags2": CellFlags2.TEXT_ALIGN_CENTER,
        "NSContents": NibString.intern(elem.attrib.get("title", "Title")),
        "NSControlSize2": 0,
        "NSSupport": font,
        "NSTextColor": makeSystemColor("labelColor"),
    })
    if "verticalHuggingPriority" in obj.extraContext or "horizontalHuggingPriority" in obj.extraContext:
        v, h = obj.extraContext.get("verticalHuggingPriority", 250), obj.extraContext.get("horizontalHuggingPriority", 250)
        obj["NSHuggingPriority"] = f"{{{h}, {v}}}"
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
