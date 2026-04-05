from ..models import ArchiveContext, NibObject, NibNSNumber
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    if not hasattr(parent, 'extraContext'):
        return
    priorities = []
    for child in elem:
        if child.tag == "integer":
            priorities.append(int(child.attrib.get("value", "1000")))
        elif child.tag == "real":
            priorities.append(int(float(child.attrib.get("value", "1000"))))
    parent.extraContext["visibility_priorities"] = priorities
