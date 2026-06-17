# Auto-Reviewer Agent (Deep Learning Papers)

一个基于 Claude API 的深度学习论文自动审稿 agent，按照 `todo.txt` 中定义的 10 阶段流程对一篇 PDF 论文生成结构化的审稿意见。

## Pipeline

| Stage | 目标 |
|-------|------|
| 0 | 解析 PDF → 结构化论文表示（title, claims, contributions, ...） |
| 1 | 整体理解（一段摘要 + claim-evidence map） |
| 2 | 分章节分析（issues / missing info / ambiguous claims） |
| 3 | Claim 抽取与证据映射（按 novelty / correctness / empirical 等分类） |
| 4 | Novelty check（启用 Claude 内置 web_search 工具查找近似工作） |
| 5 | 显著性 / 影响多视角分析（5 个 persona） |
| 6 | Rigor check（internal correctness, claim support, experimental rigor） |
| 7 | Review planning（strengths/weaknesses/recommendation） |
| 8 | Draft review（author-facing） |
| 9 | Self-critique（找 hallucinations / 过强 claim / inconsistency） |
| 10 | Finalize（应用 critique，输出 final review + 改进 checklist） |

每个 stage 的 paper 全文都通过 **prompt caching** 复用，整段 paper 只在第一阶段写入缓存，之后 9 个阶段都是廉价的 cache read。

## 安装

```bash
cd /home/weiliu1/mypaper/2026/ai-scientist/githubcode
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY
```

## 使用

```bash
python reviewer_agent.py /path/to/paper.pdf
```

可选参数：

```bash
# 自定义输出目录
python reviewer_agent.py paper.pdf --out ./my_reviews

# 关闭 Stage 4 的 web 搜索（节省 tokens）
python reviewer_agent.py paper.pdf --no-web-search

# 调整 effort（low/medium/high/xhigh/max）
python reviewer_agent.py paper.pdf --effort medium
```

## 输出

在 `--out` 目录（默认 `./reviews`）下生成：

- `{paper}.review.json` — 所有 10 个 stage 的完整结构化输出 + token 使用
- `{paper}.review.md` — 给作者看的最终审稿意见（markdown）

## 配置

环境变量 / `.env`：

| 变量 | 默认 | 说明 |
|------|------|------|
| `ANTHROPIC_API_KEY` | （必填） | Anthropic API key |
| `REVIEWER_MODEL` | `claude-opus-4-7` | 主推理模型 |
| `REVIEWER_FAST_MODEL` | `claude-sonnet-4-6` | 预留给可能的轻量子任务 |

## 文件结构

```
config.py           - 配置加载（dotenv）
pdf_parser.py       - PDF → 纯文本（pypdf）
prompts.py          - 10 个 stage 的 prompt 模板
llm_client.py       - Anthropic SDK 封装（caching + adaptive thinking + web_search）
pipeline.py         - 串联 10 个 stage，传递 JSON 上下文
reviewer_agent.py   - CLI 入口（含 markdown 报告渲染）
```

## 已知限制（基础版）

- PDF 文本提取：使用 `pypdf`，对扫描版 / 复杂排版论文效果有限；后续可换成 `pymupdf` 或调用 Claude 的 PDF 输入能力（直接传 base64 PDF）。
- 图表 / 公式：目前只抽出短描述，不做视觉理解。要做的话可以改用 Claude 多模态接口直接传 PDF 页面图像。
- Novelty check 依赖 web_search 工具的检索质量；可以叠加 Semantic Scholar / arXiv 的专用 API 做更可靠的检索。
- 没有并行化；10 个 stage 严格串行（因为存在依赖关系）。
- 缺少持久化的中间结果——一旦中途失败需要从头重跑。

## 下一步建议

1. PDF 直接传给 Claude 处理（替代 pypdf 提取的纯文本），保留版面 / 图表理解能力。
2. Stage 4 接入 Semantic Scholar API 做更精准的论文检索。
3. 每个 stage 写中间 cache 文件，支持断点续跑。
4. 多论文 batch 模式 → 使用 Anthropic Batches API，价格减半。
