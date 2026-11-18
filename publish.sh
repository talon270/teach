#!/usr/bin/env bash
# Copy INT301 pages from the study folder into this repo, fix links, commit, push.
set -euo pipefail
S="/home/talon/SyncedWork/soomaries/study"
SRC="$S/Monsoon 2026 - 1/teach/INT301"
NOTES="$S/Notes/Monsoon 2026 - 1/INT301"
R="$(cd "$(dirname "$0")" && pwd)"
cd "$R"
rsync -a --delete "$SRC/lessons/" lessons/
rsync -a --delete "$SRC/assets/" assets/
cp "$SRC/index.html" index.html
rsync -a --delete --exclude '*.backup-*' --exclude '*.sync-conflict-*' --include '*.html' --exclude '*' "$NOTES/" notes/
# fix links: notes live in notes/, the hub page is not published
sed -i 's#\.\./\.\./\.\./\.\./Notes/Monsoon%202026%20-%201/INT301/#../notes/#g' lessons/*.html index.html
sed -i 's#href="\.\./index\.html"#href="index.html"#g' index.html
touch .nojekyll
git add -A
if git diff --cached --quiet; then echo "Nothing to publish."; exit 0; fi
git commit -q -m "Update INT301 pages $(date +%F-%H%M)"
git push -q origin main
echo "Pushed. Live in about a minute."
