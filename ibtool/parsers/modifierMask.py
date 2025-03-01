from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    key = elem.attrib.get('key')
    if key == 'keyEquivalentModifierMask':
        parent.extraContext['keyEquivalentModifierMask'] = True
    else:
        raise Exception(f"unknown key {key}")
