from ..models import ArchiveContext, NibObject, XibObject, XibId, NibString, NibMutableDictionary, NibNSNumber
from xml.etree.ElementTree import Element
import ctypes
import ctypes.util
import sys

DATE_STYLE_MAP = {
    "none": 0,
    "short": 1,
    "medium": 2,
    "long": 3,
    "full": 4,
}

# ICU date format style constants (different from NSDateFormatterStyle!)
_ICU_STYLE = {
    "none": -1,   # UDAT_NONE
    "full": 0,    # UDAT_FULL
    "long": 1,    # UDAT_LONG
    "medium": 2,  # UDAT_MEDIUM
    "short": 3,   # UDAT_SHORT
}

_icu_lib = None
_icu_funcs = None

def _load_icu():
    global _icu_lib, _icu_funcs
    if _icu_funcs is not None:
        return _icu_funcs

    if sys.platform == 'darwin':
        lib_path = '/usr/lib/libicucore.dylib'
    else:
        lib_path = ctypes.util.find_library('icui18n')
    if not lib_path:
        raise RuntimeError("Could not find ICU library (libicui18n)")
    _icu_lib = ctypes.CDLL(lib_path)

    # Detect ICU version suffix (e.g., "_78")
    suffix = ""
    for ver in range(80, 50, -1):
        try:
            getattr(_icu_lib, f"udat_open_{ver}")
            suffix = f"_{ver}"
            break
        except AttributeError:
            continue

    udat_open = getattr(_icu_lib, f"udat_open{suffix}")
    udat_open.restype = ctypes.c_void_p
    udat_open.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                          ctypes.POINTER(ctypes.c_uint16), ctypes.c_int32,
                          ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int)]

    udat_toPattern = getattr(_icu_lib, f"udat_toPattern{suffix}")
    udat_toPattern.restype = ctypes.c_int32
    udat_toPattern.argtypes = [ctypes.c_void_p, ctypes.c_int,
                               ctypes.POINTER(ctypes.c_uint16), ctypes.c_int32,
                               ctypes.POINTER(ctypes.c_int)]

    udat_parse = getattr(_icu_lib, f"udat_parse{suffix}")
    udat_parse.restype = ctypes.c_double
    udat_parse.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16),
                           ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
                           ctypes.POINTER(ctypes.c_int)]

    udat_close = getattr(_icu_lib, f"udat_close{suffix}")
    udat_close.argtypes = [ctypes.c_void_p]

    _icu_funcs = {
        "open": udat_open,
        "toPattern": udat_toPattern,
        "parse": udat_parse,
        "close": udat_close,
    }
    return _icu_funcs


def _get_format_and_parse(date_style_str: str, time_style_str: str, title: str):
    """Get ICU format pattern and parse the title string as a date.
    Returns (format_string, nsdate_time) or None if ICU is unavailable."""
    funcs = _load_icu()
    if funcs is None:
        return None

    icu_date = _ICU_STYLE.get(date_style_str, -1)
    icu_time = _ICU_STYLE.get(time_style_str, -1)

    locale = b"en_AU" # no idea why this one matches, it should be overwritten
    tz = "Etc/UTC"
    tz_buf = (ctypes.c_uint16 * len(tz))(*[ord(c) for c in tz])

    status = ctypes.c_int(0)
    fmt = funcs["open"](icu_time, icu_date, locale, tz_buf, len(tz),
                        None, 0, ctypes.byref(status))
    if not fmt or status.value > 0:
        return None

    try:
        # Get pattern
        buf = (ctypes.c_uint16 * 256)()
        status2 = ctypes.c_int(0)
        length = funcs["toPattern"](fmt, 0, buf, 256, ctypes.byref(status2))
        pattern = ''.join(chr(buf[i]) for i in range(length))
        # Normalize short year format to match macOS ICU (yy -> y)
        import re
        pattern = re.sub(r'(?<![y])yy(?![y])', 'y', pattern)

        # Parse title as date
        nsdate_time = None
        if title:
            date_buf = (ctypes.c_uint16 * len(title))(*[ord(c) for c in title])
            parse_pos = ctypes.c_int32(0)
            parse_status = ctypes.c_int(0)
            timestamp = funcs["parse"](fmt, date_buf, len(title),
                                       ctypes.byref(parse_pos), ctypes.byref(parse_status))
            if parse_status.value <= 0 and parse_pos.value > 0:
                nsdate_time = (timestamp / 1000.0) - 978307200

        return (pattern, nsdate_time)
    finally:
        funcs["close"](fmt)


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    date_style_str = elem.attrib.get("dateStyle", "none")
    time_style_str = elem.attrib.get("timeStyle", "none")

    date_style_val = DATE_STYLE_MAP.get(date_style_str, 0)
    time_style_val = DATE_STYLE_MAP.get(time_style_str, 0)

    obj = XibObject(ctx, "NSDateFormatter", elem, parent)
    ctx.extraNibObjects.append(obj)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)

    date_style_num = NibNSNumber(date_style_val)
    time_style_num = date_style_num if date_style_val == time_style_val else NibNSNumber(time_style_val)
    attrs_items = [
        NibString.intern("dateStyle"), date_style_num,
    ]
    if elem.attrib.get("doesRelativeDateFormatting") == "YES":
        attrs_items.extend([NibString.intern("doesRelativeDateFormatting"), NibNSNumber(True)])
    attrs_items.extend([
        NibString.intern("formatterBehavior"), NibNSNumber(1040),
        NibString.intern("timeStyle"), time_style_num,
    ])
    attrs = NibMutableDictionary(attrs_items)

    # Get format pattern from ICU
    title = parent.get("NSContents")
    if title and hasattr(title, '_text'):
        title_str = title._text.decode('utf-8') if isinstance(title._text, bytes) else title._text
    else:
        title_str = None
    result = _get_format_and_parse(date_style_str, time_style_str, title_str)

    if result:
        format_str, nsdate_time = result
        obj["NS.format"] = NibString.intern(format_str)
        if nsdate_time is not None:
            date_obj = NibObject("NSDate", parent)
            date_obj["NS.time"] = nsdate_time
            parent["NSContents"] = date_obj
    else:
        obj["NS.format"] = NibString.intern("")

    obj["NS.attributes"] = attrs
    obj["NS.natural"] = False

    parent["NSFormatter"] = obj
