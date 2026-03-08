from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibMutableSet, NibMutableDictionary, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children

WEBVIEW_DRAG_TYPES = [
    "Apple HTML pasteboard type",
    "Apple PDF pasteboard type",
    "Apple URL pasteboard type",
    "Apple Web Archive pasteboard type",
    "Apple WebKit dummy pasteboard type",
    "Apple files promise pasteboard type",
    "NSColor pasteboard type",
    "NSFilenamesPboardType",
    "NSStringPboardType",
    "NeXT RTFD pasteboard type",
    "NeXT Rich Text Format v1.0 pasteboard type",
    "NeXT TIFF v4.0 pasteboard type",
    "WebURLsWithTitlesPboardType",
    "public.png",
    "public.url",
    "public.url-name",
]

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "WebView", elem, parent)

    parse_children(ctx, elem, obj)

    obj["NSSuperview"] = obj.xib_parent()
    obj["NSNextKeyView"] = NibNil()
    obj["NSDragTypes"] = NibMutableSet([NibString.intern(s) for s in WEBVIEW_DRAG_TYPES])
    obj["FrameName"] = NibString.intern("")
    obj["GroupName"] = NibString.intern("")

    identifier = obj.extraContext.get("webPrefsIdentifier")
    values = obj.extraContext.get("webPrefsValues", [])
    prefs = NibObject("WebPreferences", obj, {
        "Identifier": NibString.intern(identifier) if identifier else NibNil(),
        "Values": NibMutableDictionary(values),
    })
    obj["Preferences"] = prefs

    obj["UseBackForwardList"] = True
    obj["AllowsUndo"] = True

    return obj
