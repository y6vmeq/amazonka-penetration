"""Transcribe audio of video/audio files with faster-whisper (local, CPU).

Usage (from project root):
    python -P tools/transcribe.py [--model large-v3-turbo] [--lang ru] <file1.mp4> [<file2.mp4> ...]

For each input writes next to it:
    <name>.transcript.txt  — segments "[mm:ss.s – mm:ss.s] text" (+ detected language, model)
    <name>.transcript.json — raw segments with word timestamps
Language: by default auto-detect (Russian/Belarusian speech); pass --lang ru to force Russian.
"""
import argparse, json, os, sys, time

from faster_whisper import WhisperModel


def fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:04.1f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--lang", default=None)
    args = ap.parse_args()

    t0 = time.time()
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    print(f"model {args.model} loaded in {time.time() - t0:.0f}s", flush=True)

    for path in args.files:
        t1 = time.time()
        import av  # installed with faster-whisper
        with av.open(path) as container:
            has_audio = any(s.type == "audio" for s in container.streams)
        if not has_audio:
            base = os.path.splitext(path)[0]
            with open(base + ".transcript.txt", "w", encoding="utf-8") as f:
                f.write(f"# Расшифровка: {os.path.basename(path)}\n\n(в файле нет звуковой дорожки — "
                        "звук мог отдаваться площадкой отдельным потоком; см. описание источника)\n")
            print(f"{os.path.basename(path)}: no audio stream", flush=True)
            continue
        segments, info = model.transcribe(
            path, language=args.lang, beam_size=5, vad_filter=True, word_timestamps=True,
            condition_on_previous_text=False,
        )
        segs = list(segments)
        base = os.path.splitext(path)[0]
        lines = [
            f"# Расшифровка: {os.path.basename(path)}",
            f"# Модель: faster-whisper {args.model}; язык: {info.language} (p={info.language_probability:.2f}); "
            f"длительность: {info.duration:.1f} с; автоматическая расшифровка — сверять на слух перед цитированием",
            "",
        ]
        if not segs:
            lines.append("(речь не обнаружена)")
        for s in segs:
            lines.append(f"[{fmt(s.start)} – {fmt(s.end)}] {s.text.strip()}")
        with open(base + ".transcript.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with open(base + ".transcript.json", "w", encoding="utf-8") as f:
            json.dump({
                "file": os.path.basename(path), "model": args.model, "language": info.language,
                "language_probability": info.language_probability, "duration": info.duration,
                "segments": [{"start": s.start, "end": s.end, "text": s.text.strip(),
                              "words": [{"start": w.start, "end": w.end, "word": w.word, "p": w.probability}
                                        for w in (s.words or [])]} for s in segs],
            }, f, ensure_ascii=False, indent=1)
        print(f"{os.path.basename(path)}: {len(segs)} segments, lang={info.language}, {time.time() - t1:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
