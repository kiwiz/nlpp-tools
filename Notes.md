# `img.bin` #

The contents of `img.bin` are aligned on `0x800` byte blocks. Blocks are 0-indexed.

## File Header ##

Addr: `0x0` - `0x800`

The file header contains a bunch of counts, offsets and indices that allow you to figure out where everything else is stored.

- `hdr + 0x000`, bytes: 4, ?
- `hdr + 0x004`, bytes: 4, Data start block index (`data_start_block`)
- `hdr + 0x008`, bytes: 4, ?
- `hdr + 0x00C`, bytes: 4, ?
- `hdr + 0x010`, bytes: 4, Number of entries in the index table. (`idx_table_entry_count`)
- `hdr + 0x014`, bytes: 4, Offset to the offset table (`off_table_offset`)
- `hdr + 0x018`, bytes: 4, ?
- `hdr + 0x01C`, bytes: 4, ?
- `hdr + 0x020`, bytes: 4, ?
- `hdr + 0x024`, bytes: 4, ?


## Index Table ##

`idx_table_addr = 0x800`
Addr: `idx_table_addr` - `idx_table_addr + idx_table_entry_count * 0x4` (`idx_table_end`)

The index table defines all of the resource slots within `img.bin`. For whatever reason, some of these slots are empty. The table is 0-indexed.

### Entry ###

- `entry + 0x000`, bytes: 4, Type
- `entry + 0x000`, bytes: 4, Zero
- `entry + 0x000`, bytes: 4, ?
- `entry + 0x000`, bytes: 4, ?
- `entry + 0x000`, bytes: 2, Zero
- `entry + 0x000`, bytes: 1, ?
- `entry + 0x000`, bytes: 1, ?


## Offset Table ##

`off_table_addr = idx_table_addr + off_table_offset`
Addr: `off_table_addr` - `off_table_addr + 0xc + off_table_entry_count * 0x8` (`off_table_end`)

### Header ###

The header defines the size (and a mystery attribute) of the table.

- `hdr + 0x000`, bytes: 4, Zero
- `hdr + 0x004`, bytes: 4, Number of entries in the offset table (`off_table_entry_count`)
- `hdr + 0x008`, bytes: 4, ?

### Entry ###

# Table1 #

`PAK `
    unk1 == 0
    a, b == 0
    c == 128 if zero_bit else 0
    zero_bit == '0' if zero_bit else ' '

'0000'
    zero_bit = 8

# Hashes #

Orig: `77190d7bf672ff7d62c09018a8513989d22b967a`


# Pack #

## Header ##

`hdr + 0x000`, bytes: 0, Type
`hdr + 0x000`, bytes: 0, Count
`hdr + 0x000`, bytes: 0, ?
`hdr + 0x000`, bytes: 0, Offset to end of table
`hdr + 0x000`, bytes: 0, Offset to start of data
`hdr + 0x000`, bytes: 0, Size of decompressed package
`hdr + 0x000`, bytes: 0, Size of compressed package
`hdr + 0x000`, bytes: 0, ?

`'SAB '`: `cmp_len == dec_len, cmp_off == def_off, flags == 0`
`'TEXI'`: `cmp_len == 0, cmp_off == 0, flags == 0`

## Entry ##

## Str table ##

# Types #

- `SMES` - Serialized Mesh
- `SMAT` - Serialized Mat
` `MANM` - ???
