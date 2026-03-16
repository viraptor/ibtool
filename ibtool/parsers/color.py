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
    assert elem.attrib["colorSpace"] in ["catalog", "calibratedWhite", "calibratedRGB", "deviceRGB"], elem.attrib["colorSpace"]

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

        colorName = elem.attrib["name"]
        color = makeSystemColor(colorName)
        target_obj[target_attribute] = color
    elif elem.attrib["colorSpace"] == "calibratedWhite":
        if ctx.toolsVersion <= 14268:
            parent_is_clip_view = parent.originalclassname() == "NSClipView"
            is_window_content_clip_view = parent_is_clip_view and isinstance(parent, XibObject) and parent.extraContext.get("is_window_content_view")
            # Determine if this should be a system color or simple white
            use_system_color = False
            if parent.originalclassname() == "NSTextView":
                use_system_color = True
            elif parent_is_clip_view and not is_window_content_clip_view:
                # NSDocView isn't set yet during parse_children, check NSSubviews instead
                subviews = parent.get("NSSubviews")
                first_subview = subviews[0] if subviews and len(subviews) > 0 else None
                if first_subview is not None and first_subview.originalclassname() == "NSTextView":
                    use_system_color = True
            attr_white = float(elem.attrib["white"])
            if use_system_color and parent_is_clip_view:
                attr_white = attr_white * 0.602715373
            if attr_white.is_integer():
                attr_white = int(attr_white)
                white = f'{attr_white} {elem.attrib["alpha"]:.12}\x00' if 'alpha' in elem.attrib and elem.attrib["alpha"] != "1" else f'{attr_white}\x00'
            else:
                white = f'{attr_white:.12} {elem.attrib["alpha"]:.12}\x00' if 'alpha' in elem.attrib and elem.attrib["alpha"] != "1" else f'{attr_white:.12}\x00'
            if not use_system_color:
                color = NibObject("NSColor", None, {
                    "NSColorSpace": 3,
                    "NSWhite": NibInlineString(white),
                })
            else:
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
                        "NSLinearExposure": NibInlineString(b'1'),
                    }),
                })
        else:
            white_f = float(elem.attrib["white"])
            white = f'{white_f:.10} {float(elem.attrib["alpha"]):.10}\x00' if 'alpha' in elem.attrib and elem.attrib["alpha"] != "1" else f'{white_f:.10}\x00'
            color = NibObject("NSColor", None, {
                "NSColorSpace": 3,
                "NSWhite": NibInlineString(white),
            })
        target_obj[target_attribute] = color
    elif elem.attrib["colorSpace"] in ("calibratedRGB", "deviceRGB"):
        color_space_id = 1 if elem.attrib["colorSpace"] == "calibratedRGB" else 2
        red = _strip_dot_if_int(elem.attrib["red"])
        green = _strip_dot_if_int(elem.attrib["green"])
        blue = _strip_dot_if_int(elem.attrib["blue"])
        alpha = _strip_dot_if_int(elem.attrib["alpha"])
        color = NibObject("NSColor", None, {
            "NSColorSpace": color_space_id,
            "NSRGB": NibInlineString(f"{red} {green} {blue}\x00") if alpha == "1" else f"{red} {green} {blue} {alpha}\x00",
        })
        target_obj[target_attribute] = color
    else:
        raise Exception(f"unknown colorSpace {elem.attrib['colorSpace']}")
