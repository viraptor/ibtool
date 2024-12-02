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
    if elem.attrib.get("keyEquivalentModifierMask") is not None or key_equiv:
        obj["NSKeyEquivModMask"] = 0x100000
    obj["NSMixedImage"] = MENU_MIXED_IMAGE
    obj["NSMnemonicLoc"] = 0x7fffffff
    obj["NSOnImage"] = MENU_ON_IMAGE
    obj["NSTitle"] = NibString.intern(elem.attrib.get("title", ""))
    if elem.attrib.get("isSeparatorItem") == "YES":
        obj["NSIsSeparator"] = True
        obj["NSIsDisabled"] = True
    if tag := elem.attrib.get("tag"):
        obj["NSTag"] = int(tag)
    if elem.attrib.get("hidden"):
        obj["NSIsHidden"] = True
    return obj
