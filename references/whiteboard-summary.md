# 第 6 步（可选）：生成可视化总结白板

发布逐字稿后，用户常想再要一张**提炼重点的可视化图**嵌进同一篇文档。这一步用
[`beautiful-feishu-whiteboard`](https://github.com/zarazhangrui/beautiful-feishu-whiteboard)
的思路手工排 SVG，再写成飞书**可编辑白板**。它不是 Mermaid 自动布局，而是自己组版。

## 什么时候做
用户说“画个图 / 提炼重点 / 做张总结图 / whiteboard / 思维导图”并希望嵌进逐字稿文档时。

## 流程

### 6.1 把访谈提炼成结构
从 `content.json` / turns 里抽出 4–8 个**主题簇**，每簇 3–5 条要点。别把逐字稿原句搬上去，要提炼成短句。

### 6.2 选配色风格
读 `beautiful-feishu-whiteboard/CATALOG.md`，按内容气质挑一个 `templates/<slug>/design.md`（只开选中的那一个）。
AI/研究类内容适合 **Riso Brut**（新粗野主义编辑风：暖奶油底、厚墨边、硬偏移阴影、方角、多色块碰撞）。

### 6.3 手写 SVG（Python 生成器最省事）
写一个 Python 脚本吐出 `diagram.svg`，逻辑坐标空间约 1600–1700 宽。严守媒介硬规则（见
`beautiful-feishu-whiteboard/RULES.md`）：原生形状（rect/circle/line/text）、单字体（永不设 font-family）、
无渐变/滤镜/opacity、硬偏移阴影＝同形状复制偏移置后、方角、箭头用 `marker-end` 而非手画三角。

### 6.4 ⚠️ 关键教训：文字必须落在浅色底上
**飞书白板导出/渲染时会把文字强制压成深色**（RULES.md 明写：图片导出文字颜色不可靠，常变黑）。
所以：
- **所有文字都放在浅色底（奶油/黄）上用深墨色**，保证对比度；
- 彩色（绿/粉/橙）**只用于边框、顶部色条、方块项目符号、数字徽章、分隔线**，绝不要把文字放到饱和色块上；
- 别信任本地 PNG 预览的文字颜色——它和线上不一致。真相以线上白板回查图或 `--output_as raw` 为准。

（这一条是踩坑沉淀：第一版把标题/卡片头文字设成奶油色放在绿/粉色条上，线上渲染全变深色压深底、几乎看不清，返工才发现。）

### 6.5 渲染 → 看 → 修（本地）
```bash
# 本环境的 lark-whiteboard 市场技能封装了 CLI：
WB=/data/plugins/market/lark-whiteboard/skills/lark-whiteboard/scripts
$WB/whiteboard-cli.sh -i diagram.svg -o diagram.png    # 渲染预览
grep -nE '<polygon|<polyline' diagram.svg              # 自检：不该有手画箭头
```
打开 PNG 肉眼检查溢出/重叠/裁切/贴边，就地小步改 SVG，别整份重写。

### 6.6 写进文档里的白板块
若文档还没有白板块，先追加一个空块拿 token：
```bash
lark-cli docs +update --api-version v2 --doc <doc_id> \
  --command block_insert_after --block-id <某块id> \
  --content '<whiteboard type="blank"></whiteboard>' --as user
# 返回 data.new_blocks[].block_token
```
再把 SVG 转 openapi JSON 写入该 token（先 `--dry-run`，无 “nodes will be deleted” 警告才正式写）：
```bash
$WB/whiteboard-cli.sh -i diagram.svg --to openapi --format json | \
  $WB/lark-cli.sh whiteboard +update --whiteboard-token <tok> \
    --source - --input_format raw --idempotent-token <10+位唯一串> --overwrite --as user
```

### 6.7 回查线上真图（不可省）
```bash
cd <目标目录> && $WB/lark-cli.sh whiteboard +query \
  --whiteboard-token <tok> --output_as image --output ./ --overwrite --as user
```
> `+query` 的 `--output` 只收**当前目录下的相对路径**，所以要先 `cd` 到目标目录。

打开这张**线上回查图**（不是本地 diagram.png）确认文字颜色/对比度真实无误，有问题回 6.4 改。

## 沉淀的坑
- 文字放彩色块上 → 线上变深色看不清。**全部文字上浅底。**
- 信任本地 PNG 的文字颜色 → 与线上不符。**以线上回查图为准。**
- 手画三角箭头 → 嵌成锯齿图片。**用 `marker-end`。**
- 用 opacity 调浅 → 被忽略。**改用更浅的实色 hex。**
- 覆盖写入前不 dry-run → 可能误删节点。**先 `--dry-run` 看警告。**
