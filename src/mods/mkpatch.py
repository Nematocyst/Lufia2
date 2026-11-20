"""Write BPS and IPS patches from two ROM files: mkpatch.py orig mod out_base

Long runs of one byte (e.g. padding a ROM expansion) are stored compactly:
IPS RLE records, and BPS TargetCopy from the byte just written.
"""
import sys, zlib, struct

RUN = 16                              # minimum run length worth encoding as a run


def vli(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n == 0:
            out.append(0x80 | x); break
        out.append(x); n -= 1
    return bytes(out)


def pieces(data):
    """Split changed data into ('lit', bytes) and ('run', byte, length)."""
    out, i, n = [], 0, len(data)
    lit_start = 0
    while i < n:
        j = i
        while j < n and data[j] == data[i]:
            j += 1
        if j - i >= RUN:
            if lit_start < i:
                out.append(('lit', data[lit_start:i]))
            out.append(('run', data[i], j - i))
            lit_start = j
        i = j
    if lit_start < n:
        out.append(('lit', data[lit_start:n]))
    return out


def bps(src, dst, meta=b''):
    out = bytearray(b'BPS1') + vli(len(src)) + vli(len(dst)) + vli(len(meta)) + meta
    i = 0; n = len(dst); tro = 0           # target-relative offset for TargetCopy
    while i < n:
        same = i < len(src) and src[i] == dst[i]
        j = i
        while j < n and ((j < len(src) and src[j] == dst[j]) == same):
            j += 1
        if same:
            out += vli(((j - i - 1) << 2) | 0)            # SourceRead
        else:
            pos = i
            for p in pieces(dst[i:j]):
                if p[0] == 'lit':
                    out += vli(((len(p[1]) - 1) << 2) | 1) + p[1]; pos += len(p[1])   # TargetRead
                else:
                    _, b, ln = p
                    out += vli(((1 - 1) << 2) | 1) + bytes([b]); pos += 1             # one byte...
                    delta = (pos - 1) - tro                                           # ...then copy it
                    out += vli(((ln - 2) << 2) | 3) + vli((abs(delta) << 1) | (delta < 0))
                    tro = pos - 1 + (ln - 1); pos += ln - 1
        i = j
    out += struct.pack('<I', zlib.crc32(src)) + struct.pack('<I', zlib.crc32(dst))
    out += struct.pack('<I', zlib.crc32(bytes(out)))
    return bytes(out)


def ips(src, dst):
    out = bytearray(b'PATCH'); i = 0; n = len(dst)
    while i < n:
        if i < len(src) and src[i] == dst[i]:
            i += 1; continue
        j = i
        while j < n and j - i < 0xFFFF and not (j < len(src) and src[j] == dst[j] and dst[j + 1:j + 4] == src[j + 1:j + 4]):
            j += 1
        if i == 0x454F46:  # 'EOF' offset can't start a record
            i -= 1
        pos = i
        for p in pieces(dst[i:j]):
            if p[0] == 'lit':
                out += pos.to_bytes(3, 'big') + len(p[1]).to_bytes(2, 'big') + p[1]; pos += len(p[1])
            else:
                _, b, ln = p
                out += pos.to_bytes(3, 'big') + b'\x00\x00' + ln.to_bytes(2, 'big') + bytes([b]); pos += ln
        i = j
    return bytes(out + b'EOF')


def apply_ips(src, patch):
    d = bytearray(src); p = 5
    while patch[p:p + 3] != b'EOF':
        off = int.from_bytes(patch[p:p + 3], 'big'); ln = int.from_bytes(patch[p + 3:p + 5], 'big'); p += 5
        if ln == 0:
            rl = int.from_bytes(patch[p:p + 2], 'big'); data = patch[p + 2:p + 3] * rl; p += 3
        else:
            data = patch[p:p + ln]; p += ln
        if len(d) < off + len(data):
            d += bytes(off + len(data) - len(d))
        d[off:off + len(data)] = data
    return bytes(d)


def apply_bps(src, patch):
    p = 4
    def rd():
        nonlocal p
        data, shift = 0, 1
        while True:
            x = patch[p]; p += 1
            data += (x & 0x7F) * shift
            if x & 0x80:
                return data
            shift <<= 7; data += shift
    ssz, tsz, msz = rd(), rd(), rd(); p += msz
    out = bytearray(); sro = tro = 0
    while p < len(patch) - 12:
        x = rd(); cmd, ln = x & 3, (x >> 2) + 1
        if cmd == 0:
            out += src[len(out):len(out) + ln]
        elif cmd == 1:
            out += patch[p:p + ln]; p += ln
        elif cmd == 2:
            v = rd(); sro += -(v >> 1) if v & 1 else v >> 1; out += src[sro:sro + ln]; sro += ln
        else:
            v = rd(); tro += -(v >> 1) if v & 1 else v >> 1
            for _ in range(ln):
                out.append(out[tro]); tro += 1
    assert len(out) == tsz
    return bytes(out)


if __name__ == '__main__':
    src = open(sys.argv[1], 'rb').read(); dst = open(sys.argv[2], 'rb').read()
    b, i = bps(src, dst), ips(src, dst)
    assert apply_bps(src, b) == dst, 'BPS round trip failed'
    assert apply_ips(src, i) == dst, 'IPS round trip failed'
    open(sys.argv[3] + '.bps', 'wb').write(b)
    open(sys.argv[3] + '.ips', 'wb').write(i)
    print('changed bytes', sum(1 for a, c in zip(src, dst) if a != c) + max(0, len(dst) - len(src)),
          '| bps %d B, ips %d B' % (len(b), len(i)))
