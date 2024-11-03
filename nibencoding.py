import struct

NIB_TYPE_BYTE = 0x00
NIB_TYPE_SHORT = 0x01
NIB_TYPE_LONG = 0x02
NIB_TYPE_FALSE = 0x04
NIB_TYPE_TRUE = 0x05
NIB_TYPE_FLOAT = 0x06
NIB_TYPE_DOUBLE = 0x07
NIB_TYPE_STRING = 0x08  # Can also be used for tuples. e.g. CGPoint/Size/Rect
NIB_TYPE_OBJECT = 0x0A


# Input: Tuple of the four nib components. (Objects, Keys, Values, Classes)
# Output: A byte array containing the binary representation of the nib archive.
def WriteNib(nib):
    b = bytearray()
    b.extend(b"NIBArchive")
    b.extend([1, 0, 0, 0])
    b.extend([9, 0, 0, 0])

    objs = nib[0]
    keys = nib[1]
    vals = nib[2]
    clss = nib[3]

    objs_section = _nibWriteObjectsSection(objs)
    keys_section = _nibWriteKeysSection(keys)
    vals_section = _nibWriteValuesSection(vals)
    clss_section = _nibWriteClassesSection(clss)

    header_size = 50
    objs_start = header_size
    keys_start = objs_start + len(objs_section)
    vals_start = keys_start + len(keys_section)
    clss_start = vals_start + len(vals_section)

    for num in [
        len(objs),
        objs_start,
        len(keys),
        keys_start,
        len(vals),
        vals_start,
        len(clss),
        clss_start,
    ]:
        b.extend(struct.pack("<I", num))

    b.extend(objs_section)
    b.extend(keys_section)
    b.extend(vals_section)
    b.extend(clss_section)

    return b


def _nibWriteFlexNumber(btarray, number):
    cur_byte = 0
    while True:
        cur_byte = number & 0x7F
        number = number >> 7
        if not number:
            break
        btarray.append(cur_byte)
    cur_byte |= 0x80
    btarray.append(cur_byte)


def _nibWriteObjectsSection(objects):
    b = bytearray()
    for obj in objects:
        _nibWriteFlexNumber(b, obj[0])
        _nibWriteFlexNumber(b, obj[1])
        _nibWriteFlexNumber(b, obj[2])
    return b


def _nibWriteKeysSection(keys):
    b = bytearray()
    for key in keys:
        # print(key)
        _nibWriteFlexNumber(b, len(key))
        b.extend(key.encode("utf-8"))
    return b


def _nibWriteClassesSection(classes):
    b = bytearray()
    for cls in classes:
        _nibWriteFlexNumber(b, len(cls) + 1)
        b.append(0x80)
        b.extend(cls.encode("utf-8"))
        b.append(0x00)
    return b


def _nibWriteValuesSection(values):
    b = bytearray()
    for value in values:
        keyidx = value[0]
        encoding_type = value[1]
        _nibWriteFlexNumber(b, keyidx)
        b.append(encoding_type)

        if encoding_type == NIB_TYPE_FALSE:
            continue
        if encoding_type == NIB_TYPE_TRUE:
            continue
        if encoding_type == NIB_TYPE_OBJECT:
            try:
                b.extend(struct.pack("<I", value[2]))
            except struct.error:
                print("Encoding object not in object list:", value[3])
                raise
            continue
        if encoding_type == NIB_TYPE_FLOAT:
            b.extend(struct.pack("<f", value[2]))
            continue
        if encoding_type == NIB_TYPE_BYTE:
            b.append(value[2])
            continue
        if encoding_type == NIB_TYPE_SHORT:
            b.extend(struct.pack("<H", value[2]))
            continue
        if encoding_type == NIB_TYPE_LONG:
            b.extend(struct.pack("<I", value[2]))
            continue
        if (
            encoding_type == NIB_TYPE_STRING
        ):  # TODO struct support (Nibs use this encoding for CGRect)
            v = value[2]
            if isinstance(v, str):
                v = v.encode("utf-8")
            _nibWriteFlexNumber(b, len(v))
            b.extend(v)
            continue
        if encoding_type == NIB_TYPE_DOUBLE:
            b.extend(struct.pack("<d", value[2]))
            continue

        raise Exception("Bad encoding type: " + str(encoding_type))

    return b
