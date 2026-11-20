"""Tiny headless libretro frontend (ctypes) for scripted SNES runs and screenshots.

    emu = Emu(core_path, rom_path)
    emu.run(60)                       # frames
    emu.press('A', 2)                 # hold A for 2 frames, then release for 6
    emu.ram[0x05AE] = 0xD7            # WRAM poke ($7E0000 + offset)
    emu.png('shot.png')
    emu.audio.clear(); emu.run(120); emu.wav('x.wav')   # capture audio (stereo int16, 32040 Hz)
"""
import ctypes as C
import array, wave
from PIL import Image

CORE = '/home/claude/lufia2/deps/snes9x/libretro/snes9x_libretro.so'

BTN = {'B': 0, 'Y': 1, 'SELECT': 2, 'START': 3, 'UP': 4, 'DOWN': 5, 'LEFT': 6, 'RIGHT': 7,
       'A': 8, 'X': 9, 'L': 10, 'R': 11}


class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]


ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIOB = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)
POLL = C.CFUNCTYPE(None)
STATE = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class Emu:
    def __init__(self, core, rom, sram=None):
        self.lib = C.CDLL(core)
        self.fmt = 0
        self.frame = None
        self.held = set()
        self.held2 = set()
        self.audio = array.array('h')
        self.capture = True
        self.options, self._optbuf, self._optdirty = {}, {}, False
        self._cbs = [ENV(self._env), VIDEO(self._video), AUDIO(self._sample),
                     AUDIOB(self._batch), POLL(lambda: None), STATE(self._state)]
        L = self.lib
        L.retro_set_environment(self._cbs[0])
        L.retro_set_video_refresh(self._cbs[1])
        L.retro_set_audio_sample(self._cbs[2])
        L.retro_set_audio_sample_batch(self._cbs[3])
        L.retro_set_input_poll(self._cbs[4])
        L.retro_set_input_state(self._cbs[5])
        L.retro_init()
        self.romdata = open(rom, 'rb').read()
        self._buf = C.create_string_buffer(self.romdata, len(self.romdata))
        info = GameInfo(rom.encode(), C.cast(self._buf, C.c_void_p), len(self.romdata), None)
        assert L.retro_load_game(C.byref(info)), 'load failed'
        L.retro_set_controller_port_device(0, 1); L.retro_set_controller_port_device(1, 1)
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_size.restype = C.c_size_t
        p = L.retro_get_memory_data(2); n = L.retro_get_memory_size(2)
        self.ram = (C.c_uint8 * n).from_address(p)
        p = L.retro_get_memory_data(0); n = L.retro_get_memory_size(0)
        self.sram = (C.c_uint8 * n).from_address(p) if p else None
        if sram is not None and self.sram is not None:
            data = open(sram, 'rb').read() if isinstance(sram, str) else sram
            C.memmove(self.sram, data, min(len(data), n))
            L.retro_reset()

    def _env(self, cmd, data):
        cmd &= 0xFFFF
        if cmd == 10:                       # SET_PIXEL_FORMAT
            self.fmt = C.cast(data, C.POINTER(C.c_int)).contents.value; return True
        if cmd in (9, 31):                  # system / save directory
            C.cast(data, C.POINTER(C.c_char_p))[0] = b'/tmp'; return True
        if cmd == 15:                       # GET_VARIABLE (core options, e.g. snes9x_layer_1 = disabled)
            var = C.cast(data, C.POINTER(C.c_char_p * 2)).contents
            key = var[0].decode() if var[0] else ''
            if key in self.options:
                self._optbuf[key] = C.create_string_buffer(self.options[key].encode())
                C.cast(data, C.POINTER(C.c_void_p))[1] = C.cast(self._optbuf[key], C.c_void_p).value
                return True
            return False
        if cmd == 17:                       # GET_VARIABLE_UPDATE
            C.cast(data, C.POINTER(C.c_bool))[0] = self._optdirty
            self._optdirty = False; return True
        if cmd == 3:                        # GET_CAN_DUPE
            C.cast(data, C.POINTER(C.c_bool))[0] = True; return True
        return False

    def _video(self, data, w, h, pitch):
        if not data:
            return
        raw = C.string_at(data, pitch * h)
        self.frame = (raw, w, h, pitch)

    def _sample(self, l, r):
        if self.capture:
            self.audio.append(l); self.audio.append(r)

    def _batch(self, data, frames):
        if self.capture:
            self.audio.frombytes(C.string_at(data, frames * 4))
        return frames

    def _state(self, port, device, index, bid):
        held = self.held if port == 0 else self.held2
        return int(any(BTN[b] == bid for b in held))

    def layers(self, hide=()):
        """Hide layers for the next frames: 1-4 = BG1-BG4, 5 = sprites."""
        self.options = {'snes9x_layer_%d' % i: 'disabled' if i in hide else 'enabled' for i in range(1, 6)}
        self._optdirty = True

    def run(self, n=1):
        for _ in range(n):
            self.lib.retro_run()

    def press(self, *buttons, hold=3, gap=8):
        self.held = set(buttons); self.run(hold); self.held = set(); self.run(gap)

    def wav(self, path, rate=32040):
        w = wave.open(path, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(self.audio.tobytes()); w.close(); return path

    def rms(self, start=0):
        a = self.audio[start:]
        if not a:
            return 0.0
        return (sum(x * x for x in a) / len(a)) ** 0.5

    def image(self):
        raw, w, h, pitch = self.frame
        if self.fmt == 1:                   # XRGB8888
            return Image.frombuffer('RGBX', (w, h), raw, 'raw', 'BGRX', pitch, 1).convert('RGB')
        img = Image.new('RGB', (w, h)); px = img.load()   # RGB565
        for y in range(h):
            row = raw[y * pitch:(y * pitch) + 2 * w]
            for x in range(w):
                v = row[2 * x] | row[2 * x + 1] << 8
                px[x, y] = ((v >> 11) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3)
        return img

    def png(self, path, scale=2):
        img = self.image()
        img.resize((img.width * scale, img.height * scale), Image.NEAREST).save(path)
        return path

    def save_state(self):
        n = self.lib.retro_serialize_size(); buf = C.create_string_buffer(n)
        assert self.lib.retro_serialize(buf, n); return buf.raw

    def load_state(self, data):
        buf = C.create_string_buffer(data, len(data)); assert self.lib.retro_unserialize(buf, len(data))
