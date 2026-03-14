from ..models import ArchiveContext, NibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    key = elem.attrib.get("key")
    image_name = elem.attrib.get("image", "")
    catalog = elem.attrib.get("catalog", "")

    if key and parent is not None and catalog == "system":
        img = NibObject("NSCustomResource")
        img["NSClassName"] = NibString.intern("NSImage")
        img["NSResourceName"] = NibString.intern(image_name)
        img["NSCatalogName"] = NibString.intern("system")

        prop_name = {
            "image": "NSImage",
            "secondaryImage": "NSAlternateImage",
        }.get(key)
        if prop_name:
            parent[prop_name] = img
