# 网盘下载索引（Hugo + 阿里云 ESA Pages）

用 [Hugo](https://gohugo.io/) 生成的静态下载索引站，托管在阿里云 ESA Pages。
数据源来自 `qsave share ls --json`（夸克网盘账号里的 **215 条有效分享**），每条分享一个独立页面：简介、真实网盘链接、截图位。

- 仓库：https://github.com/CyL-Cly/hugo-download-site （public，`main`）
- 构建：**本机** `hugo.exe v0.169.0` → 提交 `public/` → ESA 只做静态托管（无 Node、无云端构建）

## 页面结构

**首页** `index.html`：夸克网盘总入口 + 215 个文件夹卡片（搜索、分类筛选）。

**每个文件夹页面** `/folders/<slug>/`：

- 标题、自动简介、分类 / 体积 / 文件数 / 分享日期
- 「打开网盘文件夹 ↗」按钮 → 指向该条分享的真实夸克链接
- 正文说明
- **截图区**：默认渲染一个占位块（`SCREENSHOT / 1`），想放图时填 `src` 即可，见下

### 怎么加截图

编辑对应 `content/folders/<slug>/index.md` 的 front matter：

```yaml
screenshots:
  - caption: "文件夹根目录"
    src: "screenshots/xxx.png"     # 图片放到 static/screenshots/ 下
  - caption: "第二张"
    src: "screenshots/yyy.png"
```

想只留位置不放图：把 `src` 保持 `""`（占位块会显示提示文字）。
图片用相对路径，ESA 测试域名 / 自定义域名都能正常加载。

### 怎么改内容 / 链接 / 分类

| 想改什么 | 编辑哪里 |
| --- | --- |
| 某条分享的简介、标题、网盘链接、截图 | `content/folders/<slug>/index.md` 的 front matter |
| 首页标题、站点名、网盘总入口 | `hugo.toml`（`title` / `params.panUrl` / `params.panName`） |
| 分类关键词规则 | `tools/category-rules.json` |
| 列表布局、卡片字段 | `layouts/index.html` |
| 文件夹页布局 | `layouts/folders/single.html` |
| 配色 / 字体 / 间距 | `static/css/main.css`（`:root` 设计令牌） |
| 搜索筛选逻辑 | `static/js/main.js` |

## 重新从网盘拉取分享（新增/失效时）

```bat
qsave share ls --cloud quark --cookie secrets\quark_live.txt --json > .tmp-shares.json
python tools/gen_folders.py --input .tmp-shares.json
build.bat
git add -A && git commit -m "sync shares" && git push
```

`gen_folders.py` 按 `firstId` 去重（同一文件多次分享只保留最新一条），只保留有效分享，按分享时间倒序。
slug 由 `标题 + shareId 前 8 位` 生成，稳定不变；**重跑会保留你已手改的 `summary`**，但会重置截图为占位（如需批量保留请改脚本）。

## 每次改完的发布流程

```bat
build.bat
git add -A
git commit -m "update site"
git push
```

`build.bat` 调用 `.tools\hugo\hugo.exe` 重新生成 `public/`；push 后 ESA 自动更新，不需要云端构建。
`.tools/` 与 `.tmp-shares.json` 已在 `.gitignore`，二进制和凭据不进仓库。

## ESA Pages 接入（控制台做一次）

**边缘计算和 AI → 函数和 Pages → 创建 → 导入 GitHub 仓库** → 授权 → 选 `hugo-download-site` → 生产分支 `main`。
仓库里已有 `esa.jsonc`（`installCommand`/`buildCommand` 为空、`assets.directory: ./public`、`404Page`），控制台构建信息留空即可。
正式访问绑定自定义域名（国内需已备案），ESA 自动签发 HTTPS。

## 目录结构

```
hugo.toml                 站点配置（含网盘总入口）
content/_index.md         首页
content/folders/<slug>/   215 个文件夹页（每条分享一个）
layouts/index.html        首页模板
layouts/folders/single.html 文件夹页模板（含截图位）
layouts/partials/         head / foot
static/css/main.css       样式
static/js/main.js         搜索筛选
static/screenshots/       放截图（自行放入）
tools/gen_folders.py      从 qsave JSON 生成页面
tools/category-rules.json 分类关键词
esa.jsonc                 ESA Pages 配置
build.bat                 本地构建脚本
public/                   构建产物（提交进仓库，ESA 托管此目录）
```
