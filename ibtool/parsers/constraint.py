from ..models import ArchiveContext, NibObject, XibObject, NibList, XibId, NibString
from xml.etree.ElementTree import Element
from typing import Optional, cast
from ..constants import ATTRIBUTE_MAP

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    first_attribute = elem.attrib["firstAttribute"]

    obj = XibObject(ctx, "NSLayoutConstraint", elem, parent)
    placeholder = elem.attrib.get("placeholder") == "YES"
    if placeholder:
        obj.extraContext["placeholder"] = True
    else:
        ctx.extraNibObjects.append(obj)
    obj["NSFirstAttribute"] = ATTRIBUTE_MAP[first_attribute]
    obj["NSFirstAttributeV2"] = ATTRIBUTE_MAP[first_attribute]
    if (second_attribute := elem.attrib.get("secondAttribute")) is not None:
        obj["NSSecondAttribute"] = ATTRIBUTE_MAP[second_attribute]
        obj["NSSecondAttributeV2"] = ATTRIBUTE_MAP[second_attribute]
    if (first_item := elem.attrib.get("firstItem")) is not None:
        obj["NSFirstItem"] = XibId(first_item)
    else:
        obj["NSFirstItem"] = parent
    if (second_item := elem.attrib.get("secondItem")) is not None:
        obj["NSSecondItem"] = XibId(second_item)
    if (relation := elem.attrib.get("relation")) is not None:
        obj["NSRelation"] = {"greaterThanOrEqual": 1, "lessThanOrEqual": 2}[relation]
    if placeholder:
        obj["NSRelation"] = -1
    if (priority := elem.attrib.get("priority")) is not None:
        obj["NSPriority"] = int(priority)

    symbolic = elem.attrib.get("symbolic") == "YES"
    if (constant := elem.attrib.get("constant")) is not None and symbolic is False:
        obj["NSConstant"] = float(constant)
        obj["NSConstantV2"] = float(constant)
    if symbolic:
        obj["NSSymbolicConstant"] = NibString.intern("NSSpace")
    obj["NSShouldBeArchived"] = True

    if not placeholder:
        parent.setIfEmpty("NSViewConstraints", NibList())
        ctx.constraints.append(obj)
        cast(NibList, parent["NSViewConstraints"]).addItem(obj)

