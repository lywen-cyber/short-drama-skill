# 短剧写作 Skill

给其他 AI 快速上手的写作 skill：先读甲方要求，再按要求写短剧、写到能交，并在交稿前按同一套标准自检。

本包是 [lywen-cyber](https://github.com/lywen-cyber) 的写作执行包，不是其他短剧 skill 的派生。包内是方法、阶段细则和教学用文件骨架，**不含客户或内部语料**。对照用的原文在单独的私有语料库，仅授权协作者可看；本包可独立使用。

交稿标准按当次甲方书面要求灵活锁定。示例项目里的 8 集、每集 800–1000 字只是该示例的填法，不要当成所有项目的硬规则。

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

执行时按阶段加载 `references/` 里对应的文件，不要一次读完全部。看项目文件长什么样，打开 `examples/`（教学用最小骨架，不是当次订单，正文是占位）。

## 两条路径

- **路径 A（需要对标）**：拆对标 → 提案 → 人物 → 分集 → 正文 → 自检 → 修改 → 交稿。只依据真实看过或核过的材料拆解，缺口标明，不用我方原创冒充原剧。
- **路径 B（不写对标剧）**：跳过拆对标和对标框架，按甲方题材或梗概直接立项写审。正文和文头不编造对标剧名或原剧情节。

两条路径在「人物」之后合并。一步确认后再进入下一步，不一次生成整部不可控稿。

没有书面要求时，才用默认：海外中文一卡 8 集、每集 800–1000 字、不写第 9 集、交 Word。默认可以改，不能当成所有项目的硬规则。

## 目录

```
SKILL.md                 # 现行执行入口
references/              # 按阶段加载的细则（13 份）
examples/                # 最小项目文件形状示例（教学用）
scripts/count.py         # 按当次字数规则统计
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

按当次 brief 的上下限统计，不要暗自更换口径。默认口径是汉字个数 + 英文单词数，不计空白：

```bash
python scripts/count.py 第1集.md --min 800 --max 1000
```

甲方另有口径时，改统计方式或改脚本参数，以书面要求为准。

## 许可证

许可证尚未确定，本仓库暂不附 LICENSE。
