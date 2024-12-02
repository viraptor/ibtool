from .models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
import importlib


def __xibparser_ParseXIBObject(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], all_parsers={}) -> NibObject:
    if not all_parsers:
        all_parsers = importlib.import_module(".parsers", __package__).all

    tag = elem.tag
    parsefn = all_parsers[tag].parse
    # print("----- PARSETHING:", tag, parsefn)
    if parsefn:
        obj = parsefn(ctx, elem, parent)
        if obj and isinstance(obj, XibObject):
            if elem.attrib.get("id") == None:
                raise Exception(f"Unknown id for {elem} (parent {parent})")
            ctx.addObject(obj.xibid, obj)
        return obj
    else:
        raise Exception(f"Unknown type {tag}")

def parse_children(ctx: ArchiveContext, elem: Element, obj: Optional[NibObject]) -> list[NibObject]:
    assert obj is not None
    # Constraints are always added after other elements. It may not matter, but that's what Apple's tool does and it helps in comparisons
    children = [
        __xibparser_ParseXIBObject(ctx, child_element, obj) for child_element in elem if child_element.tag != "constraints"
    ] + [
        __xibparser_ParseXIBObject(ctx, child_element, obj) for child_element in elem if child_element.tag == "constraints"
    ]
    return [c for c in children if c]
