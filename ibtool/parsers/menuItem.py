from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil, NibLocalizableString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, make_image
from ..parsers_base import parse_children
from ..constant_objects import MENU_MIXED_IMAGE, MENU_ON_IMAGE
from ..constants import NSNotFound, EventModifierFlags

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
    obj["NSMnemonicLoc"] = NSNotFound
    obj["NSOnImage"] = MENU_ON_IMAGE
    title = elem.attrib.get("title", "")
    is_separator = elem.attrib.get("isSeparatorItem") == "YES"
    if ctx.isBaseLocalization and not is_separator:
        obj["NSTitle"] = NibLocalizableString(title, key=f"{elem.attrib.get('id', '')}.title")
    else:
        obj["NSTitle"] = NibString.intern(title)
    if (is_separator := elem.attrib.get("isSeparatorItem") == "YES"):
        obj["NSIsSeparator"] = True
    if obj.extraContext.get('keyEquivalentModifierMaskValue') is not None:
        obj["NSKeyEquivModMask"] = obj.extraContext['keyEquivalentModifierMaskValue']
    elif not is_separator and not obj.extraContext.get('keyEquivalentModifierMask'):
        obj["NSKeyEquivModMask"] = EventModifierFlags.COMMAND
    if tag := elem.attrib.get("tag"):
        obj["NSTag"] = int(tag)
    if elem.attrib.get("hidden"):
        obj["NSIsHidden"] = True
    if elem.attrib.get("enabled") == "NO" or is_separator:
        obj["NSIsDisabled"] = True
    obj.setIfNotDefault("NSState", STATES[elem.attrib.get("state")], None)
    if image_name := elem.attrib.get("image"):
        obj["NSImage"] = make_image(image_name, obj, ctx)
    if secondary_image := elem.attrib.get("secondaryImage"):
        catalog = elem.attrib.get("catalog")
        if catalog:
            ctx.imageCatalog.setdefault(secondary_image, catalog)
        obj["NSActionImage"] = make_image(secondary_image, obj, ctx)
        obj["NSHasActionImage"] = True
    if elem.attrib.get("alternate") == "YES":
        obj["NSIsAlternate"] = True
    return obj
