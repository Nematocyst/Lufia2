# Lufia II disassembly — status (2026-10-20)

## Result
- US ROM (CRC32 20F2AC29, SHA1 A89931C1…2B84), LoROM FastROM, headerless, 2.5 MB.
- asar source tree in `disasm/` rebuilds the ROM **byte-identical** (`build.sh` checks SHA1).
- 90,381 instructions / 202 KB code; 1,925 named routines; 72 jump tables; 0 overlaps; 451 width conflicts (trusted decoding kept).
- Coverage: $80 90%, $81 95%, $82 98%, $83 96%, $84 78%, $85 75%, $86 68%, $8E 16%. No code traced in $87–$CF.
- **Script decompiler done** (tools/scriptdec.py): 242 maps, 1,587 entry points, 226 KB script, 0 invalid opcodes, 0 overlaps, 0 bad glyphs, 98% of $87:8000–$8E:A89D covered. Output docs/scripts/map_XX.txt + ALL_DIALOGUE.txt; format in docs/SCRIPTS.md.

## Method
- Seeds: vectors + Lufia2Decomp `metadata/functions.toml` (1,922 verified functions with names + entry M/X) + recomp `bank*.cfg` funcs + `tools/seeds.toml`.
- Tracer computes each routine's return widths (set vs inherited), iterates to fixpoint. Decomp `exit_mx` is unreliable when equal to entry.
- Gap discovery adds clean-looking routines (78 auto seeds); rejects ASCII and branch-first spans.
- Emitter: explicit widths, numeric data operands, labels only on line-start code targets → byte-exact.
- asar quirk: `MVN a,b` emits bytes in written order.
- Script operand lengths: tools/script_ops.py static path analysis (reader calls b/w, step-back '<', seek 'S', $09B7 STY/LDY checkpoint for text measuring) + manual special cases.

## Script format (key facts)
- Map record $87:8010+id*8: w0/b2 = script block (base=w0+$8000, bank $87+b2 → $099E/$09A0); w3/b5 = entry script; w6 = name offset from $87:8000. (TCRF's "$87:8016" = name word inside record.)
- Block: "PH" + 6 word offsets (slots 2,4,6,8,A,C) → [id, word] lists ending $FF; script = base+word. Slot 6 = NPC talk by actor id; slot 4 = arrival by entrance id; slot 8 = event control; slot 2 id 3 = chest table [obj+1, item word] 0-terminated (not a script).
- Goto ($80:A3C6) relative to base; if base+word ≥ $8000 stays in CURRENT DB bank (goto never reloads DB), else bank $09A0+1. Entry scripts run with base $8000 (labels E_xxxx).
- Text mode = text_state bit0: opened by 08/10/13/61–67/9E; closed by 01/0B/00/42/18/53/5B/BC. In text mode $10–$7F ASCII, $80–$FF dict $200+n; 05/06 xx dict; 03 nl; 04 xx delay; 09 hero; 0C–0F punct+nl; 0A lo hi back-reference (copy (hi>>4)+2 from addr+1 − 12-bit).
- Special ops: 10 choice (n, n targets), 12 switch (var, n, n targets), 14 condition list (term rules in SCRIPTS.md; type 20 goto-if-true, 30 goto-if-false), 15/6A goto if flag set/clear, 41 2(+1), 5B sub+1, 6D/6E word+zstring.
- 125 rarely used opcodes still unnamed (op_XX).

## Key addresses
- `$82:8028` InlinePointerDispatch; `$82:B14E` table = 5 entries.
- `$80:9CB8` script step, `$80:9D00` dispatch loop, `$80:CA14` ScriptOpcodeTable, `$8E:EA00` TextDictionary.
- `$80:C0B7` read byte, `$80:C0D0` read word, `$80:C0EC` step back, `$80:C102` seek, `$80:C12E` find record.
- Second interpreter (not decompiled yet): field events `$80:CC35`, table `tbl_80E5A4`, pointer `$7F:D196`.
- Debug: PAR 8380C7D4 → `DebugFieldHook $8E:B0D4`; flag `$7E:057C`.

## Resources / caveats
- Lufia2Decomp — no license file; Lufia2SNESRecomp — PolyForm Noncommercial.
- disasm/ and docs/scripts/ contain game data/text → keep private; publish tools/ + SCRIPTS.md only.

## Next candidates
- Field event interpreter decompiler (same approach).
- Name remaining script opcodes; data formats (items, enemies, maps, compression); bank $8E gaps.
