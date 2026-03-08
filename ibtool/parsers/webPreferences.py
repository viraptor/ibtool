from ..models import ArchiveContext, NibObject, NibString, NibNSNumber
from xml.etree.ElementTree import Element

WEBKIT_PREFS = [
    ("defaultFixedFontSize", "WebKitDefaultFixedFontSize", int),
    ("defaultFontSize", "WebKitDefaultFontSize", int),
    ("javaScriptCanOpenWindowsAutomatically", "WebKitJavaScriptCanOpenWindowsAutomatically", lambda v: v == "YES"),
]

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    identifier = elem.attrib.get("identifier")
    if not identifier:
        return

    parent.extraContext["webPrefsIdentifier"] = identifier

    values = []
    for attrib, webkit_key, convert in WEBKIT_PREFS:
        val = elem.attrib.get(attrib)
        if val is not None:
            values.append(NibString.intern(f"{identifier}{webkit_key}"))
            values.append(NibNSNumber(convert(val)))

    if values:
        parent.extraContext["webPrefsValues"] = values
