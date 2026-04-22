from ..models import ArchiveContext, XibObject, NibString, NibNil
from xml.etree.ElementTree import Element
from ..constants import vFlags
from ..parsers_base import parse_children
from .helpers import (
    parse_interfacebuilder_properties,
    _xibparser_common_view_attributes,
    _xibparser_common_translate_autoresizing,
)

BLENDING_MODES = {
    "behindWindow": 0,
    "withinWindow": 1,
}

MATERIALS = {
    "appearanceBased": 0,
    "light": 1,
    "dark": 2,
    "titlebar": 3,
    "selection": 4,
    "menu": 5,
    "popover": 6,
    "sidebar": 7,
    "mediumLight": 8,
    "ultraDark": 9,
    "headerView": 10,
    "sheet": 11,
    "windowBackground": 12,
    "hudWindow": 13,
    "fullScreenUI": 15,
    "toolTip": 17,
    "contentBackground": 18,
    "underWindowBackground": 21,
    "underPageBackground": 22,
}

STATES = {
    "followsWindowActiveState": 0,
    "active": 1,
    "inactive": 2,
}


def parse(ctx: ArchiveContext, elem: Element, parent: XibObject) -> XibObject:
    obj = XibObject(ctx, "NSVisualEffectView", elem, parent)
    ctx.extraNibObjects.append(obj)
    obj.setrepr(elem)
    obj["NSSuperview"] = obj.xib_parent()

    parse_interfacebuilder_properties(ctx, elem, parent, obj)
    parse_children(ctx, elem, obj)

    _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(parent is None))
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    blending = elem.attrib.get("blendingMode")
    if blending in BLENDING_MODES:
        obj["NSVisualEffectViewBlendingMode"] = BLENDING_MODES[blending]
    material = elem.attrib.get("material")
    if material in MATERIALS:
        obj["NSVisualEffectViewMaterial"] = MATERIALS[material]
        obj["IBVisualEffectViewExternalMaterial"] = MATERIALS[material]
    state = elem.attrib.get("state")
    if state in STATES:
        obj["NSVisualEffectViewState"] = STATES[state]
    obj["IBVisualEffectViewAppearanceType"] = 0
    obj["NSVisualEffectViewMaskImage"] = NibNil()

    return obj
