from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    key = elem.attrib.get('key')
    if key == 'keyEquivalentModifierMask':
        parent.extraContext['keyEquivalentModifierMask'] = True
        mask = 0
        if elem.attrib.get('command') != 'NO':
            mask |= 0x100000
        if elem.attrib.get('control') == 'YES':
            mask |= 0x40000
        if elem.attrib.get('option') == 'YES':
            mask |= 0x80000
        if elem.attrib.get('shift') == 'YES':
            mask |= 0x20000
        if mask != 0x100000:
            parent.extraContext['keyEquivalentModifierMaskValue'] = mask
    else:
        raise Exception(f"unknown key {key}")
