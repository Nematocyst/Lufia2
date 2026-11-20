"""Who plays which battle animation (effect id), beyond spells and IP abilities.

Battle-VM op $5A n plays effect n (and op $3D n, used by RAN-RAN). Scans:
  - every enemy's turn and reaction script (+ the shared routines they call),
  - capsule monster actions ($97:F63B, 84 records, script at +2),
  - item scripts (battle use word 1 and attack script word 2).
For each $5A it records the nearest earlier announce (op $47 message) in the same script.

    python3 effect_users.py > effect_users.txt      (also writes build/effect_users.json)
"""
import json
import rom
import battledec as B
import enemy_ai as A

d = rom.load(); o = rom.to_off
G = json.load(open('/home/claude/lufia2/build/gamedata.json'))
uses = {}          # effect id -> list of strings


def scan(dec, who):
    last = None; last2 = None
    for a in sorted(dec.lines):
        it, e = dec.lines[a]
        if isinstance(it, str):
            continue
        op, args = it
        if op == 0x1E:
            last = A.message(args[0])
        if op in (0x21, 0x22):
            last2 = A.elem(args[0][1])
        if op in (0x5A, 0x3D):
            n = args[0]
            uses.setdefault(n, []).append('%s%s%s' % (who, (' "%s"' % last) if last else '', (' [%s]' % last2) if last2 else ''))
            last = None; last2 = None


def shared(n):
    base = B.shared_base(n)
    dec = B.Decoder(base); dec.run(base)
    return dec


calls_seen = {}
for eid in range(len(A.ENEMY)):
    for nm, dec in A.enemy_scripts(eid).items():
        scan(dec, 'monster %s' % A.ENEMY[eid])
        for c in dec.calls:
            calls_seen.setdefault(c, set()).add(A.ENEMY[eid])
for c in sorted(calls_seen):
    try:
        scan(shared(c), 'shared routine %d (used by %d monsters)' % (c, len(calls_seen[c])))
    except Exception as ex:
        pass

CT = o(0x97F63B)
ncap = ((d[CT] | d[CT + 1] << 8)) // 2
for k in range(ncap):
    base = CT + (d[CT + 2 * k] | d[CT + 2 * k + 1] << 8)
    dec = B.Decoder(base)
    try:
        dec.run(base + 2)
        scan(dec, 'capsule action %d' % k)
    except Exception:
        pass

IT = o(0x96CF69)
for it in G['items']:
    i = it['id']
    base = IT + (d[IT + 2 * i] | d[IT + 2 * i + 1] << 8)
    p = base + 9
    mask = d[p] | d[p + 1] << 8 | d[p + 2] << 16 | d[p + 3] << 24; p += 4
    words = {}
    for bit in range(32):
        if mask >> bit & 1:
            words[bit] = d[p] | d[p + 1] << 8; p += 2
    for wk, what in ((1, 'item use'), (2, 'weapon')):
        if wk in words and words[wk]:
            dec = B.Decoder(base)
            try:
                if it['name'] != 'RAN-RAN step':
                    dec.run(base + words[wk]); scan(dec, '%s %s' % (what, it['name']))
            except Exception:
                pass

json.dump({str(k): v for k, v in uses.items()}, open('/home/claude/lufia2/build/effect_users.json', 'w'), indent=0)
for k in sorted(uses):
    v = uses[k]
    uniq = []
    for x in v:
        if x not in uniq: uniq.append(x)
    print('%3d ($%02X): %s' % (k, k, '; '.join(uniq[:8]) + (' (+%d more)' % (len(uniq) - 8) if len(uniq) > 8 else '')))
