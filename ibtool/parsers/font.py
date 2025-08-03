from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element
from ..constants import FontFlags

def to_flags_val(x):
    return ((x<<8) & 0xf00) | (x & 0xff)

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> NibObject:
    item = NibObject("NSFont")
    meta_font = elem.attrib.get("metaFont")
    key = elem.attrib.get("key")

    if key == "titleFont":
        flags = FontFlags.ROLE_UNKNOWN.value
    else:
        flags = 0

    if meta_font is None:
        item["NSName"] = NibString.intern(elem.attrib.get("name", ".AppleSystemUIFont"))
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        if "name" in elem.attrib:
            flags = FontFlags.ROLE_CONTROL_CONTENT_FONT.value
        else:
            flags = FontFlags.ROLE_LABEL_FONT.value
        item["NSfFlags"] = to_flags_val(flags)
        if elem.attrib.get("usesAppearanceFont") == "YES":
            item["NSFontUsesAppearanceFontSize"] = True # does it apply to all?
    elif meta_font == 'system':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        flags = flags or FontFlags.ROLE_LABEL_FONT.value
        item["NSfFlags"] = to_flags_val(flags)
    elif meta_font == 'systemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontBold")
        item["NSSize"] = float(elem.attrib.get("size", 24.0))
        item["NSfFlags"] = to_flags_val(0x18)
    elif meta_font == 'smallSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 11.0))
        item["NSfFlags"] = to_flags_val(0x1c)
    elif meta_font == 'smallSystemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontBold")
        item["NSSize"] = float(elem.attrib.get("size", 11.0))
        item["NSfFlags"] = to_flags_val(0x1d)
    elif meta_font == 'miniSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 9.0))
        item["NSfFlags"] = to_flags_val(0x1e)
    elif meta_font == 'cellTitle':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 12.0))
        item["NSfFlags"] = to_flags_val(0x13) | 0x1000
    elif meta_font == 'menu':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = to_flags_val(0x15)
    else:
        raise Exception(f"missing font {meta_font}")
    
    if key == "titleFont":
        parent.extraContext["titleFont"] = item
    else:
        parent["NSSupport"] = item
    return item
