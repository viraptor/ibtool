from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children
from ..constant_objects import MENU_MIXED_IMAGE, MENU_ON_IMAGE

STATES = {
    "on": 1,
    None: None,
}

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSMenuItem", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)
    if parent and parent.originalclassname() == "NSMenu":
        obj["NSMenu"] = parent
    obj["NSAllowsKeyEquivalentLocalization"] = True
    obj["NSAllowsKeyEquivalentMirroring"] = True
    obj["NSHiddenInRepresentation"] = False
    if (key_equiv := elem.attrib.get("keyEquivalent")) is not None:
        obj["NSKeyEquiv"] = NibString.intern(key_equiv)
    else:
        obj["NSKeyEquiv"] = NibString.intern('')
    obj["NSMixedImage"] = MENU_MIXED_IMAGE
    obj["NSMnemonicLoc"] = 0x7fffffff
    obj["NSOnImage"] = MENU_ON_IMAGE
    obj["NSTitle"] = NibString.intern(elem.attrib.get("title", ""))
    if (is_separator := elem.attrib.get("isSeparatorItem") == "YES"):
        obj["NSIsSeparator"] = True
    if obj.extraContext.get('keyEquivalentModifierMaskValue') is not None:
        obj["NSKeyEquivModMask"] = obj.extraContext['keyEquivalentModifierMaskValue']
    elif not is_separator and not obj.extraContext.get('keyEquivalentModifierMask'):
        obj["NSKeyEquivModMask"] = 0x100000
    if tag := elem.attrib.get("tag"):
        obj["NSTag"] = int(tag)
    if elem.attrib.get("hidden"):
        obj["NSIsHidden"] = True
    if elem.attrib.get("enabled") == "NO" or is_separator:
        obj["NSIsDisabled"] = True
    obj.setIfNotDefault("NSState", STATES[elem.attrib.get("state")], None)
    if image_name := elem.attrib.get("image"):
        image = NibObject("NSCustomResource", obj)
        image["NSResourceName"] = NibString.intern(image_name)
        image["NSClassName"] = NibString.intern("NSImage")
        image["IBNamespaceID"] = NibString.intern("system")
        design_size = NibObject("NSValue", obj)
        design_size["NS.sizeval"] = NibString.intern("{32, 32}")
        design_size["NS.special"] = 2
        image["IBDesignSize"] = design_size
        image["IBDesignImageConfiguration"] = NibNil()
        obj["NSImage"] = image
    return obj
