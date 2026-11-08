"""Reference TOTP (HMAC-SHA1) written from scratch, plus RFC test vectors.

Everything here is plain Python ints masked to 32 bits so the same operations
map 1:1 onto the hardware datapath model in datapath.py.
"""
import hashlib
import hmac as _hmac
import struct

M32 = 0xFFFFFFFF


def rol(x, n):
    return ((x << n) | (x >> (32 - n))) & M32


IV = (0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0)
K = (0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xCA62C1D6)


def compress(state, block16):
    """One SHA-1 compression. block16 = 16 big-endian 32-bit words."""
    w = list(block16)
    for t in range(16, 80):
        w.append(rol(w[t - 3] ^ w[t - 8] ^ w[t - 14] ^ w[t - 16], 1))
    a, b, c, d, e = state
    for t in range(80):
        if t < 20:
            f = (b & c) | (~b & M32 & d)
        elif t < 40:
            f = b ^ c ^ d
        elif t < 60:
            f = (b & c) | (b & d) | (c & d)
        else:
            f = b ^ c ^ d
        tmp = (rol(a, 5) + f + e + K[t // 20] + w[t]) & M32
        a, b, c, d, e = tmp, a, rol(b, 30), c, d
    return tuple((s + v) & M32 for s, v in zip(state, (a, b, c, d, e)))


def sha1(msg: bytes) -> bytes:
    ml = len(msg) * 8
    msg += b"\x80"
    msg += b"\x00" * ((56 - len(msg) % 64) % 64)
    msg += struct.pack(">Q", ml)
    st = IV
    for i in range(0, len(msg), 64):
        st = compress(st, struct.unpack(">16I", msg[i:i + 64]))
    return struct.pack(">5I", *st)


def hmac_sha1(key: bytes, msg: bytes) -> bytes:
    if len(key) > 64:
        key = sha1(key)
    key = key.ljust(64, b"\x00")
    ipad = bytes(b ^ 0x36 for b in key)
    opad = bytes(b ^ 0x5C for b in key)
    return sha1(opad + sha1(ipad + msg))


def truncate(digest: bytes, digits: int = 6) -> int:
    off = digest[19] & 0xF
    code = struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF
    return code % (10 ** digits)


def hotp(key: bytes, counter: int, digits: int = 6) -> int:
    return truncate(hmac_sha1(key, struct.pack(">Q", counter)), digits)


def totp(key: bytes, unix_time: int, period: int = 30, digits: int = 6) -> int:
    return hotp(key, unix_time // period, digits)


if __name__ == "__main__":
    # Our SHA-1 / HMAC vs the standard library
    for m in (b"", b"abc", b"a" * 55, b"a" * 56, b"a" * 64, b"x" * 1000):
        assert sha1(m) == hashlib.sha1(m).digest(), m
    for k in (b"k", b"12345678901234567890", b"z" * 64, b"z" * 100):
        assert hmac_sha1(k, b"msg") == _hmac.new(k, b"msg", hashlib.sha1).digest()

    # RFC 4226 Appendix D (6 digits)
    key = b"12345678901234567890"
    exp = [755224, 287082, 359152, 969429, 338314,
           254676, 287922, 162583, 399871, 520489]
    for c, e in enumerate(exp):
        assert hotp(key, c) == e, (c, hotp(key, c), e)

    # RFC 6238 Appendix B, SHA-1 (8 digits)
    for t, e in [(59, 94287082), (1111111109, 7081804), (1111111111, 14050471),
                 (1234567890, 89005924), (2000000000, 69279037),
                 (20000000000, 65353130)]:
        assert totp(key, t, digits=8) == e, (t, totp(key, t, digits=8), e)

    print("reference OK: sha1, hmac, RFC 4226 (10 vectors), RFC 6238 (6 vectors)")