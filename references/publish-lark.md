# 用 lark-doc 建档、追加、拉评论

飞书文档操作走 lark-doc skill 的 wrapper。以下是本流程验证过的调用方式。

## 入口
```bash
cd /data/plugins/market/lark-doc/skills/lark-doc/
LARK=/data/plugins/market/lark-doc/skills/lark-doc/scripts/lark-cli.sh
```
`--content` 支持 `@文件` 读取。**注意 wrapper 会 cd 进 skill 目录**，所以传文件时用相对路径
（先 `cd` 到你的工作目录，再用 `@./frags/xxx.xml`），或传绝对路径亦可视版本而定——优先相对路径。

## 建文档（写入 intro）
```bash
$LARK docs +create --title "文档标题" --content @./frags/intro.xml --api-version v2
```
返回 JSON 含 `document_id` 和 `url`。记下 `document_id`。

## 逐节追加正文
`docs +update` 用 **`--command`** 指定操作（不是 `--mode`），追加用 `append`：
```bash
DOC=<document_id>
for i in 0 1 2 3 4 5 6 7 8 9 10 11 12; do
  $LARK docs +update --api-version v2 --doc "$DOC" \
    --command append --content "@./frags/sec_${i}.xml"
done
```
成功返回含 `"ok": true`。

## 覆盖重建（推卻重做时用）
若整篇版式要重做，用 `--command overwrite` 写入新 intro，再重新 append 各节——
文档 URL 保持不变，用户收藏/链接不失效：
```bash
$LARK docs +update --api-version v2 --doc "$DOC" --command overwrite --content @./frags/intro.xml
```

## 拉取用户评论（迭代必用）
```bash
$LARK +get-comments 'https://bytedance.larkoffice.com/docx/<DOC>'
```
返回每条评论的 `quote`（被评论的原文片段）+ `reply_list`（评论内容）。据此逐条修改。

## 常见坑
- `--command is required`：忘了传 `--command`（v2 必需）。
- `unknown flag: --document-id`：用 `--doc`，不是 `--document-id`。
- token 过期（99991663 等）：按平台 token 刷新流程处理，不要跳过。
