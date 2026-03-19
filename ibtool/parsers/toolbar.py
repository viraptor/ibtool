from ..models import ArchiveContext, NibObject, NibNil, NibString, NibList, NibMutableList, NibMutableDictionary, NibNSNumber, XibObject
from ..constant_objects import GENERIC_GREY_COLOR_SPACE
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element

DISPLAY_MODE_MAP = {
    "iconAndLabel": 1,
    "iconOnly": 2,
    "labelOnly": 3,
}

SIZE_MODE_MAP = {
    "regular": 1,
    "small": 2,
}

STANDARD_ITEMS = {
    "NSToolbarShowFontsItem": {
        "class": "NSToolbarItem",
        "label": "Fonts",
        "paletteLabel": "Fonts",
        "toolTip": "Show Font Panel",
        "bordered": True,
        "action": "orderFrontFontPanel:",
        "minSize": "{36, 24}",
        "maxSize": "{36, 24}",
        "imageName": "textformat",
        "imageSize": "{19, 12}",
        "imageAlignmentRect": "{{0, 0.083333333333333329}, {1, 0.75}}",
    },
    "NSToolbarPrintItem": {
        "class": "NSToolbarItem",
        "label": "Print",
        "paletteLabel": "Print",
        "toolTip": "Print",
        "bordered": True,
        "action": "printDocument:",
        "minSize": "{35, 24}",
        "maxSize": "{35, 24}",
        "imageName": "printer",
        "imageSize": "{19, 16}",
        "imageAlignmentRect": "{{0, 0.1875}, {1, 0.5625}}",
    },
    "NSToolbarSpaceItem": {
        "class": "NSToolbarSpaceItem",
        "label": "",
        "paletteLabel": "Space",
        "toolTip": None,
        "bordered": False,
        "action": None,
        "minSize": "{8, 24}",
        "maxSize": "{8, 24}",
        "hasSeparatorMenu": True,
    },
    "NSToolbarFlexibleSpaceItem": {
        "class": "NSToolbarFlexibleSpaceItem",
        "label": "",
        "paletteLabel": "Flexible Space",
        "toolTip": None,
        "bordered": False,
        "action": None,
        "minSize": "{8, 24}",
        "maxSize": "{20000, 24}",
        "hasSeparatorMenu": True,
    },
}


def _make_toolbar_image(name, size_str, alignment_rect_str, toolbar):
    color = NibObject("NSColor", None, {
        "NSColorSpace": 3,
        "NSWhite": b'0 0\x00',
        "NSCustomColorSpace": GENERIC_GREY_COLOR_SPACE,
        "NSComponents": b'0 0',
        "NSLinearExposure": b'1',
    })
    img = NibObject("NSImage", toolbar)
    img["NSImageFlags"] = 0x20c00000
    img["NSSize"] = NibString.intern(size_str)
    inner_array = NibList([NibNSNumber(6), NibString.intern(name), NibNSNumber(False)])
    img["NSReps"] = NibList([inner_array])
    img["NSColor"] = color
    img["NSAlignmentRectInNormalizedCoordinates"] = NibString.intern(alignment_rect_str)
    img["NSIsTemplate"] = True
    img["NSResizingMode"] = 0
    img["NSTintColor"] = NibNil()
    return img


def _make_separator_menu_item(toolbar):
    item = NibObject("NSMenuItem", toolbar)
    item["NSIsDisabled"] = True
    item["NSIsSeparator"] = True
    item["NSAllowsKeyEquivalentLocalization"] = True
    item["NSAllowsKeyEquivalentMirroring"] = True
    item["NSTitle"] = NibString.intern("")
    item["NSKeyEquiv"] = NibString.intern("")
    return item


def _make_standard_item(identifier, info, toolbar, ctx):
    classname = info["class"]
    item = NibObject(classname, toolbar)
    ctx.extraNibObjects.append(item)
    item["NSToolbarItemIdentifier"] = NibString.intern(identifier)
    item["NSToolbarItemLabel"] = NibString.intern(info["label"])
    item["NSToolbarItemPaletteLabel"] = NibString.intern(info["paletteLabel"])
    if info["toolTip"] is not None:
        item["NSToolbarItemToolTip"] = NibString.intern(info["toolTip"])
    else:
        item["NSToolbarItemToolTip"] = NibNil()
    item["NSToolbarItemView"] = NibNil()
    item["NSToolbarItemBordered"] = info["bordered"]
    if "imageName" in info:
        item["NSToolbarItemImage"] = _make_toolbar_image(
            info["imageName"], info["imageSize"], info["imageAlignmentRect"], toolbar)
    else:
        item["NSToolbarItemImage"] = NibNil()
    item["NSToolbarItemTitle"] = NibString.intern("")
    item["NSToolbarItemTarget"] = NibNil()
    if info["action"] is not None:
        item["NSToolbarItemAction"] = NibString.intern(info["action"])
    else:
        item["NSToolbarItemAction"] = NibNil()
    item["NSToolbarItemMinSize"] = NibString.intern(info["minSize"])
    item["NSToolbarItemMaxSize"] = NibString.intern(info["maxSize"])
    item["NSToolbarItemIgnoreMinMaxSizes"] = False
    item["NSToolbarItemEnabled"] = True
    item["NSToolbarItemAutovalidates"] = True
    item["NSToolbarItemTag"] = -1
    item["NSToolbarItemVisibilityPriority"] = 0
    item["NSToolbarItemNavigational"] = False
    if info.get("hasSeparatorMenu"):
        item["NSToolbarItemMenuFormRepresentation"] = _make_separator_menu_item(toolbar)
    item["NSToolbarIsUserRemovable"] = True
    item["NSToolbarItemStyle"] = 0
    return item


def _make_custom_item(ctx, elem, toolbar):
    identifier = elem.attrib.get("implicitItemIdentifier", "")
    custom_class = elem.attrib.get("customClass")
    classname = "NSToolbarItem"

    item = XibObject(ctx, classname, elem, None)
    if item.xibid is not None:
        ctx.addObject(item.xibid, item)
    ctx.extraNibObjects.append(item)

    item["NSToolbarItemIdentifier"] = NibString.intern(identifier)
    item["NSToolbarItemLabel"] = NibString.intern(elem.attrib.get("label", ""))
    item["NSToolbarItemPaletteLabel"] = NibString.intern(elem.attrib.get("paletteLabel", ""))

    view_elem = None
    min_size = None
    max_size = None
    for child in elem:
        if child.tag == "nil" and child.attrib.get("key") == "toolTip":
            item["NSToolbarItemToolTip"] = NibNil()
        elif child.tag == "size":
            key = child.attrib.get("key")
            size_str = f'{{{child.attrib["width"]}, {child.attrib["height"]}}}'
            if key == "minSize":
                min_size = size_str
            elif key == "maxSize":
                max_size = size_str
        elif child.attrib.get("key") == "view":
            view_elem = child
        elif child.tag == "connections":
            from . import connections as connections_mod
            connections_mod.parse(ctx, child, item)

    item.setIfEmpty("NSToolbarItemToolTip", NibNil())

    if view_elem is not None:
        from ..parsers_base import __xibparser_ParseXIBObject
        view_obj = __xibparser_ParseXIBObject(ctx, view_elem, None)
        item["NSToolbarItemView"] = view_obj
    else:
        item["NSToolbarItemView"] = NibNil()

    item["NSToolbarItemBordered"] = False

    image_name = elem.attrib.get("image")
    if image_name:
        from .helpers import make_image
        img = make_image(image_name, item, ctx)
        item["NSToolbarItemImage"] = img
        item["NSToolbarItemBordered"] = True
    else:
        item["NSToolbarItemImage"] = NibNil()

    item["NSToolbarItemTitle"] = NibString.intern("")
    item["NSToolbarItemTarget"] = NibNil()
    item["NSToolbarItemAction"] = NibNil()
    if min_size:
        item["NSToolbarItemMinSize"] = NibString.intern(min_size)
    else:
        item["NSToolbarItemMinSize"] = NibString.intern("{0, 0}")
    if max_size:
        item["NSToolbarItemMaxSize"] = NibString.intern(max_size)
    else:
        item["NSToolbarItemMaxSize"] = NibString.intern("{0, 0}")
    item["NSToolbarItemIgnoreMinMaxSizes"] = False
    item["NSToolbarItemEnabled"] = True
    item["NSToolbarItemAutovalidates"] = True
    item["NSToolbarItemTag"] = 0
    item["NSToolbarItemVisibilityPriority"] = 0
    item["NSToolbarItemNavigational"] = False
    item["NSToolbarIsUserRemovable"] = True
    item["NSToolbarItemStyle"] = 0

    if custom_class:
        item["NSOriginalClassName"] = NibString.intern("NSToolbarItem")
        item.setclassname("NSClassSwapper")
        item["NSClassName"] = NibString.intern(custom_class)

    return identifier, item


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    toolbar = NibObject("NSToolbar", parent)
    ctx.extraNibObjects.append(toolbar)

    identifier = elem.attrib.get("explicitIdentifier", elem.attrib.get("implicitIdentifier", ""))
    toolbar["NSToolbarIdentifier"] = NibString.intern(identifier)
    toolbar["NSToolbarDelegate"] = NibNil()
    toolbar["NSToolbarPrefersToBeShown"] = True
    toolbar["NSToolbarAllowsUserCustomization"] = True
    toolbar["NSToolbarAutosavesConfiguration"] = True
    toolbar["NSToolbarDisplayMode"] = DISPLAY_MODE_MAP.get(elem.attrib.get("displayMode"), 0)
    toolbar["NSToolbarSizeMode"] = SIZE_MODE_MAP.get(elem.attrib.get("sizeMode"), 0)
    toolbar["NSToolbarCenteredItemIdentifier"] = NibNil()

    identified_items = {}
    allowed_items = []
    default_items = []

    for section in elem:
        if section.tag == "allowedToolbarItems":
            for child in section:
                if child.tag != "toolbarItem":
                    continue
                ref = child.attrib.get("reference")
                if ref:
                    obj = ctx.getObject(ref)
                    if obj:
                        allowed_items.append(obj)
                    continue

                implicit_id = child.attrib.get("implicitItemIdentifier", "")
                if implicit_id in STANDARD_ITEMS:
                    info = STANDARD_ITEMS[implicit_id]
                    item = _make_standard_item(implicit_id, info, toolbar, ctx)
                    if child.attrib.get("id"):
                        ctx.addObject(child.attrib["id"], item)
                    identified_items[implicit_id] = item
                    allowed_items.append(item)
                else:
                    item_id, item = _make_custom_item(ctx, child, toolbar)
                    identified_items[item_id] = item
                    allowed_items.append(item)

        elif section.tag == "defaultToolbarItems":
            for child in section:
                if child.tag != "toolbarItem":
                    continue
                ref = child.attrib.get("reference")
                if ref:
                    obj = ctx.getObject(ref)
                    if obj:
                        default_items.append(obj)

    dict_items = []
    for item_id, item in identified_items.items():
        dict_items.append(NibString.intern(item_id))
        dict_items.append(item)
    toolbar["NSToolbarIBIdentifiedItems"] = NibMutableDictionary(dict_items)
    toolbar["NSToolbarIBAllowedItems"] = NibList(allowed_items)
    toolbar["NSToolbarIBDefaultItems"] = NibList(default_items)
    toolbar["NSToolbarIBSelectableItems"] = NibMutableList()

    parent["NSViewClass"] = toolbar
