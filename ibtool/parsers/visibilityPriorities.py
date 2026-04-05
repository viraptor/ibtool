from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    if hasattr(parent, 'extraContext'):
        parent.extraContext["has_visibility_priorities"] = True
