# Anything to Podcast

将 arXiv 论文、技术报告 PDF、Reddit 帖子、X/Twitter 推文转换为中文播客，通过 GitHub Pages 发布 RSS feed，可在 Apple Podcasts 等客户端订阅。

## 安装

```bash
pip install requests pymupdf arxiv edge-tts openai pyyaml feedgen oss2
brew install ffmpeg
```

## 配置

复制配置模板并填入你的 LLM API 信息：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，修改 `llm` 部分的 `base_url`、`api_key`、`model`。

Twitter 需要额外提供 `cookies.txt` 文件（浏览器导出）。

### Notion 配置（可选）

在 [Notion Integrations](https://www.notion.so/my-integrations) 创建 internal integration，获取 token。然后在 `config.yaml` 中添加：

```yaml
notion:
  token: "ntn_xxx"
  parent_page_id: "your-page-id"
```

并在目标 Notion 页面的 Connections 中添加该 integration。

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

### 测试模式

只生成文稿（短稿 + 长稿）并保存到 Notion，不生成音频、不上传、不更新 RSS：

```bash
./manage.sh test <url或本地pdf路径>
```

### 批量 Prompt 测试

对多篇论文批量测试不同的 prompt 效果，结果保存到 Notion 方便对比：

```bash
./manage.sh batch <urls.txt> [prompt_variants目录]
```

**准备工作：**

1. 创建 URL 列表文件（每行一个，`#` 开头为注释）：

```
# batch_urls.txt
https://arxiv.org/pdf/2401.08740
https://arxiv.org/pdf/2212.09748
```

2. 在 `prompt_variants/` 目录下放置 prompt 文件（每个 `.md` 文件是一组 prompt）：

```
prompt_variants/
├── v1_学术严谨.md
├── v2_结构化深度解析.md
└── v3_xxx.md
```

每个 `.md` 文件是完整的 prompt 模板，用 `{content}` 作为论文内容占位符。系统会自动追加短稿/长稿的字数要求。

**Notion 输出**：每篇论文生成一个 Notion 页面，内含所有 prompt 变体的短稿和长稿，方便横向对比。

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

# 批量测试 prompt
./manage.sh batch batch_urls.txt prompt_variants/
```

## 订阅

iPhone 上打开 Apple Podcasts → 资料库 → 右上角 ··· → 通过 URL 关注节目：

```
https://crishhh1998.github.io/anything-to-podcast/feed.xml
```

## 架构

```
URL → 内容抓取 → LLM 生成中文播客脚本（短稿+长稿） → Edge TTS 语音合成 → OSS 上传 → Notion 保存 → RSS Feed → GitHub Pages
```

- 论文/技术报告：贴近原文，保持学术准确性
- Reddit/Twitter：适当拓展背景知识和分析
