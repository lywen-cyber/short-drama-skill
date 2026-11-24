# 短剧写作 Skill

给其他 AI 快速上手的写作 skill：先读甲方要求，再按要求写短剧、写到能交，并在交稿前按同一套标准自检。

本包是 [lywen-cyber](https://github.com/lywen-cyber) 的写作执行包，不是其他短剧 skill 的派生。包内是方法、阶段细则和教学用文件骨架，**不含客户或内部语料**。对照用的原文在单独的私有语料库，仅授权协作者可看；本包可独立使用。

口径优先级见 `SKILL.md`。

## 安装

将本仓库克隆到 AI 助手的技能目录：

```bash
# macOS / Linux（全局安装，示例路径以 Claude Code 为例）
git clone https://github.com/lywen-cyber/short-drama-skill.git ~/.claude/skills/short-drama-skill

# 项目级安装
cd your-project
git clone https://github.com/lywen-cyber/short-drama-skill.git .claude/skills/short-drama-skill
```

其他支持 Skills 目录的助手，把仓库放到该助手约定的 skills 路径即可。安装后先读 `SKILL.md`；能按 `/brief` 锁定甲方要求，即说明已接上。

## 快速上手

每次新项目先锁定甲方要求，再按路径推进。不要未锁定 brief 就开写。

```
/brief            → 锁定集数、字数、是否对标、国内或海外、格式和交付物
/benchmark        → 仅路径 A（甲方要求对标）时拆对标
/plan             → 提案、一句话故事、交付范围内大纲
/characters       → 人物小传与关系
/outline          → 分集目录
/episode          → 按集写正文（可写一集、一个区间、或下一集）
/review           → 按当次 brief 和审查清单自检
/revise           → 按审查或甲方意见修改，并回查相邻集
/export           → 按 brief 打包终本
```

执行时按阶段加载 `references/` 里对应的文件，不要一次读完全部。看文件形状和改前改后对照，打开 `examples/`（教学用，不是当次订单；项目正文是占位）。

## 两条路径

- **路径 A（需要对标）**：拆对标 → 提案 → 人物 → 分集 → 正文 → 自检 → 修改 → 交稿。只依据真实看过或核过的材料拆解，缺口标明，不用我方原创冒充原剧。
- **路径 B（不写对标剧）**：跳过拆对标和对标框架，按甲方题材或梗概直接立项写审。正文和文头不编造对标剧名或原剧情节。

两条路径在「人物」之后合并。一步确认后再进入下一步，不一次生成整部不可控稿。

没有书面要求时的默认和优先级见 `SKILL.md`。

## 目录

```
SKILL.md                   # 现行执行入口
references/                # 按阶段加载的细则（13 份）
examples/                  # 教学用骨架和改前改后对照；分集约定为 episodes/第NN集.md
scripts/count.py           # 按当次字数规则统计源稿
scripts/export_docx.py     # 按宁式把源稿导出为 Word
scripts/test_count.py      # 字数口径与目录扫描回归测试
requirements.txt           # export_docx.py 依赖（python-docx）
```

## 参考资料：按阶段加载

| 文件 | 加载时机 |
|------|----------|
| references/甲方要求模板.md | /brief |
| references/对标拆剧.md | /benchmark（仅路径 A） |
| references/提案与大纲.md | /plan |
| references/人物小传.md | /characters |
| references/开篇.md | /plan，以及写第 1 集时的 /episode |
| references/钩子与卡点.md | /plan、/outline、/episode |
| references/节奏.md | /plan、/outline、/episode、/review |
| references/爽点.md | /plan、/episode、/review |
| references/反派.md | /characters、/plan |
| references/正文格式.md | /episode、/export |
| references/海外本土化.md | 仅海外稿：/brief 之后、/episode、/review |
| references/审查清单.md | /review、/revise |
| references/交稿打包.md | /export |

## 字数统计

按当次 brief 的上下限统计，不要暗自更换口径。交稿前的字数以 Markdown 源稿为准，用本脚本统计，不要改去读 Word。

默认口径是汉字个数 + 英文单词数，不计空白。另外：

- 跳过集标题行（「第1集」「第 1 集」「第一集」「第1集 背叛」等）、场头（含全角空格和「1-1-1 回忆」这类闪回场号），以及「人物：」「人物:」行。
- 整行只是【音效】【闪回】这类幕头或音效标记的，不计正文字；嵌在动作段落中的，只计对外可见描述。
- `$5,000,000`、`1,200`、`30%` 这类金额或带千分位、百分号的数字按 1 个英文单词计，避免商战戏金额被记成 0。

分集统一放在 `episodes/第NN集.md`（两位编号）。按目录统计时默认扫这个路径，同时兼容旧的 `ep*.txt` 和根目录 `第N集.md`。

```bash
python scripts/count.py examples/示例项目 --min 800 --max 1000
python scripts/count.py examples/示例项目/episodes/第01集.md --min 800 --max 1000
```

甲方另有口径时，改统计方式或改脚本参数，以书面要求为准。

## 导出 Word

交 Word 时用 `scripts/export_docx.py`，不要临场自撰排版。脚本按宁式写出：△ 与动作同一行，对白另起一行。导出的 `.docx` 不要提交进仓库。

```bash
pip install -r requirements.txt
python scripts/export_docx.py examples/示例项目 --title 示例项目 -o /tmp/示例项目.docx
```

文件名跟 brief；未指定则用中文剧名。

## 许可证

许可证尚未确定，本仓库暂不附 LICENSE。
