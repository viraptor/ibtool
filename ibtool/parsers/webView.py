from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList, NibMutableSet, NibMutableDictionary, NibString, NibNSNumber
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags
from .webPreferences import WEBKIT_PREFS

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


def _build_prefs_values(obj: XibObject) -> list:
    identifier = obj.extraContext.get("webPrefsIdentifier")
    attribs = obj.extraContext.get("webPrefsAttribs", {})
    prefix = identifier or ""

    entries = []
    for attrib, webkit_key, default, convert in WEBKIT_PREFS:
        raw = attribs.get(attrib)
        if raw is None:
            continue
        if default is not None and raw == default:
            continue
        entries.append((prefix + webkit_key, convert(raw)))

    entries.sort(key=lambda kv: kv[0])

    values = []
    for k, v in entries:
        values.append(NibString.intern(k))
        values.append(NibNSNumber(v))
    return values


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "WebView", elem, parent)

    parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    obj["NSSuperview"] = obj.xib_parent()
    obj["NSNextKeyView"] = NibNil()
    obj["NSDragTypes"] = NibMutableSet([NibString.intern(s) for s in WEBVIEW_DRAG_TYPES])
    obj["FrameName"] = NibString.intern("")
    obj["GroupName"] = NibString.intern("")

    identifier = obj.extraContext.get("webPrefsIdentifier")
    values = _build_prefs_values(obj)
    prefs = NibObject("WebPreferences", obj, {
        "Identifier": NibString.intern(identifier) if identifier else NibNil(),
        "Values": NibMutableDictionary(values),
    })
    obj["Preferences"] = prefs

    obj["UseBackForwardList"] = elem.attrib.get("maintainsBackForwardList", "YES") == "YES"
    obj["AllowsUndo"] = True

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj
