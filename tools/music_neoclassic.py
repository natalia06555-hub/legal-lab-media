"""Оригинальная неоклассическая фортепианная музыка (генерируется кодом, без чужих записей).

compose(path, duration_sec, seed)
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 44100

PROGRESSIONS = [
    # (тоника, аккорды в виде MIDI-триад)
    [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]],   # Am F C G
    [[50, 53, 57], [46, 50, 53], [53, 57, 60], [52, 55, 59]],   # Dm Bb F Em
    [[52, 55, 59], [48, 52, 55], [55, 59, 62], [50, 54, 57]],   # Em C G D
    [[57, 60, 64], [52, 55, 59], [53, 57, 60], [52, 56, 59]],   # Am Em F E
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def piano(m, dur, vel=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    sig = np.zeros(n)
    for k, a in enumerate([1.0, 0.55, 0.3, 0.18, 0.1, 0.06], 1):
        fk = f * k * (1 + 0.0004 * k * k)
        sig += a * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.2 + 0.9 * k) * (f / 440) ** 0.3)
    att = int(0.004 * SR)
    sig[:att] *= np.linspace(0, 1, att)
    rel = int(0.08 * SR)
    sig[-rel:] *= np.linspace(1, 0, rel)
    return vel * sig


def add(buf, sig, start):
    s = int(start * SR)
    e = min(len(buf), s + len(sig))
    if s < len(buf):
        buf[s:e] += sig[: e - s]


def compose(path, duration, seed=1):
    rng = np.random.default_rng(seed)
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    bpm = rng.integers(64, 76)
    beat = 60 / bpm
    bar = 4 * beat
    out = np.zeros(int((duration + 3) * SR))
    t, i, prev_mel = 0.0, 0, prog[0][2] + 12
    while t < duration:
        ch = prog[i % 4]
        root = ch[0] - 12
        lh = [root, root + 7, ch[1], ch[2], root + 12, ch[2], ch[1], root + 7]
        for k, m in enumerate(lh):
            add(out, piano(m, beat * 1.6, 0.16 if k else 0.22), t + k * beat / 2)
        if i >= 1:
            pool = [x + 12 for x in ch] + [x + 24 for x in ch[:1]]
            pos = 0.0
            while pos < bar - 0.01:
                d = beat * rng.choice([1, 1, 2, 1.5]) if pos + beat <= bar else bar - pos
                d = min(d, bar - pos)
                cand = sorted(pool, key=lambda x: abs(x - prev_mel))[:3]
                m = int(rng.choice(cand))
                add(out, piano(m, d + 0.8, 0.28), t + pos)
                prev_mel, pos = m, pos + d
        t += bar
        i += 1
    ir_n = int(1.6 * SR)
    ir = np.random.default_rng(0).standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR * 3.2)
    ir[0] = 1.0
    wet = fftconvolve(out, ir)[: len(out)]
    mix = out + 0.06 * wet / (np.max(np.abs(wet)) + 1e-9) * np.max(np.abs(out))
    mix = mix[: int(duration * SR)]
    fi, fo = int(1.0 * SR), int(2.5 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= np.max(np.abs(mix)) * 1.12
    wavfile.write(path, SR, (mix * 32767).astype(np.int16))
    return path


if __name__ == "__main__":
    import sys
    compose(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 1)
