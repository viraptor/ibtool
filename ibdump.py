#!/usr/bin/python

import struct
import sys


def rword(b):
    return struct.unpack("<I", b)[0]


def rquad(b):
    return struct.unpack("<q", b)[0]


def rdouble(b):
    return struct.unpack("<d", b)[0]


def rsingle(b):
    return struct.unpack("<f", b)[0]


# Reads a flexible number from the bytes array and returns a tuple
# containing the number read and the number of bytes read.
def readFlexNumber(b, addr):
    number = 0
    shift = 0
    ptr = addr
    while True:
        num = b[ptr]
        ptr += 1

        number |= (num & 0x7F) << shift
        shift += 7

        if num & 0x80:
            break
        if shift > 30:
            raise Exception("Flex number invalid or too large.")
    return (number, ptr - addr)


def readHeader(b, start):
    hsize = rword(b[start : start + 4])
    # print("Header size (words):", str(hsize))
    sections = []
    sectionDataStart = start + 4
    for section in range((hsize - 1) // 2):
        objcount = rword(
            b[sectionDataStart + section * 8 : sectionDataStart + section * 8 + 4]
        )
        address = rword(
            b[sectionDataStart + section * 8 + 4 : sectionDataStart + section * 8 + 8]
        )
        sections += [(objcount, address)]
    return sections


def readKeys(b, keysSection):
    count, ptr = keysSection
    keys = []
    for i in range(count):
        rd = readFlexNumber(b, ptr)
        length = rd[0]
        ptr += rd[1]

        keys.append(b[ptr : ptr + length].decode('utf-8'))
        ptr += length
    return keys


def readObjects(b, objectsSection):
    count, ptr = objectsSection
    objects = []
    for i in range(count):
        r0 = readFlexNumber(b, ptr)
        r1 = readFlexNumber(b, ptr + r0[1])
        r2 = readFlexNumber(b, ptr + r0[1] + r1[1])

        class_idx = r0[0]
        start_idx = r1[0]
        size = r2[0]

        ptr += r0[1] + r1[1] + r2[1]

        objects.append((class_idx, start_idx, size))
    return objects


def readClasses(b, classSection):
    count, addr = classSection
    classes = []
    ptr = addr
    for i in range(count):
        r = readFlexNumber(b, ptr)
        length = r[0]
        ptr += r[1]

        tp = b[ptr]
        ptr += 1

        unknown = None
        assert tp in [0x80, 0x81]
        if tp == 0x81:
            unknown = rword(b[ptr : ptr + 4])
            ptr += 4
            print("readClasses: Mystery value:", unknown, "(", end=" ")

        classes.append(b[ptr : ptr + length - 1].decode('utf-8'))

        if unknown:
            print(classes[-1], ")")

        ptr += length

    return classes


def readValues(b, valuesSection, debugKeys=None):
    if debugKeys is None:
        debugKeys = []

    count, addr = valuesSection
    values = []
    ptr = addr
    for i in range(count):
        r = readFlexNumber(b, ptr)
        key_idx = r[0]
        ptr += r[1]

        encoding = b[ptr]
        ptr += 1

        value = None
        if encoding == 0x00:  # single byte
            value = b[ptr]
            ptr += 1
        elif encoding == 0x01:  # short
            value = struct.unpack("<H", b[ptr : ptr + 2])[0]
            ptr += 2
        elif encoding == 0x02:  # 4 byte integer
            value = struct.unpack("<I", b[ptr : ptr + 4])[0]
            ptr += 4
        elif encoding == 0x03:  # 8 byte integer
            value = rquad(b[ptr : ptr + 8])
            ptr += 8
        elif encoding == 0x04:
            value = False
        elif encoding == 0x05:  # true
            value = True
        elif encoding == 0x06:  # word
            # if len(debugKeys):
            #     print("Found encoding with 0x6", debugKeys[key_idx])
            value = rsingle(b[ptr : ptr + 4])
            ptr += 4
        elif encoding == 0x07:  # floating point
            value = rdouble(b[ptr : ptr + 8])
            ptr += 8
        elif encoding == 0x08:  # string
            r = readFlexNumber(b, ptr)
            length = r[0]
            ptr += r[1]
            if length and b[ptr] == 0x07:
                if length == 17:
                    value = struct.unpack("<dd", b[ptr + 1 : ptr + 17])
                elif length == 33:
                    value = struct.unpack("<dddd", b[ptr + 1 : ptr + 33])
                else:
                    raise Exception("Well this is weird.")
            else:
                value = str(b[ptr : ptr + length])
            ptr += length
        elif encoding == 0x09:  # nil?
            value = None
        elif encoding == 0x0A:  # object
            # object is stored as a 4 byte index.
            value = "@" + str(rword(b[ptr : ptr + 4]))
            ptr += 4
        else:
            # print("dumping classes:", globals()["classes"])
            print("dumping keys:")
            for n, val in enumerate(debugKeys):
                print(f"{n:X}\t{(n | 0x80):X}\t{val}")
            raise Exception(
                "Unknown value encoding (key %d idx %d addr %d): "
                % (key_idx, i, ptr - 1)
                + str(encoding)
            )
        values.append((key_idx, value, encoding))
    return values


def treePrintObjects(nib, prefix="", showencoding=False, sortKeys=False, alreadyPrinted=set(), obj_id=None):
    alreadyPrinted = alreadyPrinted.copy()

    objects, keys, values, classes = nib
    if obj_id:
        to_print = [o for i,o in enumerate(objects) if i == obj_id]
    else:
        to_print = objects

    for o_idx, obj in enumerate(objects):
        if obj not in to_print:
            continue
        if o_idx in alreadyPrinted:
            continue
        alreadyPrinted.add(o_idx)

        # print object
        classname = classes[obj[0]]
        obj_values = values[obj[1] : obj[1] + obj[2]]
        if sortKeys:
            obj_values.sort(key = lambda v: keys[v[0]])

        print(prefix + "%s" % (classname,))

        for v in obj_values:
            k_str = keys[v[0]]
            v_str = str(v[1])

            printSubNib = (
                k_str == "NS.bytes"
                and len(v_str) > 40
                and v_str.startswith("NIBArchive")
            )

            if printSubNib:
                print(prefix + "\t" + k_str + " = Encoded NIB Archive")
                nib = readNibSectionsFromBytes(v[1])
                fancyPrintObjects(nib, prefix + "\t", showencoding)

            elif v[2] == 10:
                if showencoding:
                    print(prefix + "\t" + k_str + " = (" + str(v[2]) + ")")
                else:
                    print(prefix + "\t" + k_str + " =")
                treePrintObjects(nib, prefix + "\t", showencoding, sortKeys, alreadyPrinted, int(v[1][1:]))

            else:
                if showencoding:
                    print(prefix + "\t" + k_str + " = (" + str(v[2]) + ")", v_str)
                else:
                    print(prefix + "\t" + k_str + " =", v_str)


def fancyPrintObjects(nib, prefix="", showencoding=False, sortKeys=False):
    objects, keys, values, classes = nib
    for o_idx, obj in enumerate(objects):
        # print object
        classname = classes[obj[0]]
        obj_values = values[obj[1] : obj[1] + obj[2]]

        print(prefix + "%3d: %s" % (o_idx, classname))
        
        if sortKeys:
            obj_values.sort(key = lambda v: keys[v[0]])

        for v in obj_values:
            # print(v)
            k_str = keys[v[0]]
            v_str = str(v[1])

            printSubNib = (
                k_str == "NS.bytes"
                and len(v_str) > 40
                and v_str.startswith("NIBArchive")
            )

            if printSubNib:
                print(prefix + "\t" + k_str + " = Encoded NIB Archive")
                nib = readNibSectionsFromBytes(v[1])
                fancyPrintObjects(nib, prefix + "\t", showencoding, sortKeys)

            else:  # Boring regular data.
                if showencoding:
                    print(prefix + "\t" + k_str + " = (" + str(v[2]) + ")", v_str)
                else:
                    print(prefix + "\t" + k_str + " =", v_str)

            # if k_str == 'NS.bytes' and len(v_str) > 200:
            #     with open('embedded.nib', 'wb') as f:
            #         f.write(v[1])


def readNibSectionsFromBytes(b):
    sections = readHeader(b, 14)
    # print sections
    classes = readClasses(b, sections[3])
    # print classes
    objects = readObjects(b, sections[0])
    # print objects
    keys = readKeys(b, sections[1])
    # print keys
    values = readValues(b, sections[2], keys)
    # print values
    return (objects, keys, values, classes)


def ibdump(filename, showencoding=None, showTree=False, sortKeys=False):
    with open(filename, "rb") as file:
        filebytes = file.read()

    pfx = filebytes[0:10]
    if pfx != b"NIBArchive":
        print('"%s" is not a NIBArchive file.' % (filename))
        return

    print("Prefix:", pfx.decode('utf-8'))

    headers = filebytes[10 : 10 + 4]
    headers = rword(headers)
    print("Headers:", headers)

    nib = readNibSectionsFromBytes(filebytes)
    if showTree:
        treePrintObjects(nib, showencoding=showencoding, sortKeys=sortKeys)
    else:
        fancyPrintObjects(nib, showencoding=showencoding, sortKeys=sortKeys)


if __name__ == "__main__":
    ibdump(filename=sys.argv[1])
