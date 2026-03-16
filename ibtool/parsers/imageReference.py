from ..models import ArchiveContext, NibObject, NibString, NibNil, NibNSNumber, NibList, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_image


SYMBOL_SCALE_MAP = {
    "default": -1,
    "small": 1,
    "medium": 2,
    "large": 3,
}


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    key = elem.attrib.get("key")
    image_name = elem.attrib.get("image", "")
    catalog = elem.attrib.get("catalog", "")

    if key and parent is not None and catalog == "system":
        if catalog:
            ctx.imageCatalog.setdefault(image_name, catalog)
        img = make_image(image_name, parent, ctx)

        variable_value = elem.attrib.get("variableValue")
        symbol_scale = elem.attrib.get("symbolScale")
        if variable_value is not None or symbol_scale is not None:
            config = NibObject("IBImageConfiguration", img)
            config["IBSymbolScale"] = SYMBOL_SCALE_MAP.get(symbol_scale, 0)
            config["IBRenderingMode"] = 0
            if variable_value is not None:
                config["IBVariableValue"] = NibNSNumber(float(variable_value))
                img["NSImageVariableValue"] = float(variable_value)
            config["IBHierarchicalColors"] = NibList([])
            config["IBLocale"] = NibNil()
            img["IBDesignImageConfiguration"] = config

        if key == "image":
            parent["NSImage"] = img
        elif key == "secondaryImage":
            parent["NSActionImage"] = img
            parent["NSHasActionImage"] = True
