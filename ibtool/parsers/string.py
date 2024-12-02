from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element
import base64

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() in ("NSButtonCell", "NSTextFieldCell"), parent.originalclassname()

    key = elem.attrib.get("key")
    if elem.attrib.get("base64-UTF8") == "YES":
        text = (elem.text or '').strip()
        value = base64.b64decode(text + ((4 - (len(text) % 4)) * '=')).decode('utf-8')
    else:
        value = (elem.text or '').strip()

    if key == "keyEquivalent":
        parent["NSKeyEquivalent"] = NibString.intern(value)

    elif key == "title":
        parent["NSContents"] = NibString.intern(value)

    else:
        raise Exception(f"unknown key {key}")
