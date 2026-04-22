"""Convert XIB custom-colorSpace sRGB components to calibrated RGB via
CoreGraphics. Apple's NIB stores these colors in the calibrated (generic)
RGB color space with a CGColorSpace named kCGColorSpaceSRGB attached, so
the numeric NSRGB payload needs to be matched by CG's rendering intent
logic."""
from typing import Optional
import ctypes
import ctypes.util

_cg = None
_srgb_cs: Optional[int] = None
_generic_cs: Optional[int] = None


def _init() -> bool:
    global _cg, _srgb_cs, _generic_cs
    if _cg is not None:
        return _srgb_cs is not None
    cg_path = ctypes.util.find_library("CoreGraphics")
    cf_path = ctypes.util.find_library("CoreFoundation")
    if not cg_path or not cf_path:
        _cg = False
        return False
    _cg = ctypes.CDLL(cg_path)
    cf = ctypes.CDLL(cf_path)
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    _cg.CGColorSpaceCreateWithName.restype = ctypes.c_void_p
    _cg.CGColorSpaceCreateWithName.argtypes = [ctypes.c_void_p]
    _cg.CGColorCreate.restype = ctypes.c_void_p
    _cg.CGColorCreate.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double)]
    _cg.CGColorCreateCopyByMatchingToColorSpace.restype = ctypes.c_void_p
    _cg.CGColorCreateCopyByMatchingToColorSpace.argtypes = [
        ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p]
    _cg.CGColorGetNumberOfComponents.restype = ctypes.c_size_t
    _cg.CGColorGetNumberOfComponents.argtypes = [ctypes.c_void_p]
    _cg.CGColorGetComponents.restype = ctypes.POINTER(ctypes.c_double)
    _cg.CGColorGetComponents.argtypes = [ctypes.c_void_p]
    srgb_name = cf.CFStringCreateWithCString(None, b"kCGColorSpaceSRGB", 0x08000100)
    generic_name = cf.CFStringCreateWithCString(None, b"kCGColorSpaceGenericRGB", 0x08000100)
    _srgb_cs = _cg.CGColorSpaceCreateWithName(srgb_name)
    _generic_cs = _cg.CGColorSpaceCreateWithName(generic_name)
    return _srgb_cs is not None


def srgb_to_calibrated_rgb(r: float, g: float, b: float, a: float) -> Optional[tuple[float, float, float, float]]:
    """Match an sRGB colour into macOS's generic ("calibrated") RGB color
    space; returns the four-component tuple CG produces, or None if
    CoreGraphics is not loadable."""
    if not _init():
        return None
    comps = (ctypes.c_double * 4)(r, g, b, a)
    src = _cg.CGColorCreate(_srgb_cs, comps)
    if not src:
        return None
    dst = _cg.CGColorCreateCopyByMatchingToColorSpace(_generic_cs, 0, src, None)
    if not dst:
        return None
    n = _cg.CGColorGetNumberOfComponents(dst)
    out = _cg.CGColorGetComponents(dst)
    return tuple(out[i] for i in range(n))
