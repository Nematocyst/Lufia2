"""Regression check for Lufia II builds (combined edition or any patched ROM).

Takes a snapshot of a ROM's behaviour and compares two snapshots, so a new build can be checked
against the last good one automatically: nothing that used to work should change unless intended.

    python3 regress.py snapshot ROM DIR [--maps 00,01,..|all] [--battles 00,07,..|all|none] [--quick]
    python3 regress.py compare OLD_DIR NEW_DIR [--report report.md]
    python3 regress.py check ROM OLD_DIR [--report report.md]        (snapshot into OLD_DIR.new + compare)

A snapshot (DIR) holds:
  meta.json     size, SHA1, header checksum, static checks (every map's data / header / event block
                decodes, ROM-only render works), boot result, per-map and per-battle results
  field/XX.png  emulator screenshot after warping to map XX (party placed at an exit landing spot)
  battle/XX.png screenshot ~6 s into a battle forced to background XX (test hook added to a COPY of
                the ROM in free space; the ROM itself is not changed)
Compare: a map/battle screenshot that changed by more than 0.5 % of its pixels, a map that no longer
loads, a battle that no longer starts, or a static check that got worse is reported; side-by-side
images of every difference go to NEW_DIR/diff/.
"""
import sys, os, json, hashlib, tempfile
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'mapview'))
import l2compress as L

CORE = os.environ.get('L2_CORE', '/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/'
                      'scratchpad/snes9x/libretro/snes9x_libretro.so')
MAPS = list(range(0xF0))                      # $F0/$F1 = Ancient Cave (generated), skipped
BATTLE_BGS = list(range(0x18))                # original background ids (a build may add more: --battles)
THRESH = 0.5                                  # percent of pixels


# ------------------------------------------------------------------ static checks
def header_ok(rom):
    c = rom[0x7FDE] | rom[0x7FDF] << 8; x = rom[0x7FDC] | rom[0x7FDD] << 8
    size = len(rom); p2 = 1 << (size.bit_length() - 1)
    s = sum(rom[:p2])
    if size > p2:
        rest = rom[p2:]; s += sum(rest) * (p2 // len(rest))
    s = (s - sum(rom[0x7FDC:0x7FE0]) + 0x1FE) & 0xFFFF
    return {'checksum': '%04X' % c, 'complement_ok': (c ^ x) == 0xFFFF, 'checksum_ok': s == c}


def static_checks(rom, maps):
    from mapdata import MapData
    from mapheader import MapHeader
    import romrender
    out = {}
    for m in maps:
        r = {}
        try:
            md = MapData(rom, m); r['layers'] = [(W, H) for _, W, H, _ in md.layers]
        except Exception as ex:
            r['data_error'] = str(ex)[:80]
        try:
            h = MapHeader(rom, m); r['exits'] = len(h.lists[0x06]) if isinstance(h.lists[0x06], list) else -1
        except Exception as ex:
            r['header_error'] = str(ex)[:80]
        try:
            img = romrender.ROMField(rom, m).compose()
            r['render_md5'] = hashlib.md5(img.tobytes()).hexdigest()[:12]
        except Exception as ex:
            r['render_error'] = str(ex)[:80]
        out['%02X' % m] = r
    ev = {}
    try:
        import eventdec, rom as R
        for m in maps:
            M = eventdec.Map(rom, m)
            if M.ok:
                M.decode(); ev['%02X' % m] = [len(M.ins), len(M.errors)]
    except Exception as ex:
        ev['error'] = str(ex)[:80]
    return out, ev


# ------------------------------------------------------------------ emulator
def battle_hook(rom):
    """Copy of the ROM with a test hook: $7F:FFF1 = monster group, $7F:FFF0 = 1 -> the next field frame
    starts a scripted battle (as battletest.asm, but the code goes to free space found here).
    FieldWaitForNextFrame $83:900C: LDA $40 / CMP $40 / BEQ -4 / RTS -> JSL hook / RTS."""
    rom = bytearray(rom)
    if len(rom) < 0x400000:                    # test copy only: pad to 4 MB so a free bank exists
        rom += bytes(0x400000 - len(rom))
    o = L.lo(0x83900C)
    assert bytes(rom[o:o + 7]) == bytes.fromhex('a540c540f0fc60'), 'unexpected $83:900C'
    code = bytes.fromhex(
        '08e220'            # PHP / SEP #$20
        'a540c540f0fc'      # LDA $40 / CMP $40 / BEQ -
        'afF0FF7Ff019'      # LDA $7FFFF0 / BEQ done
        'a9008fF0FF7F'      # LDA #0 / STA $7FFFF0
        'afF1FF7F8fA4F87F'  # LDA $7FFFF1 / STA $7FF8A4
        'a9ff8fA3F87F'      # LDA #$FF / STA $7FF8A3
        'c210'              # REP #$10
        '22EB8383'          # JSL FieldBattleTransition $83:83EB
        '286b')             # done: PLP / RTL
    # find room for it in a high bank (64 bytes of $00 or $FF, not crossing a bank)
    at = None
    for bank in range(0xFF, 0xBF, -1):
        base = L.lo(bank << 16 | 0x8000)
        if base + 0x8000 > len(rom):
            continue
        blk = rom[base + 0x7F00:base + 0x7FC0]
        if all(b == 0 for b in blk) or all(b == 0xFF for b in blk):
            at = bank << 16 | 0xFF00; break
    assert at, 'no free space for the battle hook'
    p = L.lo(at); rom[p:p + len(code)] = code
    # fix the BEQ to "done" (offset from after the BEQ operand to the PLP)
    beq = code.index(bytes.fromhex('f019'))
    done = len(code) - 2
    rom[p + beq + 1] = done - (beq + 2)
    rom[o:o + 5] = bytes([0x22, at & 0xFF, at >> 8 & 0xFF, at >> 16, 0x60])
    return bytes(rom)


def landing_spots(rom, maps):
    """Where to put the party on each map: the arrival point of some exit leading there."""
    from mapheader import MapHeader
    spot = {}
    for src in range(0xF0):
        try:
            ex = MapHeader(rom, src).lists[0x06]
        except Exception:
            continue
        if not isinstance(ex, list):
            continue
        for e in ex:
            if e[8] != 0xFF and e[8] not in spot:
                spot[e[8]] = (e[6], e[7])
    return {m: spot.get(m, (10, 10)) for m in maps}


class Runner:
    def __init__(self, romfile):
        from retro import Emu
        self.e = Emu(CORE, romfile); self.e.run(2)

    def boot(self, presses=400):
        e = self.e; e.run(300)
        seen = []
        for i in range(presses):
            e.press('START' if i % 7 == 0 else 'A', hold=2, gap=10)
            m = e.ram[0x5AC] | e.ram[0x5AD] << 8
            if not seen or seen[-1] != m:
                seen.append(m)
        self.field_state = e.save_state()
        return seen

    def warp(self, m, X, Y, frames=200):
        e = self.e; e.load_state(self.field_state); e.run(2); r = e.ram
        r[0x5B4] = r[0x5AC]; r[0x5AE] = m; r[0x5B0] = X; r[0x5B1] = Y; r[0x5B2] = 0xF0
        r[0x5B3] = 2; r[0x5B5] |= 0x88            # bit 3: transitions allowed (set after the intro)
        e.run(frames)
        return r[0x5AC], e.image().convert('RGB')

    def battle(self, bg, group=1, frames=360):
        e = self.e; e.load_state(self.field_state); e.run(30); r = e.ram
        r[0x1F8A0] = bg; r[0x1FFF1] = group; r[0x1FFF0] = 1
        started = False
        for f in range(900):
            if f < 120:
                r[0x1F8A0] = bg
            e.run(1)
            if r[0x1F8A3] == 1 or r[0x11E1] == bg and f > 60:
                started = True
        return started, r[0x11E1], e.image().convert('RGB')


def snapshot(romfile, out, maps=MAPS, battles=BATTLE_BGS):
    os.makedirs(os.path.join(out, 'field'), exist_ok=True)
    os.makedirs(os.path.join(out, 'battle'), exist_ok=True)
    rom = open(romfile, 'rb').read()
    meta = {'rom': os.path.basename(romfile), 'size': len(rom), 'sha1': hashlib.sha1(rom).hexdigest(),
            'header': header_ok(rom)}
    meta['static'], meta['events'] = static_checks(rom, maps)
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, 'hooked.sfc')
        open(f, 'wb').write(battle_hook(rom) if battles else rom)
        R = Runner(f)
        seq = R.boot()
        meta['boot'] = {'maps_seen': ['%X' % m for m in seq], 'field': seq[-1] < 0xF0}
        spots = landing_spots(rom, maps)
        meta['field'] = {}
        for m in maps:
            got, img = R.warp(m, *spots[m])
            img.save(os.path.join(out, 'field', '%02X.png' % m))
            meta['field']['%02X' % m] = {'loaded': got == m, 'at': spots[m]}
        meta['battle'] = {}
        for bg in battles:
            ok, cur, img = R.battle(bg)
            img.save(os.path.join(out, 'battle', '%02X.png' % bg))
            meta['battle']['%02X' % bg] = {'started': ok, 'bg_in_ram': '%02X' % cur}
    json.dump(meta, open(os.path.join(out, 'meta.json'), 'w'), indent=1)
    return meta


def pct(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape:
        return 100.0
    return float((a != b).any(axis=2).mean() * 100)


def compare(old, new, report=None):
    A = json.load(open(os.path.join(old, 'meta.json'))); B = json.load(open(os.path.join(new, 'meta.json')))
    os.makedirs(os.path.join(new, 'diff'), exist_ok=True)
    lines = ['# Regression report', '', 'old: %s (%s…)' % (A['rom'], A['sha1'][:10]),
             'new: %s (%s…)' % (B['rom'], B['sha1'][:10]), '']
    bad = []
    if not B['header']['checksum_ok']:
        bad.append('header checksum wrong in the new ROM')
    if A['boot']['field'] and not B['boot']['field']:
        bad.append('boot: new game no longer reaches the field (%s)' % B['boot']['maps_seen'])
    for m, r in B['static'].items():
        o = A['static'].get(m, {})
        for k in ('data_error', 'header_error', 'render_error'):
            if k in r and k not in o:
                bad.append('map %s: %s (%s)' % (m, k.replace('_', ' '), r[k]))
    redrawn = [m for m, r in B['static'].items()
               if 'render_md5' in r and A['static'].get(m, {}).get('render_md5') not in (None, r['render_md5'])]
    for m, (n, err) in B['events'].items() if 'error' not in B['events'] else []:
        o = A['events'].get(m)
        if o and err > o[1]:
            bad.append('map %s: event decode errors %d -> %d' % (m, o[1], err))
    changed = []
    for kind in ('field', 'battle'):
        for k, r in B[kind].items():
            o = A[kind].get(k)
            if o is None:
                continue
            if kind == 'field' and o['loaded'] and not r['loaded']:
                bad.append('map %s no longer loads' % k)
            if kind == 'battle' and o['started'] and not r['started']:
                bad.append('battle with background %s no longer starts' % k)
            ia = Image.open(os.path.join(old, kind, k + '.png')); ib = Image.open(os.path.join(new, kind, k + '.png'))
            d = pct(ia, ib)
            if d > THRESH:
                changed.append((kind, k, d))
                s = Image.new('RGB', (ia.width + ib.width + 4, max(ia.height, ib.height)), (255, 0, 255))
                s.paste(ia, (0, 0)); s.paste(ib, (ia.width + 4, 0))
                s.save(os.path.join(new, 'diff', '%s_%s.png' % (kind, k)))
    lines.append('## Problems (%d)' % len(bad))
    lines += ['- ' + b for b in bad] or ['- none']
    lines += ['', '## Screens that changed (%d, more than %.1f %% of pixels)' % (len(changed), THRESH)]
    lines += ['- %s %s: %.1f %% (diff/%s_%s.png)' % (k, i, d, k, i) for k, i, d in changed] or ['- none']
    lines += ['', '## Whole-map renders that changed (ROM data, all layers; %d)' % len(redrawn),
              '- ' + (' '.join(redrawn) if redrawn else 'none')]
    nf = sum(r['loaded'] for r in B['field'].values()); nb = sum(r['started'] for r in B['battle'].values())
    lines += ['', '## Totals', '- maps loaded: %d of %d' % (nf, len(B['field'])),
              '- battles started: %d of %d' % (nb, len(B['battle'])),
              '- event blocks decoded: %d' % len(B['events'])]
    txt = '\n'.join(lines) + '\n'
    if report:
        open(report, 'w').write(txt)
    print(txt)
    return bad, changed


def parse_ids(args, flag, default):
    if flag not in args:
        return default
    v = args[args.index(flag) + 1]
    if v == 'all':
        return default if flag == '--maps' else list(range(0x30))
    if v == 'none':
        return []
    return [int(x, 16) for x in v.split(',')]


if __name__ == '__main__':
    a = sys.argv
    if a[1] == 'snapshot':
        snapshot(a[2], a[3], parse_ids(a, '--maps', MAPS), parse_ids(a, '--battles', BATTLE_BGS))
    elif a[1] == 'compare':
        compare(a[2], a[3], a[a.index('--report') + 1] if '--report' in a else None)
    elif a[1] == 'check':
        new = a[3].rstrip('/') + '.new'
        A = json.load(open(os.path.join(a[3], 'meta.json')))
        snapshot(a[2], new, [int(k, 16) for k in A['field']], [int(k, 16) for k in A['battle']])
        bad, _ = compare(a[3], new, a[a.index('--report') + 1] if '--report' in a else None)
        sys.exit(1 if bad else 0)
