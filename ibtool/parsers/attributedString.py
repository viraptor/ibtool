from ..models import ArchiveContext, NibObject, NibString, NibDictionary, NibList, NibNSNumber
from xml.etree.ElementTree import Element
from .font import build_font
from .helpers import makeSystemColor


_ALIGNMENT_MAP = {
    None: 4,        # natural
    "left": 0,
    "right": 1,
    "center": 2,
    "justified": 3,
    "natural": 4,
}


def _fragment_text(frag: Element) -> str:
    if "content" in frag.attrib:
        return frag.attrib["content"]
    for child in frag:
        if child.tag in ("string", "mutableString") and child.attrib.get("key") == "content":
            return child.text or ""
    return ""


def _font_signature(font_elem):
    if font_elem is None:
        return None
    return (
        font_elem.attrib.get("metaFont"),
        font_elem.attrib.get("name"),
        font_elem.attrib.get("size"),
    )


def _paragraph_signature(p_elem):
    if p_elem is None:
        return None
    tabs_elem = p_elem.find("tabStops")
    tabs = ()
    if tabs_elem is not None:
        tabs = tuple((t.attrib.get("alignment", "left"), t.attrib.get("location", "0"))
                     for t in tabs_elem.findall("textTab"))
    return (
        p_elem.attrib.get("alignment"),
        p_elem.attrib.get("lineBreakMode"),
        p_elem.attrib.get("baseWritingDirection"),
        tabs,
    )


def _build_paragraph_style(p_elem, tab_pool):
    """Build an NSParagraphStyle from a <paragraphStyle> element.
    tab_pool is a dict (location_str -> NSTextTab) used to share NSTextTab
    objects across paragraph styles when the same location appears."""
    obj = NibObject("NSParagraphStyle")
    obj["NSAlignment"] = _ALIGNMENT_MAP.get(p_elem.attrib.get("alignment"))
    obj["NSTighteningFactorForTruncation"] = 0.05000000074505806
    tabs_elem = p_elem.find("tabStops")
    tabs = []
    if tabs_elem is not None:
        for t in tabs_elem.findall("textTab"):
            loc = t.attrib.get("location", "0")
            if loc not in tab_pool:
                tab = NibObject("NSTextTab")
                tab["NSLocation"] = float(loc)
                tab_pool[loc] = tab
            tabs.append(tab_pool[loc])
    obj["NSTabStops"] = NibList(tabs)
    obj["NSAllowsTighteningForTruncation"] = 1
    return obj


def _default_font():
    f = NibObject("NSFont")
    f["NSName"] = NibString.intern("Helvetica")
    f["NSSize"] = 12.0
    f["NSfFlags"] = 16
    return f


def _build_attribute_dict(font_elem, p_elem, tab_pool):
    """Build an NSDictionary attribute set with NSColor, NSFont, NSParagraphStyle."""
    items = [
        NibString.intern("NSColor"),
        makeSystemColor("textColor"),
        NibString.intern("NSFont"),
        build_font(font_elem) if font_elem is not None else _default_font(),
    ]
    if p_elem is not None:
        items.extend([NibString.intern("NSParagraphStyle"),
                      _build_paragraph_style(p_elem, tab_pool)])
    return NibDictionary(items)


def _encode_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _encode_runs(runs):
    """Encode a list of (length, dict_index) pairs as varint pairs."""
    out = bytearray()
    for length, idx in runs:
        out += _encode_varint(length)
        out += _encode_varint(idx)
    return bytes(out)


def parse(ctx: ArchiveContext, elem: Element, parent) -> None:
    fragments = []
    for child in elem:
        if child.tag != "fragment":
            continue
        text = _fragment_text(child)
        attrs_elem = child.find("attributes")
        font_elem = attrs_elem.find("font") if attrs_elem is not None else None
        p_elem = attrs_elem.find("paragraphStyle") if attrs_elem is not None else None
        fragments.append((text, font_elem, p_elem))

    full_text = "".join(f[0] for f in fragments)
    parent.extraContext["attributedStringText"] = full_text

    if not fragments:
        return

    # Group consecutive fragments with the same attribute signature into runs.
    sigs = []
    sig_to_idx = {}
    runs = []  # list of (length, dict_index)
    tab_pool = {}
    dict_objs = []
    for text, font_elem, p_elem in fragments:
        sig = (_font_signature(font_elem), _paragraph_signature(p_elem))
        if sig not in sig_to_idx:
            sig_to_idx[sig] = len(sigs)
            sigs.append(sig)
            dict_objs.append(_build_attribute_dict(font_elem, p_elem, tab_pool))
        idx = sig_to_idx[sig]
        if runs and runs[-1][1] == idx:
            runs[-1] = (runs[-1][0] + len(text), idx)
        else:
            runs.append((len(text), idx))

    parent.extraContext["attributedStringDicts"] = dict_objs
    parent.extraContext["attributedStringRuns"] = runs
    parent.extraContext["attributedStringRunData"] = _encode_runs(runs)
