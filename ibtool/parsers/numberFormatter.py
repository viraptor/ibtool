from ..models import ArchiveContext, NibObject, XibObject, NibString, NibInlineString, NibNSNumber, NibMutableDictionary, NibNil
from xml.etree.ElementTree import Element


def _build_format_string(min_int_digits, max_int_digits, min_frac_digits, max_frac_digits, uses_grouping=False, grouping_size=0):
    min_int = min_int_digits
    if uses_grouping and grouping_size > 0:
        # ICU-style grouping: #,##0 pattern (single grouping indicator)
        zeros = '0' * min_int
        if len(zeros) <= grouping_size:
            int_part = '#,##' + zeros if len(zeros) < grouping_size else '#,' + zeros
        else:
            int_part = '#,' + zeros
    else:
        capped_max = min(max_int_digits, 42)
        hash_count = max(capped_max - min_int, 0)
        int_part = '#' * hash_count + '0' * min_int
    fmt = int_part
    if min_frac_digits > 0 or max_frac_digits > 0:
        fmt += '.' + '0' * min_frac_digits + '#' * max(max_frac_digits - min_frac_digits, 0)
    return fmt


def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    allows_floats = elem.attrib.get("allowsFloats", "YES") == "YES"
    number_style = elem.attrib.get("numberStyle")
    is_decimal = number_style == "decimal"
    uses_grouping = elem.attrib.get("usesGroupingSeparator", "YES" if is_decimal else "NO") == "YES"
    grouping_size = int(elem.attrib.get("groupingSize", "3" if is_decimal else "0"))
    min_int_digits = int(elem.attrib.get("minimumIntegerDigits", "0"))
    max_int_digits = int(elem.attrib.get("maximumIntegerDigits", "42"))
    min_frac_digits = int(elem.attrib.get("minimumFractionDigits", "0"))
    max_frac_digits = int(elem.attrib.get("maximumFractionDigits", "0"))
    format_width = int(elem.attrib.get("formatWidth", "0"))

    minimum = None
    maximum = None
    has_nil_neg_infinity = False
    has_nil_pos_infinity = False

    for child in elem:
        key = child.attrib.get("key")
        if child.tag == "integer" and key == "minimum":
            minimum = NibNSNumber(int(child.attrib["value"]))
        elif child.tag == "real" and key == "minimum":
            minimum = NibNSNumber(float(child.attrib["value"]))
        elif child.tag == "integer" and key == "maximum":
            maximum = NibNSNumber(int(child.attrib["value"]))
        elif child.tag == "real" and key == "maximum":
            maximum = NibNSNumber(float(child.attrib["value"]))
        elif child.tag == "nil" and key == "negativeInfinitySymbol":
            has_nil_neg_infinity = True
        elif child.tag == "nil" and key == "positiveInfinitySymbol":
            has_nil_pos_infinity = True

    has_explicit_min = minimum is not None
    has_explicit_max = maximum is not None
    _DECIMAL_PLACEHOLDER = lambda: NibObject("NSDecimalNumberPlaceholder", None, {
        "NS.exponent": 0, "NS.length": 0, "NS.negative": True,
        "NS.compact": False, "NS.mantissa": NibInlineString(b'\x00' * 16), "NS.mantissa.bo": 1,
    })
    if minimum is None:
        minimum = _DECIMAL_PLACEHOLDER()
    if maximum is None:
        maximum = _DECIMAL_PLACEHOLDER()

    obj = XibObject(ctx, "NSNumberFormatter", elem, parent)
    ctx.extraNibObjects.append(obj)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)

    format_str = _build_format_string(min_int_digits, max_int_digits, min_frac_digits, max_frac_digits, uses_grouping, grouping_size)

    currency_symbol = elem.attrib.get("currencySymbol")
    intl_currency_symbol = elem.attrib.get("internationalCurrencySymbol")
    positive_format = elem.attrib.get("positiveFormat")
    negative_format = elem.attrib.get("negativeFormat")
    lenient = elem.attrib.get("lenient", "NO") == "YES"

    attrs_items = [
        NibString.intern("allowsFloats"), NibNSNumber(allows_floats),
        NibString.intern("alwaysShowsDecimalSeparator"), NibNSNumber(False),
    ]

    if currency_symbol is not None:
        attrs_items.extend([
            NibString.intern("currencySymbol"), NibString.intern(currency_symbol),
        ])

    attrs_items.extend([
        NibString.intern("formatWidth"), NibNSNumber(format_width),
        NibString.intern("formatterBehavior"), NibNSNumber(1040),
        NibString.intern("generatesDecimalNumbers"), NibNSNumber(False),
        NibString.intern("groupingSize"), NibNSNumber(grouping_size),
    ])

    if intl_currency_symbol is not None:
        attrs_items.extend([
            NibString.intern("internationalCurrencySymbol"), NibString.intern(intl_currency_symbol),
        ])

    attrs_items.extend([
        NibString.intern("lenient"), NibNSNumber(lenient),
    ])
    if has_explicit_max:
        attrs_items.extend([NibString.intern("maximum"), maximum])
    attrs_items.extend([
        NibString.intern("maximumFractionDigits"), NibNSNumber(max_frac_digits),
        NibString.intern("maximumIntegerDigits"), NibNSNumber(max_int_digits),
    ])
    if has_explicit_min:
        attrs_items.extend([NibString.intern("minimum"), minimum])
    attrs_items.extend([
        NibString.intern("minimumFractionDigits"), NibNSNumber(min_frac_digits),
        NibString.intern("minimumIntegerDigits"), NibNSNumber(min_int_digits),
    ])

    if negative_format is not None:
        attrs_items.extend([
            NibString.intern("negativeFormat"), NibString.intern(negative_format),
        ])

    if not has_nil_neg_infinity:
        attrs_items.extend([
            NibString.intern("negativeInfinitySymbol"), NibString.intern("-\u221e"),
        ])

    attrs_items.extend([
        NibString.intern("nilSymbol"), NibString.intern(""),
    ])

    _NUMBER_STYLE_MAP = {"none": 0, "decimal": 1, "currency": 2, "percent": 3, "scientific": 4, "spellOut": 5}
    if number_style is not None:
        attrs_items.extend([NibString.intern("numberStyle"), NibNSNumber(_NUMBER_STYLE_MAP.get(number_style, 0))])

    attrs_items.extend([
        NibString.intern("paddingPosition"), NibNSNumber(0),
    ])

    if positive_format is not None:
        attrs_items.extend([
            NibString.intern("positiveFormat"), NibString.intern(positive_format),
        ])

    if not has_nil_pos_infinity:
        attrs_items.extend([
            NibString.intern("positiveInfinitySymbol"), NibString.intern("+\u221e"),
        ])

    attrs_items.extend([
        NibString.intern("roundingMode"), NibNSNumber(4),
        NibString.intern("secondaryGroupingSize"), NibNSNumber(0),
        NibString.intern("usesGroupingSeparator"), NibNSNumber(uses_grouping),
    ])

    attrs = NibMutableDictionary(attrs_items)

    # NS.nan: NSAttributedString with "NaN" and empty NSDictionary attributes
    nan_str = NibObject("NSAttributedString")
    nan_str["NSString"] = NibString.intern("NaN")
    nan_attrs = NibObject("NSDictionary")
    nan_attrs["NSInlinedValue"] = True
    nan_str["NSAttributes"] = nan_attrs

    # NS.nil: NSAttributedString with empty string
    nil_str = NibObject("NSAttributedString")
    nil_str["NSString"] = NibString.intern("")

    # NS.rounding: NSDecimalNumberHandler
    rounding = NibObject("NSDecimalNumberHandler")
    rounding["NS.roundingmode"] = 3
    rounding["NS.raise.underflow"] = True
    rounding["NS.raise.overflow"] = True
    rounding["NS.raise.dividebyzero"] = True

    pos_format_str = positive_format if positive_format is not None else format_str
    neg_format_str = negative_format if negative_format is not None else format_str

    obj["NS.allowsfloats"] = allows_floats
    obj["NS.attributes"] = attrs
    obj["NS.decimal"] = NibString.intern(".")
    obj["NS.hasthousands"] = uses_grouping
    obj["NS.localized"] = True
    obj["NS.max"] = maximum
    obj["NS.min"] = minimum
    obj["NS.nan"] = nan_str
    obj["NS.negativeattrs"] = NibNil()
    obj["NS.negativeformat"] = NibString.intern(neg_format_str)
    obj["NS.nil"] = nil_str
    obj["NS.positiveattrs"] = NibNil()
    obj["NS.positiveformat"] = NibString.intern(pos_format_str)
    obj["NS.rounding"] = rounding
    obj["NS.thousand"] = NibString.intern(",")
    obj["NS.zero"] = NibNil()

    parent["NSFormatter"] = obj
    if parent.extraContext.get("key") == "cell":
        contents = parent.get("NSContents")
        if isinstance(contents, NibString) and contents._text == "":
            del parent["NSContents"]
