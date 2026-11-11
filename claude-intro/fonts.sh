#!/bin/sh
# Fetch the OFL fonts into fonts/ (not kept in git). Noto Sans SC is subset by the Google Fonts CSS API
# to the Chinese characters that appear in film.js and lines.json. FORCE=1 fetches again.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D="$HERE/fonts"; mkdir -p "$D"
GF=https://raw.githubusercontent.com/google/fonts/86aced91de05cd4f96a06838124cca45be337b2b
get() {
  [ -s "$D/$1" ] && [ -z "$FORCE" ] && return 0
  curl -fsSL -g --retry 2 -o "$D/download.part" "$2" || { rm -f "$D/download.part"; echo "could not fetch $1" >&2; exit 1; }
  mv "$D/download.part" "$D/$1"; echo "fonts/$1"
}
get Inter.ttf "$GF/ofl/inter/Inter[opsz,wght].ttf"
get InterTight-var.woff2 "https://fonts.gstatic.com/s/intertight/v9/NGSwv5HMAFg6IuGlBNMjxLsH8ahuQ2e8.woff2"
get JetBrainsMono-var.ttf "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/19371302b95d218af43299bce79ddbddd0bc364d/fonts/variable/JetBrainsMono[wght].ttf"
CHARS=$(python3 -c "
import re,sys,urllib.parse
s=open('$HERE/film.js',encoding='utf8').read()+open('$HERE/lines.json',encoding='utf8').read()
cs=sorted(set(c for c in s if ord(c)>0x2000))
print(urllib.parse.quote(''.join(cs)+'0123456789'))")
STAMP="$D/.notosc-chars"
if [ "$(cat "$STAMP" 2>/dev/null)" != "$CHARS" ] || [ -n "$FORCE" ]; then
  for w in 400 500 600 700; do
    URL=$(curl -fsSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36" \
      "https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@$w&text=$CHARS" | grep -o 'https://[^)]*' | head -1)
    curl -fsSL -o "$D/NotoSansSC-$w.woff2" "$URL"; echo "fonts/NotoSansSC-$w.woff2"
  done
  echo "$CHARS" > "$STAMP"
fi
