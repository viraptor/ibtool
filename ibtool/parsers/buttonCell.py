from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibDictionary, NibNSNumber
from xml.etree.ElementTree import Element
from ..parsers_base import parse_children
from .helpers import __xibparser_button_flags, __xibparser_cell_options, __xibparser_cell_flags
from ..constants import BEZEL_STYLE_MAP, CONTROL_SIZE_MAP2

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSButtonCell", elem, parent)
    ctx.extraNibObjects.append(obj)

    parse_children(ctx, elem, obj)
    if title := elem.attrib.get("title"):
        obj["NSContents"] = title
    else:
        obj["NSContents"] = NibString.intern('')
    button_type = elem.attrib.get("type", "push")
    if button_type == "radio":
        obj["NSAlternateImage"] = NibObject("NSButtonImageSource", None, {"NSImageName": "NSRadioButton"})
    elif button_type == "check":
        obj["NSAlternateImage"] = NibObject("NSButtonImageSource", None, {"NSImageName": "NSSwitch"})
    elif button_type == "inline" and obj.get("NSSupport"):
        obj["NSSupport"]["NSHasWidth"] = False
        obj["NSSupport"]["NSTextStyleDescriptor"] = NibObject("NSFontDescriptor", None, {
            "NSFontDescriptorOptions": 0x80008404,
            "NSFontDescriptorAttributes": NibDictionary([
                NibString.intern("NSCTFontSizeCategoryAttribute"),
                NibNSNumber(3),
                NibString.intern("NSCTFontUIUsageAttribute"),
                NibString.intern("UICTFontTextStyleEmphasizedSubhead"),
                NibString.intern("NSFontSizeAttribute"),
                NibNSNumber(11.0),
            ]),
        })
        obj["NSSupport"]["NSfFlags"] = 0x10
    else:
        obj["NSAlternateContents"] = NibString.intern('')

    if elem.attrib.get("image"):
        obj["NSNormalImage"] = NibNil() # TODO requires parsing embedded bplist
    obj.setIfEmpty("NSKeyEquivalent", NibString.intern(''))
    obj.setIfEmpty("NSAlternateContents", NibString.intern(''))
    obj["NSPeriodicDelay"] = 400
    obj["NSPeriodicInterval"] = 75
    obj["NSBezelStyle"] = BEZEL_STYLE_MAP.get(elem.attrib.get("bezelStyle"))
    __xibparser_button_flags(elem, obj, parent)
    obj["NSControlView"] = obj.xib_parent()

    key = elem.attrib.get("key")
    if key == "cell":
        __xibparser_cell_options(elem, obj, parent)
        obj.setIfEmpty("NSSupport", NibObject("NSFont", obj, {
            "NSName": ".AppleSystemUIFont",
            "NSSize": 13.0,
            "NSfFlags": 1044,
        }))

        obj.setIfEmpty("NSAuxButtonType", 7)
        parent["NSCell"] = obj
    elif key == "dataCell":
        __xibparser_cell_flags(elem, obj, parent)
        obj["NSControlSize2"] = CONTROL_SIZE_MAP2[elem.attrib.get("controlSize", "regular")]
        parent["NSDataCell"] = obj
    elif key == "prototype":
        __xibparser_cell_flags(elem, obj, parent)
        parent["NSProtoCell"] = obj
    elif key is None:
        __xibparser_cell_flags(elem, obj, parent)
    else:
        raise Exception(f"unexpected key {key}")

    return obj
