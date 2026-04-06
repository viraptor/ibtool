"""Text measurement using CoreText via ctypes (macOS only)."""
import ctypes
import ctypes.util
import math
from xml.etree.ElementTree import Element
from typing import Optional
from .constants import META_FONTS, DEFAULT_FONT_SIZE

_ct_path = ctypes.util.find_library('CoreText')
_cf_path = ctypes.util.find_library('CoreFoundation')

_available = _ct_path is not None and _cf_path is not None

if _available:
    _ct = ctypes.cdll.LoadLibrary(_ct_path)
    _cf = ctypes.cdll.LoadLibrary(_cf_path)

    _cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    _cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    _cf.CFStringCreateWithBytes.restype = ctypes.c_void_p
    _cf.CFStringCreateWithBytes.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32, ctypes.c_bool]
    _cf.CFRelease.argtypes = [ctypes.c_void_p]
    _cf.CFAttributedStringCreate.restype = ctypes.c_void_p
    _cf.CFAttributedStringCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    _cf.CFDictionaryCreate.restype = ctypes.c_void_p
    _cf.CFDictionaryCreate.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                        ctypes.POINTER(ctypes.c_void_p), ctypes.c_long,
                                        ctypes.c_void_p, ctypes.c_void_p]

    _ct.CTFontCreateWithName.restype = ctypes.c_void_p
    _ct.CTFontCreateWithName.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_void_p]
    _ct.CTLineCreateWithAttributedString.restype = ctypes.c_void_p
    _ct.CTLineCreateWithAttributedString.argtypes = [ctypes.c_void_p]
    _ct.CTLineGetTypographicBounds.restype = ctypes.c_double
    _ct.CTLineGetTypographicBounds.argtypes = [ctypes.c_void_p,
                                                ctypes.POINTER(ctypes.c_double),
                                                ctypes.POINTER(ctypes.c_double),
                                                ctypes.POINTER(ctypes.c_double)]

    _kCTFontAttributeName = ctypes.c_void_p.in_dll(_ct, 'kCTFontAttributeName')

    _font_cache: dict[float, ctypes.c_void_p] = {}

    def _get_font(size: float):
        if size not in _font_cache:
            name = _cf.CFStringCreateWithCString(None, b'.AppleSystemUIFont', 0x08000100)
            _font_cache[size] = _ct.CTFontCreateWithName(name, size, None)
            _cf.CFRelease(name)
        return _font_cache[size]

    def measure_text(text: str, font_size: float = 13.0) -> float:
        text_bytes = text.encode('utf-8')
        cf_str = _cf.CFStringCreateWithBytes(None, text_bytes, len(text_bytes), 0x08000100, False)
        font = _get_font(font_size)
        keys = (ctypes.c_void_p * 1)(_kCTFontAttributeName)
        vals = (ctypes.c_void_p * 1)(font)
        attrs = _cf.CFDictionaryCreate(None, keys, vals, 1, None, None)
        attr_str = _cf.CFAttributedStringCreate(None, cf_str, attrs)
        line = _ct.CTLineCreateWithAttributedString(attr_str)
        ascent = ctypes.c_double()
        descent = ctypes.c_double()
        leading = ctypes.c_double()
        width = _ct.CTLineGetTypographicBounds(line, ctypes.byref(ascent),
                                                ctypes.byref(descent), ctypes.byref(leading))
        _cf.CFRelease(line)
        _cf.CFRelease(attr_str)
        _cf.CFRelease(attrs)
        _cf.CFRelease(cf_str)
        return width

else:
    def measure_text(text: str, font_size: float = 13.0) -> float:
        raise RuntimeError("CoreText not available")


def _get_cell_elem(view_elem: Element) -> Optional[Element]:
    for child in view_elem:
        tag = child.tag
        if tag.endswith("Cell") and child.get("key") == "cell":
            return child
    return None


def _get_font_size(cell_or_view_elem: Element) -> float:
    for child in cell_or_view_elem:
        if child.tag == "font" and child.get("key") in ("font", None):
            meta = child.get("metaFont")
            if meta:
                if meta in META_FONTS:
                    return META_FONTS[meta][1]
                return DEFAULT_FONT_SIZE
            return float(child.get("size", DEFAULT_FONT_SIZE))
    return DEFAULT_FONT_SIZE


def _has_width_constraint(view_elem: Element) -> Optional[float]:
    for child in view_elem:
        if child.tag == "constraints":
            for c in child:
                if (c.tag == "constraint" and c.get("firstAttribute") == "width"
                        and c.get("secondItem") is None):
                    return float(c.get("constant", 0))
    return None


def _is_hidden(view_elem: Element) -> bool:
    return view_elem.get("hidden") == "YES"


def compute_intrinsic_width(view_elem: Element) -> Optional[int]:
    """Compute intrinsic content width for a view XML element.
    Returns None if intrinsic width cannot be determined."""
    if not _available:
        return None

    width_constraint = _has_width_constraint(view_elem)
    if width_constraint is not None:
        return int(width_constraint)

    tag = view_elem.tag

    if tag == "button":
        cell = _get_cell_elem(view_elem)
        if cell is None:
            return None
        title = cell.get("title", "")
        font_size = _get_font_size(cell)
        text_w = math.ceil(measure_text(title, font_size))
        cell_type = cell.get("type", "push")
        has_image = cell.get("image") is not None
        if cell_type == "check" or cell_type == "radio":
            return text_w + 22
        elif cell_type == "push":
            if has_image:
                return text_w + 50
            return text_w + 24
        return None

    if tag == "popUpButton":
        cell = _get_cell_elem(view_elem)
        if cell is None:
            return None
        title = cell.get("title", "")
        font_size = _get_font_size(cell)
        text_w = math.ceil(measure_text(title, font_size))
        return text_w + 48

    if tag == "textField":
        cell = _get_cell_elem(view_elem)
        if cell is None:
            return None
        # Only compute for label-style text fields (no bezel, not editable)
        if cell.get("scrollable") == "YES" or cell.get("editable") == "YES":
            return None
        title = cell.get("title", "")
        font_size = _get_font_size(cell)
        text_w = math.ceil(measure_text(title, font_size))
        return text_w + 4

    if tag == "stackView":
        return _compute_stack_intrinsic_width(view_elem)

    return None


def _compute_stack_intrinsic_width(sv_elem: Element) -> Optional[int]:
    orientation = sv_elem.get("orientation", "horizontal")
    spacing = float(sv_elem.get("spacing", 8.0))
    detaches = sv_elem.get("detachesHiddenViews", "NO") == "YES"

    children = []
    subviews_elem = None
    for child in sv_elem:
        if child.tag == "subviews":
            subviews_elem = child
            break
    if subviews_elem is None:
        return 0

    for child in subviews_elem:
        if child.tag in ("constraint", "constraints"):
            continue
        if _is_hidden(child) and detaches:
            continue
        if _is_hidden(child):
            continue
        iw = compute_intrinsic_width(child)
        if iw is None:
            return None
        children.append(iw)

    if not children:
        return 0

    if orientation == "horizontal":
        return sum(children) + int(spacing * (len(children) - 1))
    else:
        return max(children)
