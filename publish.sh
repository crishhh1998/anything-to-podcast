#!/bin/bash
# Publish podcast episodes to GitHub Pages
set -e

cd "$(dirname "$0")"

git add docs/
git commit -m "Add new podcast episode(s)"
git push origin main

echo ""
echo "Published! Feed URL:"
echo "  https://crishhh1998.github.io/anything-to-podcast/feed.xml"
