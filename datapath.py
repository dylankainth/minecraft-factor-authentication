"""Bit-exact register-transfer model of the proposed redstone TOTP core.

Architecture (what the redstone build would implement):
  * Secret key is baked in. Offline we precompute
        S_in  = compress(IV, key ^ ipad)      S_out = compress(IV, key ^ opad)
    so the circuit only ever runs TWO compressions per code.
  * One round engine: registers a,b,c,d,e (5x32) + 16x32 schedule shift reg.
    One SHA-1 round per clock cycle -> 80 cycles per compression.
  * Inner pass: block = [0, counter, 0x80000000, 0 x12, 0x240], start state S_in.
    Outer pass: block = [H0..H4, 0x80000000, 0 x9, 0x2A0], start state S_out.
  * Truncation: pick 4 bytes at digest[19]&15, clear top bit, then mod 10^digits
    via restoring shift-subtract (one bit per cycle).

Model counts clock cycles and 32-bit word operations so we can size the build.
"""
import random
import struct
from collections import Counter

import ref
from ref import M32, rol, IV, K


class Core:
    def __init__(self, key: bytes, digits: int = 6):
        if len(key) > 64:
            key = ref.sha1(key)
        key = key.ljust(64, b"\x00")
        ipad = struct.unpack(">16I", bytes(b ^ 0x36 for b in key))
        opad = struct.unpack(">16I", bytes(b ^ 0x5C for b in key))
        # offline precompute (this is the "baked-in key" ROM content)
        self.s_in = ref.compress(IV, ipad)
        self.s_out = ref.compress(IV, opad)
        self.digits = digits
        self.cycles = 0
        self.ops = Counter()

    # ---- one compression, one round per cycle -------------------------
    def _compress(self, start, block):
        a, b, c, d, e = start
        sched = [0] * 16                      # holds W[t-16 .. t-1]
        for t in range(80):
            if t < 16:
                w = block[t]
            else:
                x = sched[13] ^ sched[8] ^ sched[2] ^ sched[0]
                self.ops["xor32"] += 3
                w = rol(x, 1)                 # rotate = pure wiring
            sched = sched[1:] + [w]           # shift register
            if t < 20:
                f = (b & c) | (~b & M32 & d)
                self.ops["and/or32"] += 3     # mux-style (b?c:d)
            elif t < 40 or t >= 60:
                f = b ^ c ^ d
                self.ops["xor32"] += 2
            else:
                f = (b & c) | (b & d) | (c & d)
                self.ops["and/or32"] += 5
            tmp = (rol(a, 5) + f + e + K[t // 20] + w) & M32
            self.ops["add32"] += 4
            a, b, c, d, e = tmp, a, rol(b, 30), c, d
            self.cycles += 1
        out = tuple((s + v) & M32 for s, v in zip(start, (a, b, c, d, e)))
        self.ops["add32"] += 5                # feed-forward (reuse adder, +5 cyc)
        self.cycles += 5
        return out

    # ---- truncation + mod via restoring division ----------------------
    def _trunc_mod(self, digest_words):
        digest = struct.pack(">5I", *digest_words)
        off = digest[19] & 0xF                # 16:1 byte mux
        v = struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF
        mod = 10 ** self.digits
        rem = 0
        for i in range(30, -1, -1):           # 31 cycles, 1 bit each
            rem = (rem << 1) | ((v >> i) & 1)
            if rem >= mod:
                rem -= mod
            self.cycles += 1
            self.ops["cmp+sub20"] += 1
        return rem

    def code(self, counter: int) -> int:
        self.cycles = 0
        self.ops = Counter()
        assert 0 <= counter <= M32
        blk_in = [0, counter, 0x80000000] + [0] * 12 + [0x240]
        h = self._compress(self.s_in, blk_in)
        blk_out = list(h) + [0x80000000] + [0] * 9 + [0x2A0]
        d = self._compress(self.s_out, blk_out)
        return self._trunc_mod(d)


if __name__ == "__main__":
    rnd = random.Random(1234)

    # RFC vectors through the hardware model
    core = Core(b"12345678901234567890")
    exp = [755224, 287082, 359152, 969429, 338314,
           254676, 287922, 162583, 399871, 520489]
    for c, e in enumerate(exp):
        assert core.code(c) == e
    c8 = Core(b"12345678901234567890", digits=8)
    for t, e in [(59, 94287082), (1111111109, 7081804), (1111111111, 14050471),
                 (1234567890, 89005924), (2000000000, 69279037)]:
        assert c8.code(t // 30) == e

    # randomized equivalence vs reference: keys of various lengths, counters
    n = 0
    for _ in range(3000):
        key = bytes(rnd.getrandbits(8) for _ in range(rnd.choice([10, 20, 32, 64, 80])))
        ctr = rnd.choice([0, 1, M32, rnd.getrandbits(32), rnd.getrandbits(31)])
        dg = rnd.choice([6, 6, 6, 8])
        assert Core(key, dg).code(ctr) == ref.hotp(key, ctr, dg), (key, ctr)
        n += 1

    core = Core(b"12345678901234567890")
    core.code(54321)
    print(f"datapath model OK: RFC vectors + {n} random keys/counters match reference")
    print(f"cycles per code: {core.cycles}  (2x(80+5) compress + 31 mod)")
    print("32-bit word ops per code:", dict(core.ops))
    print("state bits: 5x32 (a..e) + 16x32 (schedule) + 5x32 (inner digest) "
          "+ 32 (counter) + 31 (trunc/mod) =", 5*32 + 16*32 + 5*32 + 32 + 31)