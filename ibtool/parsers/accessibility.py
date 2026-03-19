from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent is not None

    description = elem.attrib.get("description")
    if description:
        ctx.accessibilityConnections.append((parent, description))
