from ..models import ArchiveContext, NibObject
from xml.etree.ElementTree import Element
from ..constants import EventModifierFlags

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    key = elem.attrib.get('key')
    if key == 'keyEquivalentModifierMask':
        parent.extraContext['keyEquivalentModifierMask'] = True
        has_explicit_modifiers = any(k != 'key' for k in elem.attrib)
        if has_explicit_modifiers:
            mask = 0
            if elem.attrib.get('command') == 'YES':
                mask |= EventModifierFlags.COMMAND
            if elem.attrib.get('control') == 'YES':
                mask |= EventModifierFlags.CONTROL
            if elem.attrib.get('option') == 'YES':
                mask |= EventModifierFlags.OPTION
            if elem.attrib.get('shift') == 'YES':
                mask |= EventModifierFlags.SHIFT
            parent.extraContext['keyEquivalentModifierMaskValue'] = mask
    else:
        raise Exception(f"unknown key {key}")
