import struct, zlib, yaml, os, collections

"""
Represents a frame into a file.
"""


class FileWindow:
    def __init__(self, filename, base_offset=0, wlen=None):
        self.filename = filename
        self.base_offset = base_offset
        self.pos = 0
        self.wlen = wlen

    def read(self, wlen=None):
        if wlen is None:
            wlen = self.wlen
        if self.wlen is not None and wlen + self.pos > self.wlen:
            wlen = self.wlen - self.pos

        fh = open(self.filename, "rb")
        fh.seek(self.base_offset + self.pos, 0)
        if wlen is None:
            data = fh.read()
        else:
            data = fh.read(wlen)
            self.pos += wlen
        fh.close()

        return data

    def tell(self):
        return self.pos

    def seek(self, pos):
        assert self.wlen == None or pos <= self.wlen and pos >= 0
        self.pos = pos

    def len(self):
        return (
            os.path.getsize(self.filename) - self.base_offset
            if self.wlen is None
            else self.wlen
        )


"""
A generic resource
"""


class Resource(object):
    def __init__(self, typ, fw):
        self.typ = typ
        self.fw = fw

    def parse(self, recursive):
        pass

    def read(self):
        return self.fw.read()

    def write(self, fh):
        fh.write(self.fw.read())

    def get_header(self):
        return self.typ, self.fw.len(), 0x0, 0x0, 0x0


"""
A resource within a Package
"""


class Element(object):
    def __init__(self, typ, fn, flags, is_cmp, fw):
        self.typ = typ
        self.fn = fn
        self.flags = flags
        self.is_cmp = is_cmp
        self.fw = fw

    def parse(self, recursive=True):
        pass

    def unparse(self):
        pass

    def parsed(self):
        return self.read()

    def parsed_for_file(self):
        return self.parsed()

    def unparsed(self):
        return self.read(False)

    def unparsed_for_file(self):
        return self.unparsed()

    def read(self, decompress=True):
        self.fw.seek(0x0)
        data = self.fw.read()
        if decompress and self.is_cmp and len(data) > 0:
            data = zlib.decompress(data)
        return data

    def write(self, fh):
        data = self.unparsed_for_file()
        cmp_len = dec_len = len(data)

        if self.is_cmp:
            data = zlib.compress(data, level=9)
            cmp_len = len(data)
            print(cmp_len)
        fh.write(data)

        return cmp_len, dec_len


"""
An empty resource
"""


class Empty(Element):
    def __init__(self, typ, fn, flags):
        super(Empty, self).__init__(typ, fn, flags, False, None)

    def read(self, decompress=True):
        return b""


"""
A TEXture
"""


class Texture(Element):
    def __init__(self, typ, fn, flags, is_cmp, fw):
        super(Texture, self).__init__(typ, fn, flags, is_cmp, fw)


"""
Geometry data
"""


class Geometry(Element):
    def __init__(self, typ, fn, flags, is_cmp, fw):
        super(Geometry, self).__init__(typ, fn, flags, is_cmp, fw)


"""
dARC
"""


class ARC(Element):
    def __init__(self, typ, fn, flags, is_cmp, fw):
        super(ARC, self).__init__(typ, fn, flags, is_cmp, fw)


"""
A TeXT file
"""


class TXT(Element):
    def parsed(self):
        return self.read().decode("sjis")

    def parsed_for_file(self):
        return self.parsed().encode("utf8")

    def unparsed(self):
        return super(TXT, self).unparsed().decode("utf8")

    def unparsed_for_file(self):
        return self.unparsed().encode("sjis")


"""
A SERIalized YAML object (why?)
"""


class SERI(Element):
    FN_INDEX = [b"bone", b"smes", b"smat", b"tex", b"hair_length"]
    ARR_FN_INDEX = [b"texi", b"model", b"cloth", b"list"]
    OFF_ENTRY_LEN = struct.calcsize("=2H")

    def __init__(self, typ, fn, flags, is_cmp, fw, str_table):
        super(SERI, self).__init__(typ, fn, flags, is_cmp, fw)
        assert not is_cmp
        self.str_table = str_table
        self.data = {}

    def parse(self, recursive=True):
        self.fw.seek(0x0)
        typ, data_off, cnt = struct.unpack("=4sIH", self.fw.read(0xA))
        assert typ == b"SERI"
        self.data = self.parse_body(0xA, 0x4 + data_off, cnt, recursive)

    def unparse(self):
        self.data = yaml.load(self.read())
        self._index_strings(self.data)

    def _index_strings(self, data):
        for k, v in data.iteritems():
            self.str_table.add_str(k)
            if type(v) == dict:
                self._index_strings(v)
            elif type(v) == list and type(v[0]) == dict:
                for d in v:
                    self._index_strings(d)

    def parsed(self):
        return yaml.dump(self.data)

    def unparsed(self):
        return super(SERI, self).unparsed()

    def parse_body(self, type_table_off, data_off, cnt, recursive=True):
        self.fw.seek(type_table_off)
        data = {}  # OrderedDict

        off_table = []
        for i in range(cnt):
            name_off, val_off = struct.unpack("=2H", self.fw.read(0x4))
            off_table.append([name_off, val_off])
        type_table = self.fw.read(cnt)

        for i in range(cnt):
            etyp = type_table[i:i+1]
            name_off, val_off = off_table[i]
            k = self.str_table[name_off]
            val = None

            if etyp == b"s":
                self.fw.seek(data_off + val_off)
                (val,) = struct.unpack("I", self.fw.read(0x4))
                val = self.str_table[val_off]
            elif etyp == b"i":
                self.fw.seek(data_off + val_off)
                (val,) = struct.unpack("I", self.fw.read(0x4))
                if k in SERI.FN_INDEX:
                    val = self.str_table.get_str_slot(val - 1)
            elif etyp == b"f":
                self.fw.seek(data_off + val_off)
                (val,) = struct.unpack("f", self.fw.read(0x4))
            elif etyp == b"b":
                self.fw.seek(data_off + val_off)
                (val,) = struct.unpack("?", self.fw.read(0x1))
            elif etyp == b"a":
                self.fw.seek(data_off + val_off)
                val = self.read_arr(k, data_off, self.str_table, recursive)
            elif etyp == b"h":
                self.fw.seek(data_off + val_off)
                (icnt,) = struct.unpack("H", self.fw.read(0x2))
                val = self.parse_body(
                    data_off + val_off + 0x2, data_off, icnt, recursive
                )
            else:
                raise (Exception("Unknown type: " + repr(etyp)))

            data[k] = val
        return data

    def read_arr(self, k, data_off, str_table, recursive=True):
        atyp, acnt = struct.unpack("=cxH", self.fw.read(0x4))
        aval_table = struct.unpack("=%dH" % acnt, self.fw.read(acnt * 0x2))

        ret = []
        if atyp == b"i":
            for aval_off in aval_table:
                self.fw.seek(data_off + aval_off)
                (val,) = struct.unpack("I", self.fw.read(0x4))
                if k in SERI.ARR_FN_INDEX:
                    val = self.str_table.get_str_slot(val - 1)
                ret.append(val)
        elif atyp == b"f":
            for aval_off in aval_table:
                self.fw.seek(data_off + aval_off)
                ret.append(struct.unpack("f", self.fw.read(0x4))[0])
        elif atyp == b"a":
            for aval_off in aval_table:
                self.fw.seek(data_off + aval_off)
                ret.append(self.read_arr(data_off, str_table))
        elif atyp == b"s":
            for aval_off in aval_table:
                ret.append(self.str_table[aval_off])
        elif atyp == b"h":
            for aval_off in aval_table:
                self.fw.seek(data_off + aval_off)
                (icnt,) = struct.unpack("H", self.fw.read(0x2))

                aval = self.parse_body(
                    data_off + aval_off + 0x2, data_off, icnt, recursive
                )
                ret.append(aval)
        else:
            raise (Exception("Unknown type: " + repr(atyp)))

        return ret

    def write(self, fh):
        abs_off = fh.tell()
        fh.seek(abs_off + 0xA)

        data_off = self.OFF_ENTRY_LEN * len(self.data) + len(self.data)
        sz = self.write_body(fh, abs_off + 0xA + data_off, 0, self.data)
        fh.seek(abs_off)

        fh.write(struct.pack("=4sIH", "SERI", 0x6 + data_off, len(self.data)))

        return 0x0, 0xA + data_off + sz

    def write_body(self, fh, data_abs_off, data_off, data):
        abs_off = fh.tell()
        type_table_off = self.OFF_ENTRY_LEN * len(data)
        curr_off = data_off

        i = 0
        for k, v in data.items():
            name_off = self.str_table.find_str(k)
            fh.seek(abs_off + self.OFF_ENTRY_LEN * i)

            typ = type(v)
            typ_name = None
            if typ == str:
                if k in SERI.FN_INDEX:
                    fh.write(struct.pack("=2H", name_off, curr_off))
                    fh.seek(data_abs_off + curr_off)
                    v = self.str_table.find_str_slot(v) + 1
                    fh.write(struct.pack("I", v))
                    typ_name = b"i"
                    curr_off += 4
                else:
                    fh.write(struct.pack("=2H", name_off, self.str_table.find_str(v)))
                    # print repr(struct.pack('=2H', name_off, self.str_table.find_str(v)))
                    typ_name = b"s"
            elif typ == int:
                fh.write(struct.pack("=2H", name_off, curr_off))
                fh.seek(data_abs_off + curr_off)
                fh.write(struct.pack("I", v))
                typ_name = b"i"
                curr_off += 4
            elif typ == float:
                fh.write(struct.pack("=2H", name_off, curr_off))
                fh.seek(data_abs_off + curr_off)
                fh.write(struct.pack("f", v))
                typ_name = b"f"
                curr_off += 4
            elif typ == bool:
                fh.write(struct.pack("=2H", name_off, curr_off))
                fh.seek(data_abs_off + curr_off)
                fh.write(struct.pack("?", v))
                typ_name = b"b"
                curr_off += 1
            elif typ == list:
                fh.write(struct.pack("=2H", name_off, curr_off))
                fh.seek(data_abs_off + curr_off)
                typ_name = b"a"
                curr_off += self.write_arr(fh, data_abs_off, data_off + curr_off, k, v)
            elif typ == dict:
                fh.write(struct.pack("=2H", name_off, curr_off))
                fh.seek(data_abs_off + curr_off)
                typ_name = b"h"
                curr_off += self.write_body(fh, data_abs_off, curr_off, v)
            else:
                raise (Exception("Unknown type: " + typ))
            fh.seek(abs_off + type_table_off + i)
            fh.write(typ_name)
            i += 1

        return curr_off

    def write_arr(self, fh, data_abs_off, data_off, k, data):
        abs_off = fh.tell()
        aval_table_off = 0x4
        curr_off = data_off + aval_table_off + 0x2 * len(data)
        fh.seek(data_abs_off + curr_off)

        atyp = type(data[0])
        atyp_name = None
        aval_table = []
        if atyp == int:
            atyp_name = b"i"
            for v in data:
                fh.write(struct.pack("I", v))
                aval_table.append(curr_off)
                curr_off += 0x4
        elif atyp == float:
            atyp_name = b"f"
            for v in data:
                fh.write(struct.pack("f", v))
                aval_table.append(curr_off)
                curr_off += 0x4
        elif atyp == list:
            atyp_name = b"a"
            for arr in v:
                aval_table.append(curr_off)
                curr_off += self.write_arr(fh, data_abs_off, curr_off, arr)
        elif atyp == bytes:
            if k in SERI.ARR_FN_INDEX:
                atyp_name = b"i"
                for v in data:
                    v = self.str_table.find_str_slot(v) + 1
                    fh.write(struct.pack("I", v))
                    aval_table.append(curr_off)
                    curr_off += 0x4
            else:
                atyp_name = b"s"
                for v in data:
                    aval_table.append(self.str_table.add_str(v))
        elif atyp == dict:  # OrderedDict
            atyp_name = b"h"
            for v in data:
                aval_table.append(curr_off)
                curr_off += self.write_body(fh, data_abs_off, curr_off, v)
        else:
            raise (Exception("Unknown type: " + atyp))

        fh.seek(abs_off + aval_table_off)
        fh.write(struct.pack("=%dH" % len(data), *aval_table))
        fh.seek(abs_off)
        fh.write(struct.pack("=cxH", atyp_name, len(data)))

        return curr_off


class StrTable(object):
    def __init__(self, data=b""):
        self.data = data
        self.slots = []
        self.map = {}

    def __getitem__(self, pos):
        end = self.data.index(b"\0", pos)
        return self.data[pos:end]

    def update(self, data, slots):
        self.data = data
        self.slots = list(slots)
        self.map = {}

        for i, v in enumerate(self.slots):
            if self[v] not in self.map:
                self.map[self[v]] = i

    def find_str(self, s):
        return self.data.index(s + b"\0")

    def add_str(self, s):
        s0 = s + b"\0"
        idx = self.data.find(s0)
        if idx == -1:
            idx = len(self.data)
            self.data += s0

        return idx

    def get_str_slot(self, i):
        return self[self.slots[i]]

    def find_str_slot(self, s):
        return self.map[s]

    def push_str_slot(self, s):
        self.map[s] = len(self.slots)
        self.slots.append(self.add_str(s))

    def clear(self):
        self.data = b""
        self.slots = []
        self.map = {}

    def clear_slots(self):
        self.slots = []
        self.map = {}


"""
A Package resource
"""


class Package(Resource):
    ENTRY_SIZE = 0x20
    BLOCK_SIZE = 0x10
    BLOCK_MASK = BLOCK_SIZE - 1
    LARGE_BLOCK_SIZE = 0x80
    LARGE_BLOCK_MASK = LARGE_BLOCK_SIZE - 1

    def __init__(self, fw, unk):
        super(Package, self).__init__(b"PAK ", fw)
        self.typ0 = True
        self.dec_len = 0x0
        self.dec_data_off = 0x0
        self.unk = unk  # ???: Either 128 or 0
        self.entries = []
        self.str_table = StrTable()

    def parse(self, recursive=True):
        self.fw.seek(0x0)
        data = self.fw.read(Package.ENTRY_SIZE)

        (
            typ,
            cnt,
            ptr_off,
            str_table_off,
            dec_data_off,
            dec_len,
            cmp_len,
            pad_len,
        ) = Package.parse_header(data)
        self.dec_len = dec_len
        self.dec_data_off = dec_data_off
        self.typ0 = typ[5:6] == b"0"

        off = self.fw.tell()
        self.fw.seek(str_table_off)

        self.str_table.update(
            self.fw.read(ptr_off - str_table_off),
            struct.unpack("=%dI" % cnt, self.fw.read(cnt * 4)),
        )
        self.fw.seek(off)

        for i in range(cnt):
            (
                typ,
                dec_len,
                dec_off,
                flags,
                is_cmp,
                cmp_len,
                cmp_off,
            ) = Package.parse_entry(self.fw.read(Package.ENTRY_SIZE))
            elem_off = cmp_off if is_cmp else dec_off
            elem_len = cmp_len if is_cmp else dec_len
            fw = FileWindow(self.fw.filename, self.fw.base_offset + elem_off, elem_len)
            off = self.fw.tell()
            self.fw.seek(elem_off)

            elem = None
            if typ in [b"TEXI", b"YAML", b"MDL "]:
                elem = SERI(
                    typ,
                    self.str_table.get_str_slot(i),
                    flags,
                    is_cmp,
                    fw,
                    self.str_table,
                )
            elif typ in [b"    "]:
                elem = Empty(typ, self.str_table.get_str_slot(i), flags)
            elif typ in [b"TXT "]:
                elem = TXT(typ, self.str_table.get_str_slot(i), flags, is_cmp, fw)
                elem.read()
            elif typ in [b"TEX "]:
                elem = Texture(typ, self.str_table.get_str_slot(i), flags, is_cmp, fw)
            elif typ in [b"SMES", b"SMAT"]:
                elem = Geometry(typ, self.str_table.get_str_slot(i), flags, is_cmp, fw)
            elif typ in [b"ARC "]:
                elem = ARC(typ, self.str_table.get_str_slot(i), flags, is_cmp, fw)
            else:
                elem = Element(typ, self.str_table.get_str_slot(i), flags, is_cmp, fw)

            self.fw.seek(off)
            if recursive:
                elem.parse(recursive)

            self.entries.append(elem)

    def write(self, fh):
        abs_off = fh.tell()
        # self.str_table.clear() # FIXME: We're not clearing the str table here because the order seems to be significant

        str_table_off = (len(self.entries) + 1) * Package.ENTRY_SIZE
        #        for elem in self.entries:
        #            self.str_table.push_str_slot(elem.fn)

        for elem in self.entries:
            elem.unparse()

        fh.seek(abs_off + str_table_off)
        fh.write(self.str_table.data)
        ptr_off = str_table_off + len(self.str_table.data)
        fh.write(struct.pack("=%dI" % len(self.str_table.slots), *self.str_table.slots))
        curr_off = data_off = self.NEXT_BLOCK_ADDR(
            ptr_off + 0x4 * len(self.str_table.slots)
        )

        elem_pos_table = [None] * len(self.entries)
        for i, elem in enumerate(self.entries):
            if type(elem) != SERI:
                continue
            fh.seek(abs_off + curr_off)
            cmp_len, dec_len = elem.write(fh)
            elem_pos_table[i] = (cmp_len, dec_len, 0, curr_off)
            curr_off = self.NEXT_BLOCK_ADDR(curr_off + dec_len)

        dec_data_off = curr_off
        dec_curr_off = curr_off

        for i, elem in enumerate(self.entries):
            if type(elem) == SERI:
                continue

            is_lrg = type(elem) in [Texture, Geometry, ARC]
            fh.seek(abs_off + curr_off)
            dec_curr_data_off = self.NEXT_BLOCK_ADDR(dec_curr_off, is_lrg)
            delta = dec_curr_data_off - dec_curr_off
            if is_lrg and delta > 0:
                chunk_data = zlib.compress(b"\0" * delta)
                if len(chunk_data) > delta:
                    chunk_data = b"\0" * delta

                fh.write(chunk_data)
                curr_off = self.NEXT_BLOCK_ADDR(curr_off + len(chunk_data))
                fh.seek(abs_off + curr_off)
                assert (curr_off & 0xF) == 0
            dec_curr_off = dec_curr_data_off

            cmp_len, dec_len = elem.write(fh)

            elem_pos_table[i] = (cmp_len, dec_len, curr_off, dec_curr_off)
            curr_data_off = curr_off + cmp_len
            curr_off = self.NEXT_BLOCK_ADDR(curr_data_off)
            dec_curr_off = self.NEXT_BLOCK_ADDR(dec_curr_off + dec_len)

            fh.seek(abs_off + curr_data_off)
            if curr_off > curr_data_off:
                fh.write(b"\0" * (curr_off - curr_data_off))

        self.dec_len = dec_curr_off
        self.dec_data_off = dec_data_off

        fh.seek(abs_off)
        fh.write(
            struct.pack(
                "=6sH6I",
                b"PACK\n" + b"0" if self.typ0 else b" ",
                len(self.entries),
                ptr_off,
                str_table_off,
                dec_data_off,
                dec_curr_off,
                curr_off,
                0,
            )
        )

        for i, elem in enumerate(self.entries):
            cmp_len, dec_len, cmp_off, dec_off = elem_pos_table[i]
            fh.write(
                struct.pack(
                    "=4s4x6I",
                    elem.typ,
                    dec_len,
                    dec_off,
                    elem.flags,
                    elem.is_cmp,
                    cmp_len,
                    cmp_off if elem.is_cmp else 0x0,
                )
            )

    @staticmethod
    def parse_header(data):
        (
            typ,
            cnt,
            ptr_off,
            str_table_off,
            dec_data_off,
            dec_len,
            cmp_len,
            pad_len,
        ) = struct.unpack("=6sH6I", data)
        return typ, cnt, ptr_off, str_table_off, dec_data_off, dec_len, cmp_len, pad_len

    @staticmethod
    def parse_entry(data):
        typ, dec_len, dec_off, flags, is_cmp, cmp_len, cmp_off = struct.unpack(
            "=4s4x6I", data
        )
        return typ, dec_len, dec_off, flags, is_cmp, cmp_len, cmp_off

    def NEXT_BLOCK_ADDR(self, x, lrg=False):
        mask = self.LARGE_BLOCK_MASK if lrg else self.BLOCK_MASK
        sz = self.LARGE_BLOCK_SIZE if lrg else self.BLOCK_SIZE
        return x if (x & mask) == 0 else (x & ~mask) + sz

    def get_header(self):
        return (
            b"PAK ",
            self.dec_len,
            self.dec_data_off,
            self.unk,
            0x30 if self.typ0 else 0x20,
        )


"""
The Image class
"""


class Image(object):
    BLOCK_SIZE = 0x800
    BLOCK_MASK = BLOCK_SIZE - 1
    IDX_TABLE_ADDR = BLOCK_SIZE
    IDX_TABLE_ENTRY_SIZE = 0x14
    OFF_TABLE_ENTRY_SIZE = 0x8

    def __init__(self, filename):
        self.filename = filename
        self.fh = open(filename, "rb+")
        self.entries = []

    def parse(self, recursive=True):
        """
        Parse the image file
        """
        # Read and process the file header
        self.fh.seek(0x0, 0)
        header = struct.unpack("=10I", self.fh.read(0x28))

        data_start_block = header[0x1]

        idx_table_entry_count = header[0x4]

        off_table_offset = header[0x5]
        off_table_addr = self.IDX_TABLE_ADDR + off_table_offset

        self.fh.seek(self.IDX_TABLE_ADDR, 0)

        # Read and populate the index table
        idx_table = []
        for idx in range(idx_table_entry_count):
            typ, num1, num2, num3, num4 = Image.parse_idx_entry(
                self.fh.read(self.IDX_TABLE_ENTRY_SIZE)
            )
            idx_table.append([typ, num1, num2, num3, num4])

        self.fh.seek(off_table_addr, 0)

        # FIXME: Not sure what 'unk' is.
        off_table_entry_count, unk = struct.unpack("=4x2I", self.fh.read(0xC))

        # Read and populate the offset table
        off_table = {}
        for i in range(off_table_entry_count):
            idx, blk_num = Image.parse_off_entry(
                self.fh.read(self.OFF_TABLE_ENTRY_SIZE)
            )
            off_table[idx] = blk_num

        # Populate entries
        self.entries = []
        for idx, idx_entry in enumerate(idx_table):
            if idx not in off_table:
                self.entries.append(None)
                continue

            blk_num = off_table[idx]
            off = self.fh.tell()

            # We need to grab the actual (compressed) size from the PACKage header
            res = None
            addr = self.BLOCK_NUM_ADDR(blk_num)
            if idx_entry[0x0] == b"PAK ":
                self.fh.seek(addr)
                (
                    typ,
                    cnt,
                    ptr_off,
                    str_table_off,
                    dec_data_off,
                    dec_len,
                    cmp_len,
                    pad_len,
                ) = Package.parse_header(self.fh.read(Package.ENTRY_SIZE))
                res = Package(FileWindow(self.filename, addr, cmp_len), idx_entry[0x3])
            else:
                res = Resource(
                    idx_entry[0x0], FileWindow(self.filename, addr, idx_entry[0x1])
                )

            if recursive:
                res.parse(recursive)
            self.entries.append(res)
            self.fh.seek(off, 0)

    def write(self, fh):
        """
        Write the image file
        """
        # Skip over the file header for now, we'll fill it out later
        fh.seek(self.IDX_TABLE_ADDR, 0)

        idx_table_entry_count = len(self.entries)

        # Generate and write the index table
        for idx, res in enumerate(self.entries):
            typ, num1, num2, num3, num4 = b"\0\0\0\0", 0x0, 0x0, 0x0, 0x8
            if res is not None:
                typ, num1, num2, num3, num4 = res.get_header()
            fh.write(struct.pack("=4s4x2I2xBB", typ, num1, num2, num3, num4))

        off_table_offset = fh.tell() - self.IDX_TABLE_ADDR
        off_table_entry_count = len([i for i in self.entries if i is not None])
        # ???: An unknown pointer into the middle of the index table. Modifying it causes the game to crash on boot. The value is exactly 0x800 bytes (1 BLOCK_SIZE) less than the start of the offset table.
        unk = 0x1C4B4

        fh.write(struct.pack("=4x2I", off_table_entry_count, unk))

        next_empty_addr = self.NEXT_BLOCK_ADDR(
            fh.tell() + struct.calcsize("=2I") * off_table_entry_count
        )
        data_start_block = self.ADDR_NUM_BLOCK(next_empty_addr)

        # Generate and write the offset table & its targets

        for idx, res in enumerate(self.entries):
            if res is None:
                continue
            fh.write(struct.pack("=2I", idx, self.ADDR_NUM_BLOCK(next_empty_addr)))
            off = fh.tell()

            # Write resource
            fh.seek(next_empty_addr, 0)
            res.fw.seek(0x0)
            fh.write(res.fw.read())
            next_empty_addr = self.NEXT_BLOCK_ADDR(fh.tell())

            # Pad to next block
            fh.write(b"\0" * (next_empty_addr - fh.tell()))

            fh.seek(off)

        # Write the file header
        # ???: All these constants are unknown
        fh.seek(0x0, 0)
        fh.write(
            struct.pack(
                "=10I",
                0xA,
                data_start_block,
                0x1,
                0x0,
                idx_table_entry_count,
                off_table_offset,
                0x1,
                0x0,
                0x0,
                0x276F4, # ???: Doesn't affect game boot
            )
        )

    @staticmethod
    def parse_idx_entry(data):
        typ, num1, num2, num3, num4 = struct.unpack("=4s4x2I2xBB", data)
        return typ, num1, num2, num3, num4

    @staticmethod
    def parse_off_entry(data):
        idx, blk_num = struct.unpack("=2I", data)
        return idx, blk_num

    def NEXT_BLOCK_ADDR(self, x):
        return (
            x
            if (x & self.BLOCK_MASK) == 0
            else (x & ~self.BLOCK_MASK) + self.BLOCK_SIZE
        )

    def ADDR_NUM_BLOCK(self, x):
        return (x - 1) >> 11

    def BLOCK_NUM_ADDR(self, x):
        return (x + 1) << 11
