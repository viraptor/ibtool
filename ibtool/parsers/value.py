from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element

TITLE_BAR_HEIGHT = 32

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None
    assert elem.attrib["type"] == "size"

    w = elem.attrib['width']
    h = elem.attrib['height']
    # NSMinSize/NSMaxSize include the title bar; content variants don't
    style_mask = parent.get("NSWindowStyleMask") or 0
    title_bar_offset = TITLE_BAR_HEIGHT if style_mask & 1 else 0
    frame_h = int(float(h)) + title_bar_offset

    key = elem.attrib["key"]
    if key == "minSize":
        parent["NSMinSize"] = NibString.intern(f"{{{w}, {frame_h}}}")
        parent["NSWindowContentMinSize"] = NibString.intern(f"{{{w}, {h}}}")
    elif key == "maxSize":
        parent["NSMaxSize"] = NibString.intern(f"{{{w}, {frame_h}}}")
        parent["NSWindowContentMaxSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        raise Exception(f"unknown key {key}")
