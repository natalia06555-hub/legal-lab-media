"""Проверка и распаковка озвучки Speko.

python3 tools/voice_check.py <результат_speko.json> <папка_рилс> [tempo]

Проверяет, что озвучку сделал google-tts и что голос женский (медианная F0 > 165 Гц).
Если всё в порядке: пишет <папка>/raw.wav (исходная) и <папка>/narration.wav (ускоренная в tempo раз, по умолчанию 1.1),
печатает OK, длительность и signed URL (для Speko audio.transcribe — действует 15 минут).
Иначе печатает FAIL с причиной и завершается с кодом 1 — такую озвучку не использовать.
"""
import base64, json, subprocess, sys, wave, os
import numpy as np


def f0(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
    sr, out = 16000, []
    for i in range(0, len(x) - 640, 320):
        s = x[i:i + 640]
        if np.abs(s).mean() < 300:
            continue
        s = s - s.mean()
        c = np.correlate(s, s, "full")[639:]
        lo, hi = sr // 400, sr // 70
        l = lo + int(np.argmax(c[lo:hi]))
        if c[l] > 0.4 * c[0]:
            out.append(sr / l)
    return float(np.median(out)) if out else 0.0


def main(res, d, tempo=1.1):
    r = json.load(open(res))
    if r.get("provider") != "google-tts":
        print("FAIL provider", r.get("provider")); sys.exit(1)
    os.makedirs(d, exist_ok=True)
    open(f"{d}/raw.bin", "wb").write(base64.b64decode(r["audio_base64"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/raw.bin", "-ar", "44100", "-ac", "1", f"{d}/raw.wav"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/raw.bin", "-ac", "1", "-ar", "16000", f"{d}/_v16.wav"], check=True)
    hz = f0(f"{d}/_v16.wav")
    os.remove(f"{d}/_v16.wav"); os.remove(f"{d}/raw.bin")
    if hz < 165:
        print(f"FAIL pitch {hz:.0f} Hz (мужской голос?)"); sys.exit(1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/raw.wav", "-af", f"atempo={tempo}", f"{d}/narration.wav"], check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{d}/narration.wav"]).decode())
    print(f"OK google-tts, F0 {hz:.0f} Hz, narration {dur:.1f}s (tempo {tempo})")
    print("URL", r["url"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.1)
