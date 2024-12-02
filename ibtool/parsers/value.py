from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None
    assert elem.attrib["type"] == "size"

    key = elem.attrib["key"]
    if key == "minSize":
        parent["NSMinSize"] = NibString.intern(f"{{{elem.attrib['width']}, {elem.attrib['height']}}}")
        parent["NSWindowContentMinSize"] = NibString.intern(f"{{{elem.attrib['width']}, {elem.attrib['height']}}}")
    elif key == "maxSize":
        parent["NSMaxSize"] = NibString.intern(f"{{{elem.attrib['width']}, {elem.attrib['height']}}}")
        parent["NSWindowContentMaxSize"] = NibString.intern(f"{{{elem.attrib['width']}, {elem.attrib['height']}}}")
    else:
        raise Exception(f"unknown key {key}")
