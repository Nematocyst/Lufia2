"""Recover the Restored+Iris+RETRY ROM (the source of addon_backgrounds3_for_restored_iris_retry.bps):
bytes the patch copies from its source at the same position are taken from the result; everything
else is assumed to be the clean ROM's byte. Verified with the source CRC32 stored in the patch."""
import sys, zlib, struct
clean = open(sys.argv[1], 'rb').read(); patch = open(sys.argv[2], 'rb').read(); target = open(sys.argv[3], 'rb').read()
p = 4
def rd():
    global p
    data, shift = 0, 1
    while True:
        x = patch[p]; p += 1; data += (x & 0x7F) * shift
        if x & 0x80: return data
        shift <<= 7; data += shift
ssz, tsz, msz = rd(), rd(), rd(); p += msz
src = bytearray(clean[:ssz]) if ssz <= len(clean) else bytearray(clean) + bytes(ssz - len(clean))
out = 0; same = 0
while p < len(patch) - 12:
    x = rd(); cmd, ln = x & 3, (x >> 2) + 1
    if cmd == 0:
        src[out:out + ln] = target[out:out + ln]; same += ln
    elif cmd == 1: p += ln
    elif cmd in (2, 3): rd()
    out += ln
sc = struct.unpack('<I', patch[-12:-8])[0]
print('source size %d, copied-through bytes %d, CRC %08X expected %08X -> %s' % (ssz, same, zlib.crc32(src), sc, 'EXACT' if zlib.crc32(src) == sc else 'MISMATCH'))
open(sys.argv[4], 'wb').write(src)
