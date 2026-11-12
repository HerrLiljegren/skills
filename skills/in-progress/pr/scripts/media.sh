#!/usr/bin/env bash
# Prepare PR media: check tools, crop, annotate, render Mermaid, convert video to GIF.
# Each command writes one output file and prints its path.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: media.sh <command> [args]

  check                                   Report which media tools work, and how to fix the rest
  crop     <in> <out> <WxH+X+Y>           Crop to the region that changed (2x captures: double the numbers)
  annotate <in> <out> <WxH+X+Y> [label]   Draw a box (and optional label) around the change
  mermaid  <in.mmd> <out.png>             Render a Mermaid diagram to a 2x PNG on white
  gif      <in.mp4|webm> <out.gif> [width] [fps]
                                          Convert a short recording to a GIF (default 960 px, 10 fps)
EOF
}

die() { echo "media.sh: $*" >&2; exit 1; }

# Prefer ImageMagick 7's `magick`; fall back to IM6's `convert`.
im() {
  if command -v magick >/dev/null; then magick "$@"; else convert "$@"; fi
}

# A global mmdc, else the pinned npm package through npx. mmdc's puppeteer wants its own
# downloaded Chrome; point it at an installed Chrome or Chromium instead when one exists.
# Called directly, not in $(...), so the export reaches mmdc.
use_system_chrome() {
  if [[ -z ${PUPPETEER_EXECUTABLE_PATH:-} ]]; then
    local b
    for b in google-chrome-stable google-chrome chromium chromium-browser \
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
      if command -v "$b" >/dev/null || [[ -x $b ]]; then
        PUPPETEER_EXECUTABLE_PATH=$(command -v "$b" || echo "$b")
        export PUPPETEER_EXECUTABLE_PATH
        break
      fi
    done
  fi
}

mmdc_cmd() {
  if command -v mmdc >/dev/null; then echo mmdc
  elif command -v npx >/dev/null; then echo "npx --yes @mermaid-js/mermaid-cli@11.4.2"
  else return 1
  fi
}

install_hint() {
  local pkg_arch=$1 pkg_apt=$2 pkg_brew=$3
  if command -v pacman >/dev/null; then echo "sudo pacman -S --needed $pkg_arch"
  elif command -v apt-get >/dev/null; then echo "sudo apt-get install -y $pkg_apt"
  elif command -v brew >/dev/null; then echo "brew install $pkg_brew"
  else echo "install $pkg_apt with your package manager"
  fi
}

check() {
  local missing=0
  report() { # name ok-flag purpose fix
    if [[ $2 == ok ]]; then printf 'ok       %-10s %s\n' "$1" "$3"
    else printf 'MISSING  %-10s %s\n         fix: %s\n' "$1" "$3" "$4"; missing=1
    fi
  }

  if command -v magick >/dev/null || command -v convert >/dev/null; then im_ok=ok; else im_ok=no; fi
  report imagemagick "$im_ok" "crop, annotate" "$(install_hint imagemagick imagemagick imagemagick)"

  command -v ffmpeg >/dev/null && ff_ok=ok || ff_ok=no
  report ffmpeg "$ff_ok" "video -> GIF" "$(install_hint ffmpeg ffmpeg ffmpeg)"

  # mmdc drives a headless Chrome; a render probe is the only reliable check.
  local mm_ok=no mm_fix="npm install -g @mermaid-js/mermaid-cli (needs Node 18+)"
  use_system_chrome
  if cmd=$(mmdc_cmd); then
    local tmp; tmp=$(mktemp -d)
    printf 'graph LR\n  a --> b\n' >"$tmp/probe.mmd"
    if $cmd -q -i "$tmp/probe.mmd" -o "$tmp/probe.png" >"$tmp/log" 2>&1 && [[ -s $tmp/probe.png ]]; then
      mm_ok=ok
    else
      mm_fix="render failed: $(grep -m1 -i error "$tmp/log" || echo unknown error)
         install Chrome or Chromium, or run: npx puppeteer browsers install chrome-headless-shell"
    fi
    rm -rf "$tmp"
  fi
  report mermaid "$mm_ok" "diagram -> PNG for hosts without Mermaid" "$mm_fix"

  return "$missing"
}

case ${1:-} in
  check) check ;;
  crop)
    [[ $# -eq 4 ]] || { usage; exit 2; }
    im "$2" -crop "$4" +repage "$3"; echo "$3" ;;
  annotate)
    [[ $# -ge 4 ]] || { usage; exit 2; }
    in=$2 out=$3 geom=$4 label=${5:-}
    [[ $geom =~ ^([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+)$ ]] || die "geometry must be WxH+X+Y"
    w=${BASH_REMATCH[1]} h=${BASH_REMATCH[2]} x=${BASH_REMATCH[3]} y=${BASH_REMATCH[4]}
    # Stroke and font scale with the image, so the mark stays visible on 2x captures.
    stroke=$(( $(im identify -format '%w' "$in") / 300 + 3 ))
    args=(-fill none -stroke '#e5133a' -strokewidth "$stroke"
      -draw "rectangle $x,$y $((x + w)),$((y + h))")
    if [[ -n $label ]]; then
      ty=$(( y > stroke * 12 ? y - stroke * 2 : y + h + stroke * 9 ))
      # ImageMagick's default font can lack glyphs (renders boxes); ask fontconfig for one.
      font=()
      if command -v fc-match >/dev/null; then font=(-font "$(fc-match -f '%{file}' sans-serif:bold)"); fi
      args+=("${font[@]}" -stroke none -fill white -undercolor '#e5133a'
        -pointsize $((stroke * 7)) -annotate "+$x+$ty" " $label ")
    fi
    im "$in" "${args[@]}" "$out"; echo "$out" ;;
  mermaid)
    [[ $# -eq 3 ]] || { usage; exit 2; }
    use_system_chrome
    cmd=$(mmdc_cmd) || die "mermaid CLI unavailable; run: media.sh check"
    $cmd -q -s 2 -b white -i "$2" -o "$3"; echo "$3" ;;
  gif)
    [[ $# -ge 3 ]] || { usage; exit 2; }
    width=${4:-960} fps=${5:-10}
    # Two-pass palette keeps UI colours clean and the file small.
    ffmpeg -loglevel error -y -i "$2" -vf \
      "fps=$fps,scale=$width:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5" \
      "$3"
    size=$(stat -c %s "$3" 2>/dev/null || stat -f %z "$3")
    (( size <= 10 * 1024 * 1024 )) || echo "media.sh: $3 is over 10 MiB; trim it, lower width or fps" >&2
    echo "$3" ;;
  -h|--help) usage ;;
  *) usage; exit 2 ;;
esac
