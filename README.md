# Anything to Podcast

将 arXiv 论文、技术报告 PDF、Reddit 帖子、X/Twitter 推文转换为中文播客，通过 GitHub Pages 发布 RSS feed，可在 Apple Podcasts 等客户端订阅。

## 安装

```bash
pip install requests pymupdf arxiv edge-tts openai pyyaml feedgen
brew install ffmpeg
```

## 配置

复制配置模板并填入你的 LLM API 信息：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，修改 `llm` 部分的 `base_url`、`api_key`、`model`。

Twitter 需要额外提供 `cookies.txt` 文件（浏览器导出）。

## 使用

所有操作通过 `manage.sh` 完成：

```bash
# 生成新一期并自动发布
./manage.sh add <url或本地pdf路径>

# 列出所有期
./manage.sh list

# 删除某一期（先用 list 查看序号）
./manage.sh delete <序号>
```

### 示例

```bash
# arXiv 论文
./manage.sh add https://arxiv.org/pdf/2404.02905

# 本地 PDF（技术报告）
./manage.sh add ./report.pdf

# Reddit 帖子
./manage.sh add https://www.reddit.com/r/MachineLearning/comments/xxx/

# X/Twitter（需要 cookies.txt）
./manage.sh add https://x.com/user/status/123456
```

## 订阅

iPhone 上打开 Apple Podcasts → 资料库 → 右上角 ··· → 通过 URL 关注节目：

```
https://crishhh1998.github.io/anything-to-podcast/feed.xml
```

## 架构

```
URL → 内容抓取 → LLM 生成中文播客脚本 → Edge TTS 语音合成 → MP3 + RSS Feed → GitHub Pages
```

- 论文/技术报告：贴近原文，保持学术准确性
- Reddit/Twitter：适当拓展背景知识和分析
