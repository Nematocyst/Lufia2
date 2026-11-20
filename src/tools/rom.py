"""LoROM helpers for Lufia II (US), 2.5 MB, FastROM banks $80-$CF."""
import os

ROM_PATH = os.environ.get('L2ROM', '/home/claude/lufia2/rom/orig.smc')


def load():
    return open(ROM_PATH, 'rb').read()


def to_off(a24):
    """CPU address -> file offset, or None if not ROM."""
    bank, addr = (a24 >> 16) & 0xFF, a24 & 0xFFFF
    if bank in (0x7E, 0x7F):
        return None
    b = bank & 0x7F
    if addr < 0x8000:
        if b >= 0x40:  # $40-$7D low halves mirror ROM in LoROM
            pass
        return None
    off = b * 0x8000 + (addr - 0x8000)
    return off


def to_cpu(off):
    """File offset -> canonical FastROM CPU address ($80+)."""
    return ((0x80 + (off >> 15)) << 16) | (0x8000 + (off & 0x7FFF))
