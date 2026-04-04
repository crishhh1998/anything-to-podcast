# Anything to Podcast

将 arXiv 论文、技术报告 PDF、Reddit 帖子、X/Twitter 推文转换为中文播客，通过 GitHub Pages 发布 RSS feed，可在 Apple Podcasts 等客户端订阅。

## 安装

```bash
pip install requests pymupdf arxiv edge-tts openai pyyaml feedgen oss2 mutagen
brew install ffmpeg
```

## 配置

复制配置模板并填入你的 LLM API 信息：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，修改 `llm` 部分的 `base_url`、`api_key`、`model`。

Twitter/X 使用 fxtwitter API 抓取推文内容，无需额外配置。

### Notion 配置（可选）

生成的播客稿件可以自动保存到 Notion。在 [Notion Integrations](https://www.notion.so/my-integrations) 创建 integration 获取 token，然后在 `config.yaml` 中添加：

```yaml
notion:
  token: "ntn_xxx"
  parent_page_id: "your-page-id"
```

并在目标 Notion 页面的 Connections 中添加该 integration。

## 使用

所有操作通过 `manage.sh` 完成：

```bash
# 生成新一期并自动发布（默认内置 prompt，10 分钟时长）
./manage.sh add <url>

# 指定 prompt 变体和时长
./manage.sh add -p 1 -d 15 <url>

# 查看可用的 prompt 变体
./manage.sh prompts

# 列出所有期
./manage.sh list

# 删除某一期（先用 list 查看序号）
./manage.sh delete <序号>
```

### 选项说明

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-p <编号>` | 指定 prompt 变体编号 | 内置 prompt |
| `-d <分钟>` | 目标播客时长 | 10 分钟 |

### Prompt 变体

在 `prompt_variants/` 目录下放置 `.md` 文件，每个文件是一个完整的 prompt 模板，用 `{content}` 作为论文内容占位符。运行 `./manage.sh prompts` 查看编号。

### 示例

```bash
# arXiv 论文（默认）
./manage.sh add https://arxiv.org/pdf/2404.02905

# 用第 2 个 prompt，目标 15 分钟
./manage.sh add -p 2 -d 15 https://arxiv.org/pdf/2404.02905

# 本地 PDF
./manage.sh add ./report.pdf

# Reddit 帖子
./manage.sh add https://www.reddit.com/r/MachineLearning/comments/xxx/

# X/Twitter
./manage.sh add https://x.com/user/status/123456
```

## 流程

```
URL → 内容抓取 → LLM 生成短稿+长稿 → Edge TTS 语音合成 → OSS 上传 → Notion 保存 → RSS Feed 更新 → GitHub Pages 发布
```

- 每次生成两种稿件：短稿（500-1000 字）和长稿（按指定分钟数）
- 长稿自动生成章节标记，音频内嵌章节跳转（ID3 + Podcasting 2.0）
- 音频基于长稿合成，上传至阿里云 OSS
- 稿件自动保存到 Notion（需配置）
- 论文/技术报告：贴近原文，保持学术准确性
- Reddit/Twitter：适当拓展背景知识和分析

## 项目结构

```
anything-to-podcast/
├── main.py                     # CLI 入口，编排整条 pipeline
├── manage.sh                   # 快捷命令封装（add/list/delete/prompts）
├── config.example.yaml         # 配置模板
├── config.yaml                 # 实际配置（gitignored，含 API 密钥）
├── pyproject.toml              # Python 项目元数据与依赖
│
├── fetchers/                   # 内容抓取模块
│   ├── base.py                 #   FetchResult 数据类 + BaseFetcher 基类
│   ├── arxiv_fetcher.py        #   arXiv 论文抓取（下载 PDF → 提取文本）
│   ├── pdf_fetcher.py          #   通用 PDF / 本地文件抓取
│   ├── reddit_fetcher.py       #   Reddit 帖子 + 评论抓取
│   └── twitter_fetcher.py      #   X/Twitter 推文抓取（via fxtwitter API）
│
├── processor/                  # LLM 脚本生成模块
│   ├── prompts.py              #   内置 prompt 模板（按来源类型 × 长短）
│   └── script_generator.py     #   调用 LLM 生成短稿 + 长稿
│
├── prompt_variants/            # 自定义 prompt 变体（每个 .md 文件一种风格）
│   ├── v1_学术严谨.md
│   ├── v2_结构化深度解析.md
│   └── v3_实验详解.md
│
├── tts/                        # 语音合成模块
│   └── edge_tts_engine.py      #   Edge TTS → 分章节合成 → ffmpeg 转码 → ID3 章节标记
│
├── storage/                    # 存储模块
│   └── oss_uploader.py         #   阿里云 OSS 上传/删除
│
├── notion/                     # Notion 集成模块
│   └── writer.py               #   将稿件写入 Notion 子页面
│
├── feed/                       # RSS Feed 模块
│   └── rss_generator.py        #   维护 episodes.json + 生成 feed.xml
│
├── docs/                       # GitHub Pages 发布目录
│   ├── feed.xml                #   RSS Feed 文件
│   ├── episodes.json           #   播客期数据库
│   └── cover.jpg               #   播客封面图
│
├── server.py                   # 本地开发用 HTTP 服务器
└── publish.sh                  # 手动发布脚本（git push）
```

## 订阅

iPhone 上打开 Apple Podcasts → 资料库 → 右上角 ··· → 通过 URL 关注节目：

```
https://crishhh1998.github.io/anything-to-podcast/feed.xml
```
