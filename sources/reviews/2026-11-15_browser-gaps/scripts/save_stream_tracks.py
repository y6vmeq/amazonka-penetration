"""Сохраняет видео, полученное в браузере по сегментам (MPEG-DASH), и собирает один файл.

Запуск из корня проекта:

  python -I sources/reviews/2026-11-15_browser-gaps/scripts/save_stream_tracks.py \
      <папка_сбора> <временный.b64> <группа>

Временный файл записан Playwright MCP (browser_evaluate + filename): base64 от JSON
  {"meta": {..., "tracks": {"video": {"sha256": ..., "urls": [...]}, "audio": {...}}, "mpd": "<xml>"},
   "files": {"video": "<base64>", "audio": "<base64>"}}
Каждая дорожка — init-сегмент и все фрагменты подряд (фрагментированный MP4), как их отдал сервер.

Что делает:
  - пишет media/<группа>/<группа>_video.mp4 и <группа>_audio.mp4, сверяя SHA-256 с посчитанным в браузере;
  - пишет media/<группа>/manifest.mpd и download_meta.json (адреса сегментов, размеры, хэши);
  - собирает media/<группа>/<группа>.mp4 — видео и звук в одном файле без перекодирования (PyAV);
  - дописывает строки в media/manifest.jsonl.
Содержимое не исполняется. Временный файл удаляется.
"""
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import av


def remux(video_path, audio_path, target):
    """Складывает дорожки в один MP4 без перекодирования."""
    with av.open(str(video_path)) as video_in, av.open(str(audio_path)) as audio_in, \
            av.open(str(target), "w", format="mp4") as output:
        streams = {}
        for container in (video_in, audio_in):
            source = container.streams[0]
            streams[container] = (source, output.add_stream_from_template(source))
        for container, (source, destination) in streams.items():
            for packet in container.demux(source):
                if packet.dts is None:
                    continue
                packet.stream = destination
                output.mux(packet)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    collection_dir, temporary, group = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    raw = temporary.read_text(encoding="utf-8").strip().strip("'\"")
    capture = json.loads(base64.b64decode(raw).decode("utf-8"))
    meta, files = capture["meta"], capture["files"]

    group_dir = collection_dir / "media" / group
    group_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = meta.get("fetched_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = []
    paths = {}
    for number, kind in enumerate(("video", "audio"), 1):
        data = base64.b64decode(files[kind])
        digest = hashlib.sha256(data).hexdigest()
        track = meta["tracks"][kind]
        if digest != track["sha256"]:
            sys.exit(f"SHA-256 mismatch for {kind}: got {digest}, browser said {track['sha256']}")
        path = group_dir / f"{group}_{kind}.mp4"
        path.write_bytes(data)
        paths[kind] = path
        entries.append({
            "group": group, "n": number, "url": track["urls"][0],
            "file": path.relative_to(collection_dir).as_posix(), "bytes": len(data), "sha256": digest,
            "content_type": f"{kind}/mp4", "status": 200,
            "note": (
                f"дорожка {kind} потокового видео (MPEG-DASH, представление {track['id']}): init-сегмент и "
                f"{track['segments']} фрагм. подряд, как отдал сервер; получено в браузере (fetch), "
                "SHA-256 совпал с посчитанным в браузере"
            ),
            "fetched_at": fetched_at,
        })

    (group_dir / "manifest.mpd").write_bytes(meta["mpd"].encode("utf-8"))
    summary = {key: value for key, value in meta.items() if key != "mpd"}
    (group_dir / "download_meta.json").write_bytes(
        json.dumps(summary, ensure_ascii=False, indent=1).encode("utf-8")
    )

    combined = group_dir / f"{group}.mp4"
    remux(paths["video"], paths["audio"], combined)
    data = combined.read_bytes()
    entries.append({
        "group": group, "n": 3, "url": meta.get("player_url", ""),
        "file": combined.relative_to(collection_dir).as_posix(), "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "content_type": "video/mp4", "status": 200,
        "note": (
            "видео и звук в одном файле: собрано из двух дорожек выше без перекодирования (PyAV); "
            "это производный файл, исходные данные сервера — в файлах дорожек"
        ),
        "fetched_at": fetched_at,
    })

    with (collection_dir / "media" / "manifest.jsonl").open("a", encoding="utf-8", newline="\n") as manifest:
        for entry in entries:
            manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")
    temporary.unlink()
    print(json.dumps(
        [{"file": e["file"], "bytes": e["bytes"], "sha256": e["sha256"]} for e in entries], ensure_ascii=True
    ))


if __name__ == "__main__":
    main()
