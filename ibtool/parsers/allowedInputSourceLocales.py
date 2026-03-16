from ..models import ArchiveContext, NibObject, NibString, NibList, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    if parent is None:
        return
    strings = []
    for s in elem.findall("string"):
        if s.text:
            strings.append(NibString.intern(s.text))
    if strings:
        if parent.originalclassname() == "NSSecureTextFieldCell":
            parent["NSAllowedInputLocales"] = NibList(strings)
        else:
            parent["NSAllowedInputLocales"] = NibMutableList(strings)
