#!/bin/sh
# One command rebuilds the film: fonts → voice → events → readcheck → mix → subtitles → render → master.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
LIB=${LIB:-$HOME/lemo-opuscar}
export LIB
[ -f "$LIB/core/render/video.mjs" ] || { echo "set LIB to the Lemo-Opuscar library folder"; exit 1; }
PY="$LIB/.venv/bin/python"
sh "$HERE/fonts.sh"
cd "$LIB"
"$PY" core/tts/tts_zh.py "$HERE/lines.json" "$HERE/voices" --voice zh-CN-YunxiNeural --rate=-4%
"$PY" core/tts/asr_check.py "$HERE/lines.json" "$HERE/voices" --lang zh || echo "asr: check the lines listed above by ear (Chinese homophones are expected)"
node core/render/events.mjs "$HERE"
node core/render/readcheck.mjs "$HERE"
"$PY" "$HERE/mix.py"
"$PY" "$HERE/tools/subs.py"
"$PY" core/render/srt.py "$HERE/out/cues.json" "$HERE/claude-intro.srt"
node core/render/video.mjs "$HERE" --fps 24 --workers ${WORKERS:-4} --out "$HERE/out/video.mp4"
sh core/render/mux.sh "$HERE/out/video.mp4" "$HERE/out/mix.wav" "$HERE/claude-intro.mp4" 24 0
node core/render/still.mjs "$HERE" 36.5 --out "$HERE/out" --prefix poster_ && cp "$HERE/out/poster_36.5.jpg" "$HERE/poster.jpg"
