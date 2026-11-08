"""Gate-level netlist model of the SHA-1 round engine, built from a
redstone-realistic primitive set, with per-gate delays in redstone ticks (rt).

Primitive delays (textbook redstone-engineering convention; NOT yet measured
against a real MCHPRS build -- see CLAUDE.md "Recon findings"):
    NOT (torch inverter):               1 rt
    OR  (dust merge):                   0 rt
    AND (De Morgan via 2 NOTs + NOR):    2 rt
    XOR (torch-based XOR circuit):       2 rt
Registers (D flip-flops) are modelled as resetting signal delay to 0 at each
clock edge; the required clock period is the max combinational delay produced
during the cycle that feeds them.

This module:
  1. Builds 32-bit ripple-carry and carry-select adders out of single-bit
     gates (addition must be bit-serial -- carry propagation is exactly the
     thing being compared, so word-wide ops are wrong here).
  2. Builds the SHA-1 round function (f, schedule XOR, rotate-as-wiring,
     5-operand add tree) out of the same gates.
  3. Runs the full HMAC-SHA1 TOTP core (2 compressions + truncate/mod) through
     the gate model and checks the result bit-exactly against ref.py /
     datapath.py on the RFC vectors plus a random sample.
  4. Reports gate counts and the critical-path clock period (in rt) for each
     adder choice, and converts that to an estimated wall-clock time per code
     under measured MCHPRS /rtps semantics (2 game ticks = 1 redstone tick).
"""
import random
import struct
from collections import Counter

import ref
from ref import M32, IV, K

COUNTS = Counter()


def reset_counts():
    COUNTS.clear()


# ---- single-bit gates: signal = (value:0/1, delay:int rt) -----------------
def g_not(s):
    COUNTS["NOT"] += 1
    return (1 - s[0], s[1] + 1)


def g_and(s1, s2):
    COUNTS["AND"] += 1
    return (s1[0] & s2[0], max(s1[1], s2[1]) + 2)


def g_or(s1, s2):
    COUNTS["OR"] += 1
    return (s1[0] | s2[0], max(s1[1], s2[1]) + 0)


def g_xor(s1, s2):
    COUNTS["XOR"] += 1
    return (s1[0] ^ s2[0], max(s1[1], s2[1]) + 2)


def mux_bit(sel, x, y):
    """2:1 mux: sel ? x : y, built from NOT/AND/OR."""
    n = g_not(sel)
    a1 = g_and(n, y)
    a2 = g_and(sel, x)
    return g_or(a1, a2)


# ---- 32-bit words as tuples of 32 signals, LSB-first -----------------------
def to_word(x):
    return tuple(((x >> i) & 1, 0) for i in range(32))


def from_word(w):
    return sum(v << i for i, (v, _) in enumerate(w)) & M32


def word_delay(w):
    return max(d for _, d in w)


def word_not(w):
    return tuple(g_not(b) for b in w)


def word_and(w1, w2):
    return tuple(g_and(a, b) for a, b in zip(w1, w2))


def word_or(w1, w2):
    return tuple(g_or(a, b) for a, b in zip(w1, w2))


def word_xor(w1, w2):
    return tuple(g_xor(a, b) for a, b in zip(w1, w2))


def word_mux(sel_signal, w_true, w_false):
    return tuple(mux_bit(sel_signal, x, y) for x, y in zip(w_true, w_false))


def rol_word(w, n):
    """Left rotate by n bits: pure wiring, zero extra delay."""
    return tuple(w[(i - n) % 32] for i in range(32))


# ---- adders -----------------------------------------------------------------
def full_adder(a, b, cin):
    t1 = g_xor(a, b)
    s = g_xor(t1, cin)
    g1 = g_and(a, b)
    g2 = g_and(t1, cin)
    cout = g_or(g1, g2)
    return s, cout


def ripple_add32(a, b):
    cin = (0, 0)
    out = []
    for i in range(32):
        s, cin = full_adder(a[i], b[i], cin)
        out.append(s)
    return tuple(out)


def carry_select_add32(a, b, block=8):
    n = 32
    out = [None] * n
    c_prev = (0, 0)
    i = 0
    first = True
    while i < n:
        bw = min(block, n - i)
        ablk, bblk = a[i:i + bw], b[i:i + bw]
        if first:
            c = c_prev
            blk = []
            for k in range(bw):
                s, c = full_adder(ablk[k], bblk[k], c)
                blk.append(s)
            c_prev = c
            first = False
        else:
            c0 = (0, 0)
            s0 = []
            for k in range(bw):
                s, c0 = full_adder(ablk[k], bblk[k], c0)
                s0.append(s)
            carry0 = c0
            c1 = (1, 0)
            s1 = []
            for k in range(bw):
                s, c1 = full_adder(ablk[k], bblk[k], c1)
                s1.append(s)
            carry1 = c1
            sel = c_prev
            blk = [mux_bit(sel, s1[k], s0[k]) for k in range(bw)]
            c_prev = mux_bit(sel, carry1, carry0)
        for k, s in enumerate(blk):
            out[i + k] = s
        i += bw
    return tuple(out)


def add_tree(words, adder):
    """Pairwise-reduce an operand list with the given 2-input adder."""
    words = list(words)
    while len(words) > 1:
        nxt = []
        j = 0
        while j + 1 < len(words):
            nxt.append(adder(words[j], words[j + 1]))
            j += 2
        if j < len(words):
            nxt.append(words[j])
        words = nxt
    return words[0]


# ---- SHA-1 round function ---------------------------------------------------
def f_function(b, c, d, t):
    if t < 20:
        return word_or(word_and(b, c), word_and(word_not(b), d))
    elif t < 40 or t >= 60:
        return word_xor(word_xor(b, c), d)
    else:
        return word_or(word_or(word_and(b, c), word_and(b, d)), word_and(c, d))


def compress(start, block, adder):
    """One SHA-1 compression. start/block are tuples of gate-words.
    Returns (out_words, round_delays[80])."""
    a, b, c, d, e = start
    sched = list(block)
    round_delays = []
    for t in range(80):
        if t < 16:
            w = block[t]
        else:
            x = word_xor(word_xor(word_xor(sched[13], sched[8]), sched[2]), sched[0])
            w = rol_word(x, 1)
        sched = sched[1:] + [w]
        f = f_function(b, c, d, t)
        rol5a = rol_word(a, 5)
        tmp = add_tree([rol5a, f, e, to_word(K[t // 20]), w], adder)
        round_delays.append(word_delay(tmp))
        # register boundary: values latch, delay resets to 0 next cycle
        tmp0 = tuple((v, 0) for v, _ in tmp)
        a2 = tuple((v, 0) for v, _ in a)
        b2 = rol_word(tuple((v, 0) for v, _ in b), 30)
        c2 = tuple((v, 0) for v, _ in c)
        d2 = tuple((v, 0) for v, _ in d)
        a, b, c, d, e = tmp0, a2, b2, c2, d2
    out = tuple(add_tree([s, v], adder) for s, v in zip(start, (a, b, c, d, e)))
    out = tuple(tuple((v, 0) for v, _ in word) for word in out)
    return out, round_delays


def trunc_mod(digest_words, digits, adder):
    """digest_words: 5 gate-words (big-endian H0..H4, as in ref.truncate)."""
    digest = struct.pack(">5I", *(from_word(w) for w in digest_words))
    off = digest[19] & 0xF
    v = struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF
    mod = 10 ** digits
    rem = 0
    for i in range(30, -1, -1):
        rem = (rem << 1) | ((v >> i) & 1)
        if rem >= mod:
            rem -= mod
        COUNTS["cmp+sub20"] += 1
    return rem


def totp_code(key: bytes, counter: int, digits: int, adder):
    if len(key) > 64:
        key = ref.sha1(key)
    key = key.ljust(64, b"\x00")
    ipad = struct.unpack(">16I", bytes(b ^ 0x36 for b in key))
    opad = struct.unpack(">16I", bytes(b ^ 0x5C for b in key))
    s_in = ref.compress(IV, ipad)
    s_out = ref.compress(IV, opad)

    blk_in = [to_word(w) for w in (0, counter, 0x80000000) + (0,) * 12 + (0x240,)]
    rd1 = compress(tuple(to_word(w) for w in s_in), tuple(blk_in), adder)
    h, delays1 = rd1

    blk_out = [h[0], h[1], h[2], h[3], h[4], to_word(0x80000000)] + \
              [to_word(0)] * 9 + [to_word(0x2A0)]
    d, delays2 = compress(tuple(to_word(w) for w in s_out), tuple(blk_out), adder)

    code = trunc_mod(d, digits, adder)
    return code, delays1 + delays2


if __name__ == "__main__":
    key = b"12345678901234567890"
    rfc10 = [755224, 287082, 359152, 969429, 338314,
             254676, 287922, 162583, 399871, 520489]

    for name, adder in (("ripple", ripple_add32), ("carry_select_8", carry_select_add32)):
        max_delay = 0
        for c, exp in enumerate(rfc10):
            code, delays = totp_code(key, c, 6, adder)
            assert code == exp, (name, c, code, exp)
            max_delay = max(max_delay, max(delays))
        n = 0
        rnd = random.Random(99)
        for _ in range(40):
            k = bytes(rnd.getrandbits(8) for _ in range(rnd.choice([10, 20, 32])))
            ctr = rnd.getrandbits(32)
            code, delays = totp_code(k, ctr, 6, adder)
            assert code == ref.hotp(k, ctr, 6), (name, k, ctr)
            max_delay = max(max_delay, max(delays))
            n += 1

        # gate count for exactly one code (reset immediately before)
        reset_counts()
        totp_code(key, 0, 6, adder)
        gates = dict(COUNTS)
        cycles = 201
        clock_period_rt = max_delay
        total_rt = clock_period_rt * cycles
        print(f"--- adder: {name} ---")
        print(f"  verified: RFC vectors (10) + {n} random keys/counters, bit-exact")
        print(f"  critical path per round: {clock_period_rt} rt  "
              f"-> clock period must be >= that")
        print(f"  total redstone ticks per code (model): {total_rt} rt "
              f"({cycles} cycles x {clock_period_rt} rt)")
        print(f"  gate counts (one code, 2 compressions + mod): {gates}")
        game_ticks = total_rt * 2  # confirmed: 2 game ticks = 1 redstone tick (MCHPRS)
        for rtps in (10, 20, 100, 1000):
            secs = total_rt / rtps
            print(f"  est. time per code @ /rtps {rtps}: {secs:.2f} s  "
                  f"[ESTIMATE from gate-delay model, not a measured build]")
        print()

    print("Carry-lookahead (32-bit, 5-level P/G tree) is NOT implemented at "
          "gate level here -- closed-form estimate only:")
    print("  depth ~= 2 * ceil(log2(32)) * max(AND,XOR delay) ~= 2*5*2 = 20 rt "
          "[UNVERIFIED estimate, not simulated]")
