from ..models import ArchiveContext, NibObject, NibString, NibDictionary, NibNSNumber
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import __xibparser_cell_flags
from ..parsers_base import parse_children
from ..constants import CONTROL_SIZE_MAP2

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibObject:
    assert parent is not None
    assert parent.originalclassname() == "NSTableColumn"

    obj = NibObject("NSTableHeaderCell", parent)

    parse_children(ctx, elem, obj)
    __xibparser_cell_flags(elem, obj, parent)
    obj["NSContents"] = NibString.intern(elem.attrib.get("title", ''))
    obj["NSControlSize2"] = CONTROL_SIZE_MAP2[elem.attrib.get("controlSize", "regular")]
    obj.setIfEmpty("NSSupport", NibObject("NSFont", obj, {
        "NSName": ".AppleSystemUIFont",
        "NSSize": 11.0,
        "NSfFlags": 16,
        "NSHasWidth": False,
        "NSTextStyleDescriptor": NibObject("NSFontDescriptor", None, {
            "NSFontDescriptorAttributes": NibDictionary([
                NibString.intern("NSCTFontSizeCategoryAttribute"),
                NibNSNumber(3),
                NibString.intern("NSCTFontUIUsageAttribute"),
                NibString.intern("UICTFontTextStyleSubhead"),
                NibString.intern("NSFontSizeAttribute"),
                NibNSNumber(11.0),
            ]),
            "NSFontDescriptorOptions": 0x80008404,
        }),
    }))
    parent["NSHeaderCell"] = obj

    return obj
