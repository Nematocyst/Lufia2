"""Minimal 65816 interpreter for unit-testing ROM routines (native mode only).

Memory: LoROM ROM, 8 KB SRAM ($70:0000), 128 KB WRAM ($7E/$7F, mirrored at $00-$3F/$80-$BF:0000-1FFF),
the multiply/divide registers ($4202-$4206, $4214-$4217) and WMDATA ($2180-$2183).
Usage:
    cpu = CPU(rom_bytes); cpu.call(0x80C9C0, a=.., x=.., m=1, xf=0)   # runs until the RTL/RTS
Hooks: cpu.hooks[addr] = fn(cpu) -> True to emulate a routine and return from it.
"""
from opcodes import OPS


class Stop(Exception):
    pass


class CPU:
    def __init__(self, rom):
        self.rom = rom
        self.wram = bytearray(0x20000)
        self.io = {}
        self.hooks = {}
        self.sram = bytearray(0x2000)
        self.reset()

    def reset(self):
        self.A = self.X = self.Y = 0
        self.S = 0x1FF0; self.D = 0; self.DB = 0x7E; self.PB = 0x80; self.PC = 0
        self.n = self.v = self.z = self.c = 0
        self.m = self.xf = 1; self.d = 0; self.i = 1
        self.steps = 0

    # ------------------------------------------------------------ memory
    def _map(self, a):
        bank, off = (a >> 16) & 0xFF, a & 0xFFFF
        if bank in (0x7E, 0x7F):
            return 'w', ((bank & 1) << 16) | off
        if (bank & 0x7F) < 0x40 and off < 0x2000:
            return 'w', off
        if 0x70 <= bank <= 0x7D and off < 0x8000:
            return 's', off & 0x1FFF
        if off >= 0x8000:
            return 'r', (bank & 0x7F) * 0x8000 + off - 0x8000
        if (bank & 0x7F) < 0x40 and 0x2000 <= off < 0x6000:
            return 'io', off
        raise Stop('unmapped read/write %06X' % a)

    def rd(self, a):
        k, o = self._map(a & 0xFFFFFF)
        if k == 'w': return self.wram[o]
        if k == 'r': return self.rom[o] if o < len(self.rom) else 0
        if k == 's': return self.sram[o]
        return self.io_read(o)

    def wr(self, a, v):
        k, o = self._map(a & 0xFFFFFF)
        v &= 0xFF
        if k == 'w': self.wram[o] = v
        elif k == 'r': raise Stop('write to ROM %06X' % a)
        elif k == 's': self.sram[o] = v
        else: self.io_write(o, v)

    def io_read(self, o):
        if o == 0x2180:
            p = self.io.get('wm', 0); v = self.wram[p & 0x1FFFF]; self.io['wm'] = p + 1; return v
        if o in (0x4214, 0x4215, 0x4216, 0x4217):
            return self.io.get(o, 0)
        return self.io.get(o, 0)

    def io_write(self, o, v):
        self.io[o] = v
        if o == 0x4203:
            r = self.io.get(0x4202, 0) * v
            self.io[0x4216] = r & 0xFF; self.io[0x4217] = r >> 8
        elif o == 0x4206:
            num = self.io.get(0x4204, 0) | self.io.get(0x4205, 0) << 8
            q, r = (num // v, num % v) if v else (0xFFFF, num)
            self.io[0x4214] = q & 0xFF; self.io[0x4215] = q >> 8
            self.io[0x4216] = r & 0xFF; self.io[0x4217] = r >> 8
        elif o in (0x2181, 0x2182, 0x2183):
            p = self.io.get('wm', 0); sh = (o - 0x2181) * 8
            self.io['wm'] = (p & ~(0xFF << sh)) | (v << sh)
        elif o == 0x2180:
            p = self.io.get('wm', 0); self.wram[p & 0x1FFFF] = v; self.io['wm'] = p + 1

    def rd16(self, a, wrap_bank=False):
        if wrap_bank:
            return self.rd(a) | self.rd((a & 0xFF0000) | ((a + 1) & 0xFFFF)) << 8
        return self.rd(a) | self.rd(a + 1) << 8

    def wr16(self, a, v):
        self.wr(a, v); self.wr(a + 1, v >> 8)

    # ------------------------------------------------------------ helpers
    def fetch(self):
        v = self.rd(self.PB << 16 | self.PC); self.PC = (self.PC + 1) & 0xFFFF; return v

    def fetch16(self):
        return self.fetch() | self.fetch() << 8

    def push(self, v):
        self.wr(self.S, v); self.S = (self.S - 1) & 0xFFFF

    def pull(self):
        self.S = (self.S + 1) & 0xFFFF; return self.rd(self.S)

    def push16(self, v):
        self.push(v >> 8); self.push(v)

    def pull16(self):
        lo = self.pull(); return lo | self.pull() << 8

    @property
    def P(self):
        return (self.n << 7 | self.v << 6 | self.m << 5 | self.xf << 4 | self.d << 3 |
                self.i << 2 | self.z << 1 | self.c)

    @P.setter
    def P(self, p):
        self.n, self.v, self.m, self.xf = p >> 7 & 1, p >> 6 & 1, p >> 5 & 1, p >> 4 & 1
        self.d, self.i, self.z, self.c = p >> 3 & 1, p >> 2 & 1, p >> 1 & 1, p & 1
        if self.xf: self.X &= 0xFF; self.Y &= 0xFF

    def nz(self, v, w8):
        if w8: v &= 0xFF; self.n = v >> 7
        else: v &= 0xFFFF; self.n = v >> 15
        self.z = int(v == 0)
        return v

    def getA(self):
        return self.A & 0xFF if self.m else self.A

    def setA(self, v):
        if self.m: self.A = (self.A & 0xFF00) | (v & 0xFF)
        else: self.A = v & 0xFFFF

    # ------------------------------------------------------------ addressing
    def ea(self, mode):
        """Return effective 24-bit address for a memory mode."""
        if mode == 'dp': return (self.D + self.fetch()) & 0xFFFF
        if mode == 'dpx': return (self.D + self.fetch() + self.X) & 0xFFFF
        if mode == 'dpy': return (self.D + self.fetch() + self.Y) & 0xFFFF
        if mode == 'abs': return self.DB << 16 | self.fetch16()
        if mode == 'absx': return ((self.DB << 16 | self.fetch16()) + self.X) & 0xFFFFFF
        if mode == 'absy': return ((self.DB << 16 | self.fetch16()) + self.Y) & 0xFFFFFF
        if mode == 'absl': return self.fetch16() | self.fetch() << 16
        if mode == 'abslx': return ((self.fetch16() | self.fetch() << 16) + self.X) & 0xFFFFFF
        if mode == 'dpi':
            p = (self.D + self.fetch()) & 0xFFFF; return self.DB << 16 | self.rd16(p)
        if mode == 'dpxi':
            p = (self.D + self.fetch() + self.X) & 0xFFFF; return self.DB << 16 | self.rd16(p)
        if mode == 'dpiy':
            p = (self.D + self.fetch()) & 0xFFFF; return ((self.DB << 16 | self.rd16(p)) + self.Y) & 0xFFFFFF
        if mode == 'dpil':
            p = (self.D + self.fetch()) & 0xFFFF; return self.rd16(p) | self.rd(p + 2) << 16
        if mode == 'dpily':
            p = (self.D + self.fetch()) & 0xFFFF; return ((self.rd16(p) | self.rd(p + 2) << 16) + self.Y) & 0xFFFFFF
        if mode == 'sr': return (self.S + self.fetch()) & 0xFFFF
        if mode == 'sriy':
            p = (self.S + self.fetch()) & 0xFFFF; return ((self.DB << 16 | self.rd16(p)) + self.Y) & 0xFFFFFF
        raise Stop('mode ' + mode)

    def operand(self, mode, wide):
        """Read operand value (for loads/ALU)."""
        if mode in ('immm', 'immx'):
            return self.fetch16() if wide else self.fetch()
        a = self.ea(mode)
        return self.rd16(a) if wide else self.rd(a)

    # ------------------------------------------------------------ run
    def call(self, addr, a=None, x=None, y=None, m=None, xf=None, db=None, d=None, max_steps=200000):
        if m is not None: self.m = m
        if xf is not None: self.xf = xf
        if a is not None: self.A = a
        if x is not None: self.X = x
        if y is not None: self.Y = y
        if db is not None: self.DB = db
        if d is not None: self.D = d
        # fake return address: JSL from $00:FFF0 (an RTL lands there and stops)
        self.push(0x00); self.push16(0xFFF2)
        base_s = self.S
        self.PB, self.PC = addr >> 16, addr & 0xFFFF
        while True:
            if (self.PB << 16 | self.PC) == 0x00FFF3 and self.S == base_s + 3:
                return
            self.step()
            self.steps += 1
            if self.steps > max_steps:
                raise Stop('step limit at %02X:%04X' % (self.PB, self.PC))

    def step(self):
        pc = self.PB << 16 | self.PC
        if pc in self.hooks:
            if self.hooks[pc](self):
                # emulate RTL
                self.PC = (self.pull16() + 1) & 0xFFFF; self.PB = self.pull(); return
        op = self.fetch()
        mn, mode = OPS[op]
        f = getattr(self, 'op_' + mn, None)
        if f is None:
            raise Stop('unimplemented %s at %06X' % (mn, pc))
        f(mode)

    # ------------------------------------------------------------ instructions
    def _ld(self, mode, reg):
        wide = not (self.m if reg == 'A' else self.xf)
        v = self.operand(mode, wide)
        self.nz(v, not wide)
        if reg == 'A': self.setA(v)
        else: setattr(self, reg, v)

    def op_LDA(self, mode): self._ld(mode, 'A')
    def op_LDX(self, mode): self._ld(mode, 'X')
    def op_LDY(self, mode): self._ld(mode, 'Y')

    def _st(self, mode, v, w8):
        a = self.ea(mode)
        if w8: self.wr(a, v)
        else: self.wr16(a, v)

    def op_STA(self, mode): self._st(mode, self.getA(), self.m)
    def op_STX(self, mode): self._st(mode, self.X, self.xf)
    def op_STY(self, mode): self._st(mode, self.Y, self.xf)
    def op_STZ(self, mode): self._st(mode, 0, self.m)

    def _alu(self, mode):
        return self.operand(mode, not self.m)

    def op_AND(self, mode): self.setA(self.nz(self.getA() & self._alu(mode), self.m))
    def op_ORA(self, mode): self.setA(self.nz(self.getA() | self._alu(mode), self.m))
    def op_EOR(self, mode): self.setA(self.nz(self.getA() ^ self._alu(mode), self.m))

    def op_ADC(self, mode):
        b = self._alu(mode); a = self.getA(); bits = 8 if self.m else 16; mask = (1 << bits) - 1
        if self.d: raise Stop('decimal mode')
        r = a + b + self.c
        self.v = int(((~(a ^ b)) & (a ^ r)) >> (bits - 1) & 1)
        self.c = int(r > mask)
        self.setA(self.nz(r, self.m))

    def op_SBC(self, mode):
        b = self._alu(mode); a = self.getA(); bits = 8 if self.m else 16; mask = (1 << bits) - 1
        r = a - b - (1 - self.c)
        self.v = int(((a ^ b) & (a ^ r)) >> (bits - 1) & 1)
        self.c = int(r >= 0)
        self.setA(self.nz(r & mask, self.m))

    def _cmp(self, reg_v, mode, w8):
        b = self.operand(mode, not w8)
        r = reg_v - b
        self.c = int(r >= 0)
        self.nz(r & (0xFF if w8 else 0xFFFF), w8)

    def op_CMP(self, mode): self._cmp(self.getA(), mode, self.m)
    def op_CPX(self, mode): self._cmp(self.X, mode, self.xf)
    def op_CPY(self, mode): self._cmp(self.Y, mode, self.xf)

    def op_BIT(self, mode):
        b = self._alu(mode); a = self.getA()
        self.z = int((a & b) == 0)
        if mode != 'immm':
            bits = 8 if self.m else 16
            self.n = b >> (bits - 1) & 1; self.v = b >> (bits - 2) & 1

    def _rmw(self, mode, fn):
        if mode == 'acc':
            self.setA(fn(self.getA())); return
        a = self.ea(mode)
        if self.m: self.wr(a, fn(self.rd(a)))
        else: self.wr16(a, fn(self.rd16(a)))

    def op_INC(self, mode): self._rmw(mode, lambda v: self.nz(v + 1, self.m))
    def op_DEC(self, mode): self._rmw(mode, lambda v: self.nz(v - 1, self.m))

    def op_ASL(self, mode):
        def f(v):
            bits = 8 if self.m else 16; self.c = v >> (bits - 1) & 1; return self.nz(v << 1, self.m)
        self._rmw(mode, f)

    def op_LSR(self, mode):
        def f(v):
            self.c = v & 1; return self.nz(v >> 1, self.m)
        self._rmw(mode, f)

    def op_ROL(self, mode):
        def f(v):
            bits = 8 if self.m else 16; c = self.c; self.c = v >> (bits - 1) & 1
            return self.nz(v << 1 | c, self.m)
        self._rmw(mode, f)

    def op_ROR(self, mode):
        def f(v):
            bits = 8 if self.m else 16; c = self.c; self.c = v & 1
            return self.nz(v >> 1 | c << (bits - 1), self.m)
        self._rmw(mode, f)

    def op_TSB(self, mode):
        def f(v):
            self.z = int((v & self.getA()) == 0); return v | self.getA()
        self._rmw(mode, f)

    def op_TRB(self, mode):
        def f(v):
            self.z = int((v & self.getA()) == 0); return v & ~self.getA()
        self._rmw(mode, f)

    def _idx(self, reg, d):
        v = (getattr(self, reg) + d) & (0xFF if self.xf else 0xFFFF)
        setattr(self, reg, v); self.nz(v, self.xf)

    def op_INX(self, mode): self._idx('X', 1)
    def op_INY(self, mode): self._idx('Y', 1)
    def op_DEX(self, mode): self._idx('X', -1)
    def op_DEY(self, mode): self._idx('Y', -1)

    def _br(self, cond):
        off = self.fetch()
        if cond:
            self.PC = (self.PC + (off - 256 if off > 127 else off)) & 0xFFFF

    def op_BPL(self, m): self._br(not self.n)
    def op_BMI(self, m): self._br(self.n)
    def op_BVC(self, m): self._br(not self.v)
    def op_BVS(self, m): self._br(self.v)
    def op_BCC(self, m): self._br(not self.c)
    def op_BCS(self, m): self._br(self.c)
    def op_BNE(self, m): self._br(not self.z)
    def op_BEQ(self, m): self._br(self.z)
    def op_BRA(self, m): self._br(True)

    def op_BRL(self, m):
        off = self.fetch16(); self.PC = (self.PC + (off - 0x10000 if off > 0x7FFF else off)) & 0xFFFF

    def op_JMP(self, mode):
        if mode == 'abs': self.PC = self.fetch16()
        elif mode == 'absi': p = self.fetch16(); self.PC = self.rd16(p)
        elif mode == 'absxi':
            p = (self.fetch16() + self.X) & 0xFFFF; self.PC = self.rd16(self.PB << 16 | p)
        else: raise Stop('jmp ' + mode)

    def op_JML(self, mode):
        if mode == 'absl':
            a = self.fetch16() | self.fetch() << 16
        else:
            p = self.fetch16(); a = self.rd16(p) | self.rd(p + 2) << 16
        self.PB, self.PC = a >> 16, a & 0xFFFF

    def op_JSR(self, mode):
        if mode == 'abs':
            t = self.fetch16(); self.push16((self.PC - 1) & 0xFFFF); self.PC = t
        else:
            p = self.fetch16(); self.push16((self.PC - 1) & 0xFFFF)
            self.PC = self.rd16(self.PB << 16 | ((p + self.X) & 0xFFFF))

    def op_JSL(self, mode):
        t = self.fetch16() | self.fetch() << 16
        self.push(self.PB); self.push16((self.PC - 1) & 0xFFFF)
        self.PB, self.PC = t >> 16, t & 0xFFFF

    def op_RTS(self, m): self.PC = (self.pull16() + 1) & 0xFFFF

    def op_RTL(self, m):
        self.PC = (self.pull16() + 1) & 0xFFFF; self.PB = self.pull()

    def op_PHA(self, m):
        if self.m: self.push(self.A & 0xFF)
        else: self.push16(self.A)

    def op_PLA(self, m):
        if self.m: self.setA(self.nz(self.pull(), True))
        else: self.A = self.nz(self.pull16(), False)

    def _phr(self, reg):
        v = getattr(self, reg)
        if self.xf: self.push(v)
        else: self.push16(v)

    def _plr(self, reg):
        v = self.pull() if self.xf else self.pull16()
        setattr(self, reg, self.nz(v, self.xf))

    def op_PHX(self, m): self._phr('X')
    def op_PHY(self, m): self._phr('Y')
    def op_PLX(self, m): self._plr('X')
    def op_PLY(self, m): self._plr('Y')
    def op_PHB(self, m): self.push(self.DB)
    def op_PLB(self, m): self.DB = self.nz(self.pull(), True)
    def op_PHK(self, m): self.push(self.PB)
    def op_PHD(self, m): self.push16(self.D)
    def op_PLD(self, m): self.D = self.nz(self.pull16(), False)
    def op_PHP(self, m): self.push(self.P)
    def op_PLP(self, m): self.P = self.pull()
    def op_PEA(self, m): self.push16(self.fetch16())

    def op_PEI(self, m):
        p = (self.D + self.fetch()) & 0xFFFF; self.push16(self.rd16(p))

    def op_PER(self, m):
        off = self.fetch16(); self.push16((self.PC + off) & 0xFFFF)

    def op_REP(self, m): self.P = self.P & ~self.fetch()
    def op_SEP(self, m): self.P = self.P | self.fetch()
    def op_CLC(self, m): self.c = 0
    def op_SEC(self, m): self.c = 1
    def op_CLI(self, m): self.i = 0
    def op_SEI(self, m): self.i = 1
    def op_CLD(self, m): self.d = 0
    def op_SED(self, m): self.d = 1
    def op_CLV(self, m): self.v = 0
    def op_NOP(self, m): pass
    def op_WDM(self, m): self.fetch()
    def op_XCE(self, m): pass

    def _t(self, src, dst, w8):
        v = getattr(self, src) if src != 'A' else self.A
        if dst == 'A':
            if self.m: self.A = (self.A & 0xFF00) | (v & 0xFF)
            else: self.A = v & 0xFFFF
            self.nz(self.A, self.m)
        elif dst in ('X', 'Y'):
            v &= 0xFF if self.xf else 0xFFFF
            setattr(self, dst, v); self.nz(v, self.xf)

    def op_TAX(self, m): self._t('A', 'X', self.xf)
    def op_TAY(self, m): self._t('A', 'Y', self.xf)
    def op_TXA(self, m): self._t('X', 'A', self.m)
    def op_TYA(self, m): self._t('Y', 'A', self.m)
    def op_TXY(self, m): self._t('X', 'Y', self.xf)
    def op_TYX(self, m): self._t('Y', 'X', self.xf)
    def op_TSX(self, m): self._t('S', 'X', self.xf)
    def op_TXS(self, m): self.S = self.X
    def op_TCS(self, m): self.S = self.A
    def op_TSC(self, m): self.A = self.nz(self.S, False)
    def op_TCD(self, m): self.D = self.nz(self.A, False)
    def op_TDC(self, m): self.A = self.nz(self.D, False)

    def op_XBA(self, m):
        self.A = ((self.A & 0xFF) << 8) | (self.A >> 8); self.nz(self.A & 0xFF, True)

    def op_MVN(self, mode): self._mv(1)
    def op_MVP(self, mode): self._mv(-1)

    def _mv(self, step):
        dst = self.fetch(); src = self.fetch(); self.DB = dst
        while True:
            self.wr(dst << 16 | self.Y, self.rd(src << 16 | self.X))
            self.X = (self.X + step) & 0xFFFF; self.Y = (self.Y + step) & 0xFFFF
            self.A = (self.A - 1) & 0xFFFF
            if self.A == 0xFFFF: break
