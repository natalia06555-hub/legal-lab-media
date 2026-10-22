"""Фоновая музыка в стиле первого Reels: мягкие пэды, арпеджио, лёгкий бит. Оригинальная, генерируется кодом."""
import numpy as np
from scipy.io import wavfile

SR = 44100

PROGS = [([[57,60,64],[53,57,60],[48,52,55],[55,59,62]],[45,41,48,43]),
         ([[50,53,57],[46,50,53],[53,57,60],[52,55,59]],[38,46,41,40]),
         ([[52,55,59],[48,52,55],[55,59,62],[50,54,57]],[40,48,43,38]),
         ([[57,60,64],[52,55,59],[53,57,60],[52,56,59]],[45,40,41,40])]

def compose(path, DUR, seed=1):
    BPM = 92 if seed % 2 else 88
    beat = 60 / BPM
    t_total = np.arange(int(SR * DUR)) / SR
    out = np.zeros_like(t_total)

    def note(f):
        return 440 * 2 ** ((f - 69) / 12)

    # Am - F - C - G, two bars each chord (4 beats per bar)
    chords, bass = PROGS[seed % len(PROGS)]
    chord_len = 4 * beat * 2

    def env(n, a=0.05, r=0.4):
        e = np.ones(n)
        ai = int(a * SR); ri = int(r * SR)
        e[:ai] = np.linspace(0, 1, ai)
        e[-ri:] = np.linspace(1, 0, ri)
        return e

    i = 0
    t0 = 0.0
    while t0 < DUR:
        ch = chords[i % 4]
        s = int(t0 * SR); n = min(int(chord_len * SR), len(out) - s)
        tt = np.arange(n) / SR
        pad = sum(np.sin(2 * np.pi * note(m) * tt) + 0.3 * np.sin(2 * np.pi * note(m) * 2.003 * tt) for m in ch)
        out[s:s + n] += 0.06 * pad * env(n, 0.6, 0.8)
        b = bass[i % 4]
        out[s:s + n] += 0.12 * np.sin(2 * np.pi * note(b - 12) * tt) * env(n, 0.05, 0.5)
        # arpeggio, eighth notes
        step = beat / 2
        for k in range(int(chord_len / step)):
            m = ch[k % 3] + 12
            ss = s + int(k * step * SR); nn = int(step * SR * 0.9)
            if ss + nn > len(out): break
            ta = np.arange(nn) / SR
            out[ss:ss + nn] += 0.035 * np.sin(2 * np.pi * note(m) * ta) * np.exp(-ta * 6)
        i += 1
        t0 += chord_len

    # soft kick on beats 1 and 3, hat on offbeats, start after 2 bars
    rng = np.random.default_rng(seed)
    t = 8 * beat
    while t < DUR - 1:
        for k in range(4):
            tb = t + k * beat
            s = int(tb * SR)
            if k in (0, 2):
                n = int(0.25 * SR); tt = np.arange(n) / SR
                f = 110 * np.exp(-tt * 18) + 45
                kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
                seg = kick[: max(0, len(out) - s)]
                out[s:s + len(seg)] += 0.22 * seg
            sh = int((tb + beat / 2) * SR); n = int(0.05 * SR)
            if sh + n < len(out):
                out[sh:sh + n] += 0.02 * rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 80)
        t += 4 * beat

    # fades
    fi = int(1.5 * SR); fo = int(2.5 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    out /= np.max(np.abs(out)) * 1.15
    wavfile.write(path, SR, (out * 32767).astype(np.int16))
    return path

if __name__ == '__main__':
    import sys
    compose(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 1)
