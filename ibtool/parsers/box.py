from ..models import ArchiveContext, NibObject, NibMutableList, NibString, NibNil, NibList, NibNSNumber
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, makeSystemColor, _xibparser_common_translate_autoresizing, handle_props, PropSchema
from ..parsers_base import parse_children
from ..constants import vFlags, CellFlags, CellFlags2

BOX_TITLE_POSITION_MAP = {
    "noTitle": 0,
    None: 2,
}

BOX_BORDER_TYPE_MAP = {
    None: 3,
    "none": 0,
    "line": 1,
    "bezel": 2,
}

BOX_TYPE_MAP = {
    None: 0,
    "separator": 2,
}

BOX_USING_CONTENT_VIEW_MAP = {
    None: True,
    "separator": None,
}

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    obj = make_xib_object(ctx, "NSBox", elem, parent)
    obj.extraContext["titlePosition"] = elem.attrib.get("titlePosition")
    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSSuperview", const=obj.xib_parent()),
        PropSchema(prop="NSBoxType", attrib="boxType", default=None, map=BOX_TYPE_MAP, skip_default=False),
        PropSchema(prop="NSBorderType", attrib="borderType", default=None, map=BOX_BORDER_TYPE_MAP, skip_default=False),
        PropSchema(prop="IBNSBoxIsUsingDocumentContentView", attrib="boxType", default=None, map=BOX_USING_CONTENT_VIEW_MAP, skip_default=False),
        PropSchema(prop="NSTransparent", const=False),
        PropSchema(prop="NSOffsets", attrib="boxType", default=None, map={None: NibString.intern("{0, 0}"), "separator": NibString.intern("{5, 5}")}, skip_default=False),
        PropSchema(prop="NSSubviews", default=NibMutableList([])),
    ])
    
    is_separator = elem.attrib.get("boxType") == "separator"

    if is_separator:
        font = NibObject("NSFont", None, {
            "NSName": NibString.intern(".AppleSystemUIFont"),
            "NSSize": 11.0,
            "NSfFlags": 0xc1c,
        })
        title = "Title"
        title_position = 2
    else:
        if tf := obj.extraContext.get("titleFont"):
            font = tf
        else:
            font = NibObject("NSFont", None, {
                "NSName": NibString.intern(".AppleSystemUIFont"),
                "NSSize": 11.0,
                "NSfFlags": 0xc1c,
            })
        title = elem.attrib.get("title", "" if elem.attrib.get("titlePosition") == "noTitle" else "Title")
        title_position = BOX_TITLE_POSITION_MAP.get(elem.attrib.get("titlePosition"), 2)

    obj["NSTitlePosition"] = title_position

    obj["NSTitleCell"] = NibObject("NSTextFieldCell", None, {
        "NSBackgroundColor": makeSystemColor("textBackgroundColor"),
        "NSCellFlags": CellFlags.UNKNOWN_TEXT_FIELD,
        "NSCellFlags2": CellFlags2.TEXT_ALIGN_CENTER,
        "NSContents": NibString.intern(title),
        "NSControlView": NibNil(),
        "NSSupport": font,
        "NSTextColor": makeSystemColor("labelColor"),
    })
    if "verticalHuggingPriority" in obj.extraContext or "horizontalHuggingPriority" in obj.extraContext:
        v, h = obj.extraContext.get("verticalHuggingPriority", 250), obj.extraContext.get("horizontalHuggingPriority", 250)
        obj["NSHuggingPriority"] = f"{{{h}, {v}}}"
    if is_separator and not obj.extraContext.get("NSDoNotTranslateAutoresizingMask"):
        obj.flagsOr("NSvFlags", 0x1000)

    if not obj.extraContext.get("parsed_autoresizing"):
        flags = vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS
        if obj.extraContext.get("no_autoresizes_subviews"):
            flags = flags & ~vFlags.AUTORESIZES_SUBVIEWS
            ctx.connections.append(NibObject("NSIBUserDefinedRuntimeAttributesConnector", None, {
                "NSObject": obj,
                "NSValues": NibList([NibNSNumber(False)]),
                "NSKeyPaths": NibList([NibString.intern("autoresizesSubviews")]),
            }))
        obj.flagsOr("NSvFlags", flags)

    return obj
