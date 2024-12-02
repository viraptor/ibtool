from ..parsers_base import parse_children
from ..models import ArchiveContext, NibObject, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from ..constants import WTFlags
from typing import Union

def calculate_window_rect(struts: dict[str, bool], content_rect: tuple[int, int, int, int], screen_rect: tuple[int, int, int, int]) -> tuple[Union[int,float], ...]:
    if screen_rect == (0, 0, 0, 0):
        return content_rect
    res = (
        content_rect[0] if struts.get("left") else screen_rect[2]/2 - content_rect[2]/2,
        content_rect[1] if struts.get("bottom") else screen_rect[3]/2 - content_rect[3]/2,
        content_rect[2],
        content_rect[3],
        )
    return tuple(int(x) if x==int(x) else x for x in res)

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    item = XibObject(ctx, "NSWindowTemplate", elem, parent)
    ctx.extraNibObjects.append(item)
    item.flagsOr("NSWTFlags", 0x780000) # default initial position mask, can be overriden by children

    parse_children(ctx, elem, item)
    item["NSWindowBacking"] = 2
    if not item.extraContext.get("NSWindowRect"):
        item.extraContext["NSWindowRect"] = (0, 0, 0, 0)

    item.flagsOr("NSWTFlags", WTFlags.DEFER)
    if elem.attrib.get("allowsToolTipsWhenApplicationIsInactive", "YES") == "YES":
        item.flagsOr("NSWTFlags", WTFlags.ALLOWS_TOOL_TIPS_WHEN_APPLICATION_IS_INACTIVE)
    if elem.attrib.get("autorecalculatesKeyViewLoop", "YES") == "YES":
        item.flagsOr("NSWTFlags", WTFlags.AUTORECALCULATES_KEY_VIEW_LOOP)
    if elem.attrib.get("releasedWhenClosed", "YES") == "NO":
        item.flagsOr("NSWTFlags", WTFlags.RELEASED_WHEN_CLOSED)

    item["NSWindowTitle"] = NibString.intern(elem.attrib.get("title", ''))
    item["NSWindowSubtitle"] = ""
    item["NSWindowClass"] = item.get("NSClassName") or NibString.intern("NSWindow")
    if item.get("NSClassName"):
        del item["NSClassName"]
    item["NSViewClass"] = NibNil() # TODO
    item["NSUserInterfaceItemIdentifier"] = NibNil() # TODO
    if not item.get("NSWindowView"):
        item["NSWindowView"] = NibNil()
    if not item.extraContext.get("NSScreenRect"):
        item.extraContext["NSScreenRect"] = (0, 0, 0, 0)
    item.setIfEmpty("NSMaxSize", '{10000000000000, 10000000000000}')
    item["NSWindowIsRestorable"] = elem.attrib.get("restorable", "YES") == "YES"
    item["NSMinFullScreenContentSize"] = NibString.intern('{0, 0}')
    item["NSMaxFullScreenContentSize"] = NibString.intern('{0, 0}')
    if elem.attrib.get("tabbingMode"):
        item["NSWindowTabbingMode"] = {"disallowed": 2}[elem.attrib["tabbingMode"]]
    if elem.attrib.get("visibleAtLaunch", "YES") == "YES":
        ctx.visibleWindows.append(item)
    if frame_autosave_name := elem.attrib.get("frameAutosaveName"):
        item["NSFrameAutosaveName"] = NibString.intern(frame_autosave_name)

    # fixup the rects
    if item.extraContext.get("NSWindowRect"):
        content_rect = item.extraContext["NSWindowRect"]
        screen_rect = item.extraContext["NSScreenRect"]
        item.extraContext["NSWindowRect"] = calculate_window_rect(item.extraContext.get("initialPositionMask", {}), content_rect, screen_rect)
        item["NSWindowRect"] = "{{" + str(item.extraContext["NSWindowRect"][0]) + ", " + str(item.extraContext["NSWindowRect"][1]) + "}, {" + str(item.extraContext["NSWindowRect"][2]) + ", " + str(item.extraContext["NSWindowRect"][3]) + "}}"
    if item.extraContext.get("NSScreenRect"):
        item["NSScreenRect"] = "{{" + str(item.extraContext["NSScreenRect"][0]) + ", " + str(item.extraContext["NSScreenRect"][1]) + "}, {" + str(item.extraContext["NSScreenRect"][2]) + ", " + str(item.extraContext["NSScreenRect"][3]) + "}}"

    return item
