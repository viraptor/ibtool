from ..models import ArchiveContext, NibObject, XibObject, NibInlineString
from xml.etree.ElementTree import Element
from .helpers import makeSystemColor, NibInlineString
from ..constants import CellFlags
from ..constant_objects import GENERIC_GREY_COLOR_SPACE

def _strip_dot_if_int(s: str) -> str:
    s_val = float(s)
    return str(int(s_val)) if int(s_val) == s_val else f'{s_val:.12}'

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert isinstance(parent, XibObject) or isinstance(parent, NibObject), type(parent)
    assert elem.attrib["colorSpace"] in ["catalog", "calibratedWhite", "calibratedRGB"], elem.attrib["colorSpace"]

    key = elem.attrib["key"]

    special_target_attributes = { # weird and standard attributes
        "NSView": {
            "backgroundColor": None,
        },
        "NSClipView": {
            "backgroundColor": ["NSBGColor"],
        },
        "NSTextView": {
            "backgroundColor": ["NSSharedData", "NSBackgroundColor"],
            "insertionPointColor": ["NSSharedData", "NSInsertionColor"],
            "textColor": ["NSTextViewTextColor"],
        },
        "NSMatrix": {
            "backgroundColor": ["NSBackgroundColor"],
        },
        None: {
            "textColor": ["NSTextColor"],
            "backgroundColor": ["NSBackgroundColor"],
            "insertionPointColor": ["NSInsertionPointColor"],
            "gridColor": ["NSGridColor"],
            "color": ["NSColor"],
        }
    }

    target_path = special_target_attributes.get(parent.originalclassname(), special_target_attributes[None])[key]
    if target_path is None:
        return
    target_obj = parent
    for step in target_path[:-1]:
        target_obj = target_obj[step]
    target_attribute = target_path[-1]

    if elem.attrib["colorSpace"] == "catalog":
        assert elem.attrib["catalog"] == "System", elem.attrib["catalog"]

        # hack - does it generalize to other types of cells?
        if parent.originalclassname() == "NSTextFieldCell" and elem.attrib["name"] == "textColor" and parent["NSCellFlags"] & CellFlags.EDITABLE:
            colorName = 'controlTextColor'
        else:
            colorName = elem.attrib["name"]
        color = makeSystemColor(colorName)
        target_obj[target_attribute] = color
    elif elem.attrib["colorSpace"] == "calibratedWhite":
        if ctx.toolsVersion <= 11762:
            parent_is_clip_view = parent.originalclassname() == "NSClipView"
            attr_white = float(elem.attrib["white"])
            if parent_is_clip_view:
                attr_white = attr_white * 0.602715373
            if attr_white.is_integer():
                attr_white = int(attr_white)
                white = f'{attr_white} {elem.attrib["alpha"]:.12}\x00' if 'alpha' in elem.attrib and elem.attrib["alpha"] != "1" else f'{attr_white}\x00'
            else:
                white = f'{attr_white:.12} {elem.attrib["alpha"]:.12}\x00' if 'alpha' in elem.attrib and elem.attrib["alpha"] != "1" else f'{attr_white:.12}\x00'
            color = NibObject("NSColor", None, {
                "NSColorSpace": 6,
                "NSCatalogName": "System",
                "NSColorName": {
                    "NSClipView": "controlBackgroundColor",
                    "NSTextView": "textBackgroundColor",
                }[parent.originalclassname()],
                "NSColor": NibObject("NSColor", None, {
                    "NSColorSpace": 3,
                    "NSComponents": NibInlineString(b'0.6666666667 1' if parent_is_clip_view else b'1 1'),
                    "NSCustomColorSpace": GENERIC_GREY_COLOR_SPACE,
                    "NSWhite": NibInlineString(white),
                }),
            })
        else:
            white = f'{elem.attrib["white"]:.12} {elem.attrib["alpha"]:.12}\x00' if 'alpha' in elem.attrib and elem.attrib["alpha"] != "1" else f'{elem.attrib["white"]:.12}\x00'
            color = NibObject("NSColor", None, {
                "NSColorSpace": 3,
                "NSWhite": NibInlineString(white),
            })
        target_obj[target_attribute] = color
    elif elem.attrib["colorSpace"] == "calibratedRGB":
        red = _strip_dot_if_int(elem.attrib["red"])
        green = _strip_dot_if_int(elem.attrib["green"])
        blue = _strip_dot_if_int(elem.attrib["blue"])
        alpha = _strip_dot_if_int(elem.attrib["alpha"])
        color = NibObject("NSColor", None, {
            "NSColorSpace": 1,
            "NSRGB": NibInlineString(f"{red} {green} {blue}\x00") if alpha == "1" else f"{red} {green} {blue} {alpha}\x00",
        })
        target_obj[target_attribute] = color
    else:
        raise Exception(f"unknown colorSpace {elem.attrib['colorSpace']}")
