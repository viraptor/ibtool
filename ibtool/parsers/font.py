from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> NibObject:
    item = NibObject("NSFont")
    meta_font = elem.attrib.get("metaFont")

    if meta_font is None:
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = 0x414
    elif meta_font == 'system':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = 1044
    elif meta_font == 'systemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontBold")
        item["NSSize"] = float(elem.attrib.get("size", 24.0))
        item["NSfFlags"] = 2072
    elif meta_font == 'smallSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 11.0))
        item["NSfFlags"] = 3100
    elif meta_font == 'smallSystemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontDemi")
        item["NSSize"] = float(elem.attrib.get("size", 11.0))
        item["NSfFlags"] = 3357
    elif meta_font == 'miniSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 9.0))
        item["NSfFlags"] = 3614
    elif meta_font == 'cellTitle':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 12.0))
        item["NSfFlags"] = 4883
    elif meta_font == 'menu':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = float(elem.attrib.get("size", 13.0))
        item["NSfFlags"] = 0x515
    else:
        raise Exception(f"missing font {meta_font}")
    parent["NSSupport"] = item
    return item
