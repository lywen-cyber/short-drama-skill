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
/review           → 先跑 lint.py，再按当次 brief 和审查清单自检
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
scripts/script_text.py     # 源稿规范化、分集扫描和两种计字口径（共用）
scripts/count.py           # 按当次字数规则统计源稿（本包 / Word 近似）
scripts/lint.py            # /review 时先跑的轻量检查（说话人、场头、△ 排法）
scripts/export_docx.py     # 按宁式把源稿导出为 Word
scripts/test_count.py      # 字数口径、目录扫描与导出回归测试
scripts/test_lint.py       # lint 回归测试
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

按当次 brief 的上下限统计，不要暗自更换口径。交稿前用 `scripts/count.py` 同时看「本包口径」和「Word 近似口径」，以 brief 指定的为准；brief 没写则默认本包口径，并注意 Word 里看到的数字可能更大。脚本读 Markdown 源稿，不直接读 Word。源稿可用 Markdown 标题和加粗，脚本会剥掉行首 `#` 和包裹的 `**`，再计字。

本包口径：汉字个数 + 英文单词数，不计空白、中文标点和 △。另外：

- 跳过集标题行（「第1集」「第 1 集」「第一集」「第1集 背叛」「第1集：背叛」「第1集《背叛》」等）、场头（含全角空格、「1-1-1 回忆」，以及写成 `### 1-1 客厅 夜 内` 的标题行），以及「人物：」「人物:」行。
- 制作类标记（音效、特写、闪回等）：整行不计；嵌在段落里的整段去掉，包括【闪回—三年前】这类带说明的写法，不把说明算进正文。
- 内容类标记（字幕、弹幕、短信、新闻）：只计括号里的文字。整行内容类标记不再记 0。
- `$5,000,000`、`1,200`、`30%` 这类金额或带千分位、百分号的数字按 1 个英文单词计，避免商战戏金额被记成 0。

Word 近似口径把中文标点、△、场头、人物行、集标题也算进去。这是尽量接近 Word「字数」的近似，不是打开 Word 后的官方统计。判定上下限时可用 `--metric pack`（默认）或 `--metric word`。

分集统一放在 `episodes/第NN集.md`（两位编号）。按目录统计时，有 `episodes/` 就只读这个目录、不递归；没有它才回退到项目根目录的 `第N集.md` 或 `ep*.txt`，不会扫描子目录里的旧稿。同一集号出现两次、或传了 `--episodes N` 却缺集、多集，脚本会报错并以非零退出。字数不合格时也返回非零。

```bash
python scripts/count.py examples/示例项目 --min 800 --max 1000
python scripts/count.py examples/示例项目/episodes/第01集.md --min 800 --max 1000
python3 scripts/test_count.py
python3 scripts/test_lint.py
```

示例项目里的第 1 集是占位稿，字数低于 800，上面带 `--min` 的命令会打印「低于下限」并以非零退出，这是合格判定，不是脚本坏了。回归测试用：`python3 scripts/test_count.py`；lint 测试用：`python3 scripts/test_lint.py`。

## 分集检查

`/review` 时先跑 `scripts/lint.py`，再按审查清单做人工判断。脚本只查机器能稳定判断的问题：台词说话人是否出现在本场「人物：」里、是否出现在 `characters.md` 小传中（项目里有这个文件才查）、场头在剥掉 `#` 之后是否可识别、△ 是否单独成行或与对白挤在同一段。「冷笑」「一脸」这类神态词只统计报告，不当错误。发现问题以非零退出。

```bash
python3 scripts/lint.py <项目目录>
python3 scripts/lint.py examples/示例项目
```

示例项目里的第 1 集是格式占位，说话人写成「姓名」，跑上面第二条会报问题并以非零退出，这是预期结果，不是脚本坏了。真正项目应使用姓名，并与本场人物表、小传一致。

## 导出 Word

交 Word 时用 `scripts/export_docx.py`，不要临场自撰排版。脚本按宁式写出：△ 与动作同一行，对白另起一行。源稿里的标题和加粗会剥掉符号、保留文字，场头不会因为写成 `###` 而在 Word 里消失。可用 `--front` 按约定或指定文件把对标、大纲、人物小传依次放进文头。扫描范围与 `count.py` 相同，避免把子目录旧稿导进去。导出的 `.docx` 不要提交进仓库。

```bash
pip install -r requirements.txt
python scripts/export_docx.py examples/示例项目 --title 示例项目 -o /tmp/示例项目.docx
python scripts/export_docx.py examples/示例项目 --front --title 示例项目 -o /tmp/示例项目.docx
```

文件名跟 brief；未指定则用中文剧名。

## 许可证

许可证尚未确定，本仓库暂不附 LICENSE。
