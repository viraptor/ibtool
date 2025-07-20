from ..models import ArchiveContext, NibObject, NibString
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    key = elem.attrib["key"]
    if key == "maxSize":
        parent["NSMaxSize"] = f'{{{elem.attrib["width"]}, {elem.attrib["height"]}}}'
    elif key == "intercellSpacing":
        width = elem.attrib.get("width")
        height = elem.attrib.get("height")
        if parent.originalclassname() == "NSMatrix":
            parent["NSIntercellSpacing"] = NibString.intern(f"{{{width}, {height}}}")
        else:
            if (width := elem.attrib.get("width")) is not None:
                parent["NSIntercellSpacingWidth"] = float(width)
            if (height := elem.attrib.get("height")) is not None:
                parent["NSIntercellSpacingHeight"] = float(height)
    elif key == "cellSize":
        parent["NSCellSize"] = f'{{{elem.attrib["width"]}, {elem.attrib["height"]}}}'
    else:
        raise Exception(f"Unknown key {key}")
    parent.extraContext[elem.attrib["key"]] = (elem.attrib["width"], elem.attrib["height"])
