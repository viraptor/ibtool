from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element
import base64

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() == "NSButtonCell"

    key = elem.attrib.get("key")
    if key == "keyEquivalent":
        if elem.attrib.get("base64-UTF8") == "YES":
            text = (elem.text or '').strip()
            value = base64.b64decode(text + ((4 - (len(text) % 4)) * '=')).decode('utf-8')
        else:
            value = (elem.text or '').strip()
        parent["NSKeyEquivalent"] = NibString.intern(value)
    else:
        raise Exception(f"unknown key {key}")
