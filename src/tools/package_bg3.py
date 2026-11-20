"""Package a backgrounds build: 3 BPS patches (clean -> all, Restored+Iris+RETRY -> all, music-off add-on),
each verified by applying it, plus the music-off ROM.

    python3 package_bg3.py BUILT_ROM BASE_RIR_ROM OUT_DIR

BUILT_ROM = build_bg3.py output (lufia2_rir_bg3.sfc). Prints SHA1s for the README. Boot-test the two
ROMs it leaves in OUT_DIR (rom_bg.sfc, rom_bg_music.sfc) before shipping.
"""
import sys, os, shutil, subprocess, hashlib
sys.path.insert(0, '/home/claude/lufia2/mods')
import mkpatch as M

ASAR = '/home/claude/lufia2/deps/asar/build/asar/bin/asar'
CLEAN = '/home/claude/lufia2/rom/orig.smc'
MUSIC = '/home/claude/lufia2/mods/music.asm'


def main(built, base, out):
    os.makedirs(out, exist_ok=True)
    bgp, mup = os.path.join(out, 'rom_bg.sfc'), os.path.join(out, 'rom_bg_music.sfc')
    shutil.copy(built, bgp); shutil.copy(built, mup)
    subprocess.run([ASAR, MUSIC, mup], check=True)          # default checksum fix
    r = lambda p: open(p, 'rb').read()
    clean, rir, bg, mu = r(CLEAN), r(base), r(bgp), r(mup)
    for name, a, b in [('lufia2_restored_iris_retry_backgrounds3.bps', clean, bg),
                       ('addon_backgrounds3_for_restored_iris_retry.bps', rir, bg),
                       ('addon_musicoff_for_backgrounds3.bps', bg, mu)]:
        p = M.bps(a, b)
        assert M.apply_bps(a, p) == b, name
        open(os.path.join(out, name), 'wb').write(p)
        print(name, len(p), 'verified')
    print('SHA1 backgrounds', hashlib.sha1(bg).hexdigest())
    print('SHA1 with music-off', hashlib.sha1(mu).hexdigest())


if __name__ == '__main__':
    main(*sys.argv[1:4])
