"""Parser for the legacy Interface Builder 3 'archive' XIB format.

These files use a keyed-archive XML schema (root element <archive>) that is
effectively a direct serialization of NSCoding-style objects. Compared to the
modern <document>-based XIB format, the node names and keys already match the
NIB-native class and property names, so parsing is mostly mechanical.

Schema notes:

- <object class="X" id="Y"> defines an object of class X with id Y.
- <array class="X" key="K"> or <array key="K"> is a list property.
- <string>, <int>, <integer>, <bool>, <real>, <bytes>, <nil> are scalar values.
- <reference ref="id"/> points to an already-declared object.
- Dictionaries use the NSMutableDictionary form: children are pairs of keys
  named "NS.key.N" and "NS.object.N".
"""
from typing import Optional

from xml.etree.ElementTree import Element

from .models import (
    NibObject,
    NibString,
    NibNil,
    NibData,
    NibMutableList,
    NibMutableSet,
    NibMutableDictionary,
    NibInlineString,
)


def parse_archive(root: Element) -> NibObject:
    raise NotImplementedError("archive XIB parsing not yet implemented")
