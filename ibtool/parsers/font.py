from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> NibObject:
    item = NibObject("NSFont")
    meta_font = elem.attrib.get("metaFont")

    if meta_font is None:
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = 0x414
        if elem.attrib.get("usesAppearanceFont") == "YES":
            item["NSFontUsesAppearanceFontSize"] = True # does it apply to all?
    elif meta_font == 'system':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = 0x414
    elif meta_font == 'systemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontBold")
        item["NSSize"] = float(elem.attrib.get("size", 24.0))
        item["NSfFlags"] = 0x818
    elif meta_font == 'smallSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 11.0))
        item["NSfFlags"] = 0xc1c
    elif meta_font == 'smallSystemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontBold")
        item["NSSize"] = float(elem.attrib.get("size", 11.0))
        item["NSfFlags"] = 0xd1d
    elif meta_font == 'miniSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 9.0))
        item["NSfFlags"] = 0xe1e
    elif meta_font == 'cellTitle':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 12.0))
        item["NSfFlags"] = 0x1313
    elif meta_font == 'menu':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = 0x515
    else:
        raise Exception(f"missing font {meta_font}")
    parent["NSSupport"] = item
    return item
