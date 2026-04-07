"""Static table of system NSImage sizes.

Apple's ibtool overrides XIB-declared image dimensions for system images (e.g.
NSRefreshTemplate) with the actual on-disk size from AppKit's image cache. The
table below was generated once via the AppKit Objective-C runtime and is checked
in so we don't need a live system at compile time. NIBs are forwards-compatible
across macOS versions, so these sizes are stable in practice.

To regenerate or extend the table, run:

    python -m ibtool.system_images NSImageName1 NSImageName2 ...

which queries [NSImage imageNamed:] via libobjc and prints entries.
"""
from typing import Optional

SYSTEM_IMAGE_SIZES: dict[str, tuple[int, int]] = {
    "NSActionTemplate": (19, 19),
    "NSAddTemplate": (18, 16),
    "NSAdvanced": (32, 32),
    "NSApplicationIcon": (128, 128),
    "NSBluetoothTemplate": (16, 20),
    "NSBonjour": (32, 32),
    "NSBookmarksTemplate": (22, 17),
    "NSCaution": (32, 32),
    "NSColorPanel": (32, 32),
    "NSComputer": (32, 32),
    "NSEnterFullScreenTemplate": (20, 18),
    "NSEveryone": (32, 32),
    "NSExitFullScreenTemplate": (20, 19),
    "NSFolder": (32, 32),
    "NSFolderBurnable": (32, 32),
    "NSFolderSmart": (32, 32),
    "NSFontPanel": (32, 32),
    "NSGoLeftTemplate": (12, 16),
    "NSGoRightTemplate": (12, 16),
    "NSHomeTemplate": (24, 20),
    "NSIChatTheaterTemplate": (15, 13),
    "NSInfo": (32, 32),
    "NSInvalidDataFreestandingTemplate": (19, 19),
    "NSLeftFacingTriangleTemplate": (12, 16),
    "NSListViewTemplate": (21, 14),
    "NSLockLockedTemplate": (16, 18),
    "NSLockUnlockedTemplate": (21, 18),
    "NSMenuCheckmark": (18, 16),
    "NSMenuMixedState": (18, 4),
    "NSMobileMe": (32, 32),
    "NSMultipleDocuments": (32, 32),
    "NSNetwork": (32, 32),
    "NSPathTemplate": (25, 14),
    "NSPreferencesGeneral": (32, 32),
    "NSQuickLookTemplate": (27, 16),
    "NSRefreshTemplate": (17, 20),
    "NSRemoveTemplate": (18, 4),
    "NSRevealFreestandingTemplate": (19, 19),
    "NSRightFacingTriangleTemplate": (12, 16),
    "NSShareTemplate": (19, 22),
    "NSSlideshowTemplate": (24, 17),
    "NSSmartBadgeTemplate": (14, 14),
    "NSStatusAvailable": (16, 16),
    "NSStatusNone": (16, 16),
    "NSStatusPartiallyAvailable": (16, 16),
    "NSStatusUnavailable": (16, 16),
    "NSStopProgressFreestandingTemplate": (19, 19),
    "NSStopProgressTemplate": (17, 15),
    "NSTrashEmpty": (32, 32),
    "NSTrashFull": (32, 32),
    "NSUser": (32, 32),
    "NSUserAccounts": (32, 32),
    "NSUserGroup": (32, 32),
    "NSUserGuest": (32, 32),
}


def system_image_size(name: str) -> Optional[tuple[int, int]]:
    return SYSTEM_IMAGE_SIZES.get(name)


def _query_runtime(name: str) -> Optional[tuple[int, int]]:
    """Query [NSImage imageNamed:].size via libobjc. Used to extend the table."""
    import ctypes
    import ctypes.util

    class _CGSize(ctypes.Structure):
        _fields_ = [("w", ctypes.c_double), ("h", ctypes.c_double)]

    objc_path = ctypes.util.find_library("objc")
    appkit_path = ctypes.util.find_library("AppKit")
    if not objc_path or not appkit_path:
        return None
    objc = ctypes.CDLL(objc_path)
    ctypes.CDLL(appkit_path)
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    NSImage = objc.objc_getClass(b"NSImage")
    NSString = objc.objc_getClass(b"NSString")
    sel_imageNamed = objc.sel_registerName(b"imageNamed:")
    sel_size = objc.sel_registerName(b"size")
    sel_str = objc.sel_registerName(b"stringWithUTF8String:")
    str_fn = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p))
    img_fn = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))
    size_fn = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(
        _CGSize, ctypes.c_void_p, ctypes.c_void_p))

    ns_name = str_fn(NSString, sel_str, name.encode("utf-8"))
    if not ns_name:
        return None
    img = img_fn(NSImage, sel_imageNamed, ns_name)
    if not img:
        return None
    sz = size_fn(img, sel_size)
    if sz.w <= 0 or sz.h <= 0:
        return None
    return (int(sz.w), int(sz.h))


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:]:
        sz = _query_runtime(name)
        if sz is not None:
            print(f'    "{name}": ({sz[0]}, {sz[1]}),')
        else:
            print(f"# {name}: not found", file=sys.stderr)
