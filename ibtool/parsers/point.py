from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(_ctx: ArchiveContext, elem: Element, _parent: NibObject) -> None:
    point = (float(elem.attrib["x"]), float(elem.attrib["y"]))
    if elem.attrib.get("key") == "canvasLocation":
        pass # only useful for the designer
    else:
        raise Exception(f"unknown point key {elem.attrib.get('key')}")
