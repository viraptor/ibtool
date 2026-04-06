from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element
from ..constants import FontFlags, META_FONTS, DEFAULT_FONT_SIZE, DEFAULT_SYSTEM_FONT_NAME

def to_flags_val(x):
    return ((x<<8) & 0xf00) | (x & 0xff)

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> NibObject:
    item = NibObject("NSFont")
    meta_font = elem.attrib.get("metaFont")
    key = elem.attrib.get("key")

    if meta_font is None:
        item["NSName"] = NibString.intern(elem.attrib.get("name", DEFAULT_SYSTEM_FONT_NAME))
        item["NSSize"] = float(elem.attrib.get("size", DEFAULT_FONT_SIZE))
        if "name" in elem.attrib:
            flags = FontFlags.ROLE_CONTROL_CONTENT_FONT.value
        else:
            flags = FontFlags.ROLE_LABEL_FONT.value
        item["NSfFlags"] = to_flags_val(flags)
        if elem.attrib.get("usesAppearanceFont") == "YES":
            item["NSFontUsesAppearanceFontSize"] = True # does it apply to all?
    elif meta_font in META_FONTS:
        name, default_size, role = META_FONTS[meta_font]
        item["NSName"] = NibString.intern(name)
        item["NSSize"] = float(elem.attrib.get("size", default_size))
        flags = to_flags_val(role.value)
        if meta_font == "cellTitle":
            flags |= 0x1000
        item["NSfFlags"] = flags
    else:
        raise Exception(f"missing font {meta_font}")
    
    if key == "titleFont":
        parent.extraContext["titleFont"] = item
    elif parent.originalclassname() == "NSTabView":
        parent["NSFont"] = item
    else:
        parent["NSSupport"] = item
    return item
