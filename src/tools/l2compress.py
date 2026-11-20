"""Compressor/decompressor for Lufia II resource streams (DecompressResource $80:8E9D).

Stream: 2-byte decoded length, then groups. A group starts with a flag byte; its bits
(MSB first) are spent only by tokens >= $80:
  token < $80            literal byte, no flag bit
  token >= $80, bit 0    literal byte
  token >= $80, bit 1    back reference, token + 1 or 2 more bytes:
      second & $0F != 0  v = (token<<8 | second) >> 4,  distance = $1000 - v (1..$800),
                         count = (second & $0F) + 2   (3..17)
      second & $0F == 0  third byte: offset = $C000 | v<<2 | third>>6, distance = $10000 - offset
                         (1..$2000), count = (third & $3F) + 3   (3..66)
Decoding stops as soon as the declared length is reached.

    python3 l2compress.py check <rom>      round-trip every resource in the ROM
"""
import sys


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
                assert 0 < dist <= len(out) and count <= n - len(out)
                for _ in range(count):
                    out.append(out[-dist])
            if len(out) == n:
                return bytes(out), p


MAXD2, MAXC2, MAXD3, MAXC3 = 0x800, 17, 0x2000, 66


def _matches(data):
    """For each position, the longest match per useful distance band (hash chains on 3 bytes)."""
    n = len(data)
    head = {}
    prev = [-1] * n
    best = [None] * n
    for i in range(n):
        if i + 3 <= n:
            key = data[i:i + 3]
            j = head.get(key, -1)
            cand2 = cand3 = None
            steps = 0
            while j >= 0 and i - j <= MAXD3 and steps < 256:
                d = i - j
                m = 0
                lim = min(MAXC3, n - i)
                while m < lim and data[j + m] == data[i + m]:
                    m += 1
                if m >= 3:
                    if d <= MAXD2 and (cand2 is None or m > cand2[1]):
                        cand2 = (d, min(m, MAXC2))
                    if cand3 is None or m > cand3[1]:
                        cand3 = (d, m)
                j = prev[j]; steps += 1
            best[i] = (cand2, cand3)
            prev[i] = head.get(key, -1)
            head[key] = i
    return best


def encode(data):
    """Optimal parse (cost in bits; flag bits cost 1, bytes 8)."""
    data = bytes(data)
    n = len(data)
    assert 0 < n <= 0xFFFF
    M = _matches(data)
    INF = float('inf')
    cost = [INF] * (n + 1); cost[n] = 0
    choice = [None] * (n + 1)
    for i in range(n - 1, -1, -1):
        lit = (8 if data[i] < 0x80 else 9) + cost[i + 1]
        cost[i] = lit; choice[i] = ('L',)
        if M[i]:
            c2, c3 = M[i]
            if c2:
                d, m = c2
                for L in range(3, m + 1):
                    c = 17 + cost[i + L]
                    if c < cost[i]:
                        cost[i] = c; choice[i] = ('R', d, L)
            if c3:
                d, m = c3
                for L in range(3, m + 1):
                    c = 25 + cost[i + L]
                    if c < cost[i]:
                        cost[i] = c; choice[i] = ('R', d, L)
    out = bytearray([n & 0xFF, n >> 8])
    group = bytearray(); flags = 0; used = 0

    def flush():
        nonlocal group, flags, used
        out.append((flags << (8 - used)) & 0xFF); out.extend(group)
        group = bytearray(); flags = 0; used = 0

    i = 0
    while i < n:
        ch = choice[i]
        if ch[0] == 'L':
            b = data[i]
            if b < 0x80:
                group.append(b)
            else:
                group.append(b); flags = flags << 1; used += 1
            i += 1
        else:
            _, d, L = ch
            if d <= MAXD2 and L <= MAXC2:
                v = 0x1000 - d
                group += bytes([v >> 4, (v & 0xF) << 4 | (L - 2)])
            else:
                off = 0x10000 - d
                v = (off & 0x3FFF) >> 2
                group += bytes([v >> 4, (v & 0xF) << 4, (off & 3) << 6 | (L - 3)])
            flags = flags << 1 | 1; used += 1
            i += L
        if used == 8:
            flush()
    if group or used:
        flush()
    enc = bytes(out)
    assert decode(enc)[0] == data
    return enc


TABLE = 0xA78000


def lo(a):
    return (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)


def stream_addr(e):
    low = e[0] | e[1] << 8
    high = e[1] | e[2] << 8
    carry = high >> 15
    bank = (0xA7 + (((high << 1) & 0xFFFF) >> 8) + carry) & 0xFF
    return bank << 16 | (low | 0x8000)


def resource(rom, i, table=TABLE):
    p = lo(table) + 3 * i
    return lo(stream_addr(rom[p:p + 3]))


if __name__ == '__main__' and sys.argv[1] == 'check':
    rom = open(sys.argv[2], 'rb').read()
    tot_old = tot_new = 0
    for i in range(680):
        s = resource(rom, i)
        dec, used = decode(rom[s:])
        enc = encode(dec)
        tot_old += used; tot_new += len(enc)
    print('680 resources round-trip; original %d bytes, re-encoded %d bytes (%.1f%%)' % (tot_old, tot_new, 100 * tot_new / tot_old))
