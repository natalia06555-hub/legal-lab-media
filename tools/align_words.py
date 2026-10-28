"""Тайминги слов для make_motion_reel.py.

python3 tools/align_words.py <папка_рилс> <transcript.json>

<папка>/narration.txt — текст озвучки ровно в том виде, в каком он ушёл в Speko (его слова и пойдут в титры).
transcript.json — результат Speko audio.transcribe(word_timestamps=true) по ИСХОДНОЙ (не ускоренной) озвучке.
Выход: <папка>/words_raw.json — [[слово, start_ms], ...]: слова сценария со временем из транскрипта.
Числа и слова, которые распознаватель записал иначе («12 часов» → «12:00»), получают время интерполяцией.
"""
import json, re, sys, difflib


def norm(w):
    return re.sub(r"[^0-9a-zа-я]", "", w.lower().replace("ё", "е"))


def main(d, tpath):
    text = open(f"{d}/narration.txt").read()
    # тире и одиночные знаки приклеиваем к предыдущему слову
    toks = []
    for t in text.split():
        if not norm(t) and toks:
            toks[-1] += " " + t
        else:
            toks.append(t)
    tr = json.load(open(tpath))
    tw = [w for w in tr["words"] if norm(w["text"])]
    a = [norm(t) for t in toks]
    b = [norm(w["text"]) for w in tw]
    times = [None] * len(toks)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = tw[blk.b + k]["start_ms"]
    # заменённые фрагменты: равномерно между соседями
    end = tw[-1]["end_ms"] if tw else 1000
    i = 0
    while i < len(times):
        if times[i] is None:
            j = i
            while j < len(times) and times[j] is None:
                j += 1
            lo = times[i - 1] if i > 0 else 0
            hi = times[j] if j < len(times) else end
            for k in range(i, j):
                times[k] = int(lo + (hi - lo) * (k - i + 1) / (j - i + 1))
            i = j
        else:
            i += 1
    for k in range(1, len(times)):
        times[k] = max(times[k], times[k - 1])
    matched = sum(1 for x in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks() for _ in range(x.size))
    json.dump([[t, ms] for t, ms in zip(toks, times)], open(f"{d}/words_raw.json", "w"), ensure_ascii=False)
    print(f"words: {len(toks)}, matched: {matched} ({100 * matched // max(1, len(toks))}%)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
