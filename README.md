# CCF-A Paper Search skill

> “明天就要开组会了，文献都还没开始找，用AI帮我找找吧” “靠，怎么这些AI全在编文献骗我，为啥数据库的AI全要充VIP，为啥这个codex只会用web搜一两个文章来糊弄我” 

## 这玩意儿是干嘛的

想要让你的agent搜索文献能力上一个台阶？

想要把你的研究领域的全部文献一次性全拉下来？

想让AI帮你自己梳理细分领域？发展历史？研究前景？

交给CCF-A Paper Search skill

## 它到底能干什么

- 目前可以按主题搜索 **2023-2026 年 CCF-A 级别会议**的论文
- 提供一套完整的检索策略报告，供你补充修正
- 搜完之后生成三件套：`query_plan.md`（搜索策略）、`papers.md`（论文列表）、`report.md`（综述报告）
- 可选下载开放获取的 PDF

## 架构设计

整个项目结构大概长这样：

```
scripts/
  run_search.py          # 主搜索入口，并发拉三个数据源，写得挺正经
  fetch_dblp.py          # 从 DBLP 搜论文 + 爬 proceedings 目录页（对，手写 HTML parser）
  fetch_openalex.py      # 从 OpenAlex 搜论文
  fetch_crossref.py      # Crossref 元数据补全，预算只给 5 条，抠门
  dedupe.py              # 去重，DOI > 标题 > 标题+年份+作者
  download_pdfs.py       # 下载 PDF，会检查文件头是不是真 PDF
  download_selected_pdfs.py  # 只下载最终保留的论文的 PDF
  write_outputs.py       # 把搜索结果打包成 writer_context.json
  common.py              # 工具函数大杂烩，HTTP、日志、slug、路径什么都有
  doctor.py              # 健康检查，看看网络通不通、快照文件在不在
  bootstrap_snapshots.py # 大概是用来初始化快照数据的

data/
  ccf_snapshots/         # 2023-2026 年 CCF-A 会议列表快照（JSON）
  query_profiles/        # 搜索模式配置：broad-recall vs high-precision（各两行 YAML，没错就两行）

references/              # 七份参考文档，堪称项目的"宪法"
  workflow.md            # 29 步工作流程，比 IKEA 家具说明书还细
  query-expansion.md     # 搜索词扩展原则，核心思想：宁可多搜不可漏搜
  dedupe-policy.md       # 去重策略，三行搞定
  pdf-policy.md          # PDF 下载红线：不准翻墙、不准用机构账号、不准爬付费页面
  output-spec.md         # 输出文件规范
  source-priority.md     # 数据源优先级：DBLP > OpenAlex > Crossref
  trigger-phrases.md     # 触发短语列表
  writer-subagent.md     # writer 子代理的行为准则，写得像劳动合同

agents/
  openai.yaml            # OpenAI agent 接口配置（对，虽然叫 openai 但其实是给 Codex 用的）
```

## 工作流程

1. 你说"帮我找 XXX 论文"
2. AI 先去网上搜一圈，找找这个领域最近有什么热词
3. 结合热词生成一堆英文搜索词，给你看中文预览
4. 你说"行"
5. 并发去 DBLP（关键词搜索 + 会议目录页全量枚举）和 OpenAlex 拉数据
6. 去重合并，缺 DOI 的去 Crossref 补（最多补 5 条，多了不给）
7. 把原始结果存成 `writer_context.json`
8. 派一个 writer 子代理把 JSON 写成人话（三个 markdown 文件）
9. 你要是勾选了下载 PDF，这时候才开始下，而且只下最终保留的那些

10. 想下 PDF 的话跟 AI 说一声，它会通过元数据直链或 ACL Anthology 拼接 URL 下载开放获取的论文到 `pdf/` 目录，付费的不碰

## 怎么用

把整个目录丢到 `~/.codex/skills/` 下面就行了。然后跟 Codex 说"帮我找 XXX 的 CCF-A 论文"，剩下的它自己会搞定——包括拼参数、调脚本、走那套三审流程。你要做的就是看预览、说"行"、等结果。


