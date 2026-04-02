#!/bin/bash
# Podcast Manager - 生成、发布、删除播客
set -e
cd "$(dirname "$0")"

usage() {
    echo "用法:"
    echo "  ./manage.sh add <url或本地pdf路径>   生成并发布新一期"
    echo "  ./manage.sh list                     列出所有期"
    echo "  ./manage.sh delete <序号>            删除某一期"
    echo ""
    echo "示例:"
    echo "  ./manage.sh add https://arxiv.org/pdf/2404.02905"
    echo "  ./manage.sh add ./paper.pdf"
    echo "  ./manage.sh list"
    echo "  ./manage.sh delete 1"
}

publish() {
    git add docs/
    git commit -m "Update podcast"
    git push origin main
    echo ""
    echo "已发布! Feed: https://crishhh1998.github.io/anything-to-podcast/feed.xml"
}

case "${1}" in
    add)
        [ -z "$2" ] && echo "请提供 URL 或文件路径" && exit 1
        python main.py "$2"
        publish
        ;;
    list)
        python -c "
import json
from pathlib import Path
db = Path('docs/episodes.json')
if not db.exists():
    print('暂无播客'); exit()
eps = json.loads(db.read_text())
for i, ep in enumerate(eps, 1):
    print(f'{i}. [{ep[\"pub_date\"][:10]}] {ep[\"title\"]}')
    print(f'   文件: {ep[\"filename\"]}')
"
        ;;
    delete)
        [ -z "$2" ] && echo "请提供要删除的序号 (先用 ./manage.sh list 查看)" && exit 1
        python -c "
import json, sys
from pathlib import Path
idx = int(sys.argv[1]) - 1
db = Path('docs/episodes.json')
eps = json.loads(db.read_text())
if idx < 0 or idx >= len(eps):
    print(f'序号无效，共 {len(eps)} 期'); sys.exit(1)
removed = eps.pop(idx)
db.write_text(json.dumps(eps, ensure_ascii=False, indent=2))
print(f'已删除: {removed[\"title\"]}')

# Delete from OSS
sys.path.insert(0, '.')
import yaml
cfg = yaml.safe_load(open('config.yaml'))
oss_cfg = cfg.get('oss', {})
if oss_cfg:
    from storage.oss_uploader import OSSUploader
    uploader = OSSUploader(oss_cfg['access_key_id'], oss_cfg['access_key_secret'], oss_cfg['endpoint'], oss_cfg['bucket'], oss_cfg['base_url'])
    uploader.delete(f'episodes/{removed[\"filename\"]}')
    print('OSS 文件已删除')

# Regenerate feed
from feed.rss_generator import RSSGenerator
feed_cfg = cfg.get('feed', {})
rss = RSSGenerator(feed_cfg.get('title',''), feed_cfg.get('description',''), feed_cfg.get('language',''), feed_cfg.get('base_url',''), './docs', audio_base_url=oss_cfg.get('base_url',''))
rss._generate_feed(eps)
print('Feed 已更新')
" "$2"
        publish
        ;;
    *)
        usage
        ;;
esac
