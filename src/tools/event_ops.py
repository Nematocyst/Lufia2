"""Static operand analysis of the FIELD EVENT script opcodes (table $80:E5A4, 191 entries).
(Adapted from script_ops.py.)

For each opcode handler, explores every path (through callees) until it
returns to the interpreter loop, recording the sequence of script reads:
  'b' = SceneScriptReadOperand ($80:C0B7), 'w' = SceneScriptReadWord ($80:C0D0),
  '<' = step back one byte ($80:C0EC), 'S' = SceneScriptSeekRelative (goto).
Also notes writes to the script pointer ($09B7) and text_state ($099B), and
any direct use of Y (which would make the static count unreliable).

Output: build/event_ops.json
"""
import json

import rom
from opcodes import OPS

A = json.load(open('/home/claude/lufia2/build/analysis.json'))
insn = {int(k): v for k, v in A['insn'].items()}
labels = {int(k): v for k, v in A['labels'].items()}
d = rom.load()

R_BYTE = rom.to_off(0x80E8B9)   # FieldReadEventByte
R_WORD = rom.to_off(0x80E8AD)   # FieldReadEventWord
R_BACK = rom.to_off(0x80E8D0)   # FieldRewindEventByte
R_SEEK = rom.to_off(0x80E8F4)   # FieldSetEventPointer
ENDS = {rom.to_off(0x80CC35): 'next'}
OPT = rom.to_off(0x80E5A4)
MAXREADS = 10
MAXSTATES = 4000

summ_cache = {}


def target_of(off, mn, mode, val):
    pc = rom.to_cpu(off)
    size = insn[off][2]
    if mode == 'rel8':
        disp = val - 256 if val > 127 else val
        return rom.to_off((pc & 0xFF0000) | ((pc + size + disp) & 0xFFFF))
    if mode == 'rel16':
        disp = val - 65536 if val > 32767 else val
        return rom.to_off((pc & 0xFF0000) | ((pc + size + disp) & 0xFFFF))
    if mode == 'abs':
        return rom.to_off((pc & 0xFF0000) | val)
    if mode == 'absl':
        return rom.to_off(val)
    return None


def explore(entry, is_handler, depth=0):
    """Return dict(paths=set of (reads, end), flags=set)."""
    if not is_handler and entry in summ_cache:
        return summ_cache[entry]
    if not is_handler:
        summ_cache[entry] = {'paths': {((), 'ret')}, 'flags': {'recursive'}}  # guard
    flags = set()
    paths = set()
    stack = [(entry, (), None)]
    seen = set()
    while stack:
        off, reads, ck = stack.pop()
        if len(seen) > MAXSTATES:
            flags.add('state-limit')
            break
        if (off, reads, ck) in seen:
            continue
        seen.add((off, reads, ck))
        if len(reads) > MAXREADS:
            paths.add((reads[:MAXREADS], 'var'))
            flags.add('variable')
            continue
        if is_handler and off in ENDS:
            paths.add((reads, ENDS[off]))
            continue
        if off not in insn:
            flags.add('untraced@%06X' % rom.to_cpu(off))
            paths.add((reads, '?'))
            continue
        op = d[off]
        mn, mode = OPS[op]
        size = insn[off][2]
        val = int.from_bytes(d[off + 1:off + size], 'little') if size > 1 else 0
        nxt = off + size
        # pointer / text-state bookkeeping
        if mn == 'PHY':                     # Y saved on the stack: later reads are look-ahead
            stack.append((nxt, reads, (ck or ()) + (reads,)))
            continue
        if mn == 'PLY' and ck:              # Y restored: discard reads since the PHY
            stack.append((nxt, ck[-1], ck[:-1]))
            continue
        if mode == 'abs' and val == 0x09B7 and mn == 'STY':
            stack.append((nxt, reads, reads))  # checkpoint: Y saved
            continue
        if mode == 'abs' and val == 0x09B7 and mn == 'LDY' and ck is not None:
            stack.append((nxt, ck, ck))  # Y restored: read-ahead discarded
            continue
        if mode in ('abs',) and val == 0x09B7 and mn in ('STA', 'STX', 'STZ'):
            flags.add('setptr')
        if mode in ('abs',) and val == 0x099B and mn in ('STA', 'STZ', 'TRB', 'TSB'):
            flags.add('textstate:' + mn)
        if mn in ('LDY', 'TAY', 'PLY', 'TXY', 'INY', 'DEY') and (op != 0xA0 or True):
            flags.add('y:' + mn)
        if mn in ('JSR', 'JSL') and mode in ('abs', 'absl'):
            t = target_of(off, mn, mode, val)
            if t == R_BYTE:
                stack.append((nxt, reads + ('b',), ck))
                continue
            if t == R_WORD:
                stack.append((nxt, reads + ('w',), ck))
                continue
            if t == R_BACK:
                stack.append((nxt, reads + ('<',), ck))
                continue
            if t == R_SEEK:
                stack.append((nxt, reads + ('S',), ck))
                continue
            if mn == 'JSL':                 # event readers are JSR-only; JSL'd code (start other events,
                stack.append((nxt, reads, ck))   # find records) reads its own streams and restores Y
                continue
            if t is None or depth > 6:
                stack.append((nxt, reads, ck))
                continue
            sub = explore(t, False, depth + 1)
            flags |= {f for f in sub['flags'] if f.startswith(('setptr', 'textstate', 'variable'))}
            for r, e in sub['paths']:
                if e in ('ret', 'var'):
                    stack.append((nxt, reads + r, ck))
                else:
                    paths.add((reads + r, 'sub-' + e))
            continue
        if mn in ('RTS', 'RTL', 'RTI'):
            paths.add((reads, 'ret' if not is_handler else 'yield'))
            continue
        if mn in ('BRK', 'COP', 'STP'):
            paths.add((reads, 'trap'))
            continue
        if mode in ('rel8', 'rel16'):
            t = target_of(off, mn, mode, val)
            stack.append((t, reads, ck))
            if mn not in ('BRA', 'BRL'):
                stack.append((nxt, reads, ck))
            continue
        if mn in ('JMP', 'JML') and mode in ('abs', 'absl'):
            stack.append((target_of(off, mn, mode, val), reads, ck))
            continue
        if mn in ('JMP', 'JML'):
            flags.add('indirect-jump')
            paths.add((reads, 'indirect'))
            continue
        if mode == 'absxi':  # JSR (abs,X)
            flags.add('indirect-call')
        stack.append((nxt, reads, ck))
    res = {'paths': paths, 'flags': flags}
    if not is_handler:
        summ_cache[entry] = res
    return res


def fmt_reads(r):
    return ''.join(r)


out = {}
for i in range(191):
    h = d[OPT + 2 * i] | d[OPT + 2 * i + 1] << 8
    off = rom.to_off(0x800000 | h)
    res = explore(off, True)
    def net(r):
        return sum(2 if c == 'w' else 1 if c == 'b' else -1 if c == '<' else 0 for c in r)
    lens = sorted({net(r) for r, e in res['paths']
                   if not (r and r[-1] == '<') and e not in ('trap',) and net(r) >= 0})
    out['%02X' % i] = {
        'handler': '%06X' % rom.to_cpu(off),
        'label': labels.get(off, ''),
        'paths': sorted({(fmt_reads(r), e) for r, e in res['paths']}),
        'lengths': lens,
        'flags': sorted(res['flags']),
    }
json.dump(out, open('/home/claude/lufia2/build/event_ops.json', 'w'), indent=1)
fixed = sum(1 for v in out.values() if len(v['lengths']) == 1 and 'variable' not in v['flags'])
print('opcodes', len(out), 'single fixed length', fixed)
for k, v in out.items():
    print(k, v['handler'], v['lengths'], ' '.join('%s>%s' % p for p in v['paths'][:5]),
          ','.join(f for f in v['flags'] if not f.startswith('y:')))
