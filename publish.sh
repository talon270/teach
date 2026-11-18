#!/usr/bin/env bash
# Mirror all course pages from the study folder into this repo, rebuild the landing page, commit, push.
set -euo pipefail
S="/home/talon/SyncedWork/soomaries/study"
SEM="Monsoon 2026 - 1"
TEACH="$S/$SEM/teach"
NOTES="$S/Notes/$SEM"
R="$(cd "$(dirname "$0")" && pwd)"
cd "$R"; mkdir -p notes
# only web files; no PDFs, docs, md, backups or sync conflicts
FILT=(--prune-empty-dirs --exclude '*.backup-*' --exclude '*.sync-conflict-*'
  --include '*/' --include '*.html' --include '*.css' --include '*.js'
  --include '*.png' --include '*.jpg' --include '*.jpeg' --include '*.svg' --include '*.webp' --include '*.woff2'
  --exclude '*')
# notes also keep .md answer files that the lessons link to
NFILT=("${FILT[@]:0:${#FILT[@]}-2}" --include '*.md' --exclude '*')
for d in "$TEACH"/*/; do
  c="$(basename "$d")"
  [ -f "$d/index.html" ] || continue
  rsync -a --delete "${FILT[@]}" "$d" "$c/"
  if [ -d "$NOTES/$c" ]; then rsync -a --delete "${NFILT[@]}" "$NOTES/$c/" "notes/$c/"; else rm -rf "notes/$c"; fi
done
# remove course folders that no longer exist in the source
for d in */; do
  c="${d%/}"; [ "$c" = notes ] && continue; [ -f "$d/index.html" ] || continue
  [ -d "$TEACH/$c" ] || rm -rf "$c" "notes/$c"
done
cp -p "$TEACH/index.html" plan.html
python3 -I build.py
touch .nojekyll
git add -A
if git diff --cached --quiet; then echo "Nothing to publish."; exit 0; fi
git commit -q -m "Update teach pages $(date +%F-%H%M)"
git push -q origin HEAD:main
echo "Pushed. Live in about a minute: https://talon270.github.io/teach/"
