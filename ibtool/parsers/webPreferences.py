from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

WEBKIT_PREFS = [
    ("defaultFixedFontSize", "WebKitDefaultFixedFontSize", "12", int),
    ("defaultFontSize", "WebKitDefaultFontSize", "12", int),
    ("javaScriptCanOpenWindowsAutomatically", "WebKitJavaScriptCanOpenWindowsAutomatically", "YES", lambda v: v == "YES"),
    ("minimumFontSize", "WebKitMinimumFontSize", None, int),
    ("plugInsEnabled", "WebKitLegacyPluginQuirkForMailSignaturesEnabled", "YES", lambda v: v == "YES"),
]


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    identifier_elem = elem.find('string[@key="identifier"]')
    identifier = identifier_elem.text if identifier_elem is not None else elem.attrib.get("identifier")
    parent.extraContext["webPrefsHasIdentifier"] = identifier is not None
    parent.extraContext["webPrefsIdentifier"] = identifier
    parent.extraContext["webPrefsAttribs"] = dict(elem.attrib)
