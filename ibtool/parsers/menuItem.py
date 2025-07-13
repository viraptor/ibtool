from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children
from ..constant_objects import MENU_MIXED_IMAGE, MENU_ON_IMAGE

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
    if not is_separator and (key_equiv or obj.extraContext.get('keyEquivalentModifierMaskValue')):
        obj["NSKeyEquivModMask"] = obj.extraContext.get('keyEquivalentModifierMaskValue', 0x100000)
    if tag := elem.attrib.get("tag"):
        obj["NSTag"] = int(tag)
    if elem.attrib.get("hidden"):
        obj["NSIsHidden"] = True
    if elem.attrib.get("enabled") == "NO" or is_separator:
        obj["NSIsDisabled"] = True
    return obj
