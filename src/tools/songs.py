"""List Lufia II songs: resources 0..99 decompressed, 'S2C' header + 12-char name."""
import sys, json


def decode(s):
    n = s[0] | s[1] << 8
    out = bytearray(); p = 2
    while True:
        flags = s[p]; p += 1; left = 8
        while left:
            t = s[p]; p += 1
            if t < 0x80:
                out.append(t)
                if len(out) == n:
                    return bytes(out), p
                continue
            ref = flags & 0x80; flags = (flags << 1) & 0xFF; left -= 1
            if not ref:
                out.append(t)
            else:
                b = s[p]; p += 1
                v = (t << 8 | b) >> 4
                if b & 0x0F:
                    count = (b & 0x0F) + 2; dist = 0x1000 - v
                else:
                    c = s[p]; p += 1
                    count = (c & 0x3F) + 3
                    off = (0xC000 | v << 2 | c >> 6) & 0xFFFF; dist = 0x10000 - off
                for _ in range(count):
                    out.append(out[-dist])
            if len(out) == n:
                return bytes(out), p


def lo(a):
    return (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)


def stream_addr(e):
    low = e[0] | e[1] << 8
    high = e[1] | e[2] << 8
    carry = high >> 15
    bank = (0xA7 + (((high << 1) & 0xFFFF) >> 8) + carry) & 0xFF
    return bank << 16 | (low | 0x8000)


def resource(rom, i, table=0xA78000):
    p = lo(table) + 3 * i
    return lo(stream_addr(rom[p:p + 3]))


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    songs = []
    for i in range(100):
        try:
            d, used = decode(rom[resource(rom, i):])
        except Exception as e:
            print('%02X error %s' % (i, e)); continue
        tag = d[2:5]
        name = d[5:17].decode('ascii', 'replace') if tag == b'S2C' else ''
        songs.append({'id': i, 'name': name.strip(), 'size': len(d), 'tag': tag.hex(), 'samples': d[0x1A] if len(d) > 0x1A else None})
        print('%02X %-3s %-14s decoded %5d  sample-mode %s' % (i, tag.decode('ascii', 'replace'), name, len(d), d[0x1A] if len(d) > 0x1A else '-'))
    json.dump(songs, open(sys.argv[2] if len(sys.argv) > 2 else 'songs.json', 'w'), indent=1)
