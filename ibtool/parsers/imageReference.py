from ..models import ArchiveContext, NibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_image


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    key = elem.attrib.get("key")
    image_name = elem.attrib.get("image", "")
    catalog = elem.attrib.get("catalog", "")

    if key and parent is not None and catalog == "system":
        if catalog:
            ctx.imageCatalog.setdefault(image_name, catalog)
        img = make_image(image_name, parent, ctx)

        if key == "image":
            parent["NSImage"] = img
        elif key == "secondaryImage":
            parent["NSActionImage"] = img
            parent["NSHasActionImage"] = True
