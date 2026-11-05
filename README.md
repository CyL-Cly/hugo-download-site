# 资源分享站（Hugo + 阿里云 ESA Pages）

用 [Hugo](https://gohugo.io/) 生成的静态资源分享站，托管在阿里云 ESA Pages。
数据源来自 `qsave share ls --json`（夸克网盘账号里的 **215 条有效分享**），每条分享一个独立页面：简介、真实网盘链接、截图位。

- 仓库：https://github.com/CyL-Cly/hugo-download-site （public，`main`）
- 构建：**本机** `hugo.exe v0.169.0` → 提交 `public/` → ESA 只做静态托管（无 Node、无云端构建）

## 页面结构

**首页** `/`：只有资源分享站介绍（用途、免责声明）与一个「浏览资源目录」入口，不放网盘入口，也不列文件夹。

**资源目录** `/index/`：215 个文件夹列表（搜索、分类筛选）。列表模板在 `layouts/dirlist/list.html`。

**全站地图** `/sitemap/`：列出全站页面（含每个资源页的 `.md` 镜像链接）；另有 `/sitemap.md`（纯 Markdown 超链接）、`/sitemap.xml` 与 `/sitemap-md.xml`。

**机器可读索引** `/llms.txt`、`/llms-full.txt`：站点级 Markdown 链接索引与全文镜像；首页/目录/每个资源页都提供同名 `.md` 镜像（`rel=alternate` 指向）。

**每个文件夹页面** `/folders/<slug>/`：

- 标题、简介、分类 / 体积 / 文件数 / 分享日期
- 「打开网盘文件夹 ↗」按钮 → 指向该条分享的真实夸克链接
- **手机版软件例外**：安卓 App / APK 这类资源页面不输出任何网盘链接，按钮变成「下载（扫码获取）」，点击弹二维码
- 正文介绍（来自 `tools/intros.json`）
- **截图**：只有真正配了图片才会出现「截图」区；没有图片时整块不渲染，不会留空占位

### 手机版软件 / 二维码

哪些资源算「手机版软件」写在 **`data/mobile_apps.json`** 的 `ids` 里（按 `share_id`）：

```json
{ "ids": ["<share_id>", "<share_id>"] }
```

这些页面在构建时不会把 `pan_url` 写进 HTML，只留一个二维码按钮。二维码由 `tools/gen_qr.py`
在构建前根据 `pan_url` 生成到 `static/qr/<share_id>.svg`，所以**增删列表后必须重新构建**，链接才会真正消失。
未列入的资源（Windows 软件、固件、游戏等）照常显示网盘链接，手机浏览器访问也不改变行为。

### 文字介绍从哪来

215 条资源的简介（列表页）与正文（详情页）集中在 **`tools/intros.json`**，按 `share_id` 归档：

```json
{
  "<share_id>": {
    "slug": "blender-5-2-3-3a482a9c",
    "title": "Blender 5.2.3",
    "category": "软件工具",
    "summary": "列表页的一句话简介",
    "intro": "详情页正文，2~3 句。"
  }
}
```

改文案就改这个文件，然后 `python tools/apply_intros.py && build.bat`。
`gen_folders.py` 重新生成页面时也会读它，不会把文案冲掉。

### 怎么加截图

想给某个资源放图：把图片放进 `static/screenshots/`，再在对应 `content/folders/<slug>/index.md` 的 front matter 加：

```yaml
screenshots:
  - caption: "文件夹根目录"
    src: "screenshots/xxx.png"
  - caption: "第二张"
    src: "screenshots/yyy.png"
```

`src` 为空的条目会被忽略；一条有效图片都没有时，页面上不会出现截图区。
图片用相对路径，ESA 测试域名 / 自定义域名都能正常加载。

### 怎么改内容 / 链接 / 分类

| 想改什么 | 编辑哪里 |
| --- | --- |
| 某条资源的简介与正文 | `tools/intros.json`（改完跑 `python tools/apply_intros.py`） |
| 某条分享的标题、网盘链接、截图 | `content/folders/<slug>/index.md` 的 front matter |
| 首页介绍文案 | `layouts/index.html` |
| 站点名、站点描述 | `hugo.toml`（`title` / `params.description`） |
| 分类关键词规则 | `tools/category-rules.json` |
| 目录列表布局、卡片字段 | `layouts/dirlist/list.html` |
| 全站地图、GEO 产物 | `content/sitemap/_index.md` + `layouts/sitemap/list.html` + `tools/gen_geo.py` |
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
slug 由 `标题 + shareId 前 8 位` 生成，稳定不变；文案取自 `tools/intros.json`，**重跑会保留你手改过的 `summary` 与已配好的截图**。

新分享还没有文案时，`gen_folders.py` 会退回一句通用描述；把它补进 `tools/intros.json` 再跑一次 `apply_intros.py` 即可。

### 文案工具链

```bat
python tools\build_intro_batches.py --size 54   # 把缺文案的页面切成批次，输出到 tools/intros/
python tools\merge_intros.py                    # 合并分批写好的文案，校验覆盖与重复
python tools\apply_intros.py                    # 写回 215 个页面
```

## 每次改完的发布流程

```bat
build.bat
git add -A
git commit -m "update site"
git push
```

`build.bat` 四步：

1. `tools/gen_qr.py` — 给手机版软件生成二维码到 `static/qr/`
2. `.tools\hugo\hugo.exe` — 重新生成 `public/`
3. `tools/gen_geo.py` — 生成 `llms.txt` / `sitemap.md` / 全站 `.md` 镜像（见下节）
4. `tools/indexnow.py` — 读取 `public/sitemap.xml` 与 `public/sitemap-md.xml` 的绝对地址，提交给 Bing 的 IndexNow

`.tools/` 与 `.tmp-shares.json` 已在 `.gitignore`，二进制和凭据不进仓库。

## 搜索引擎收录（IndexNow / GEO）

站点域名写在 `hugo.toml` 的 `baseURL`，IndexNow 的 host / key 写在 `tools/indexnow.json`。
验证文件是 `static/<key>.txt`，构建后即出现在站点根目录。

面向搜索引擎与大模型（GEO）的索引产物，`build.bat` 第 3 步由 `tools/gen_geo.py` 在 Hugo 构建后生成（Hugo 用了 `--cleanDestinationDir`，必须先构建再生成）：

| 文件 | 内容 |
| --- | --- |
| `llms.txt` | llmstxt.org 风格的站点索引，全部为 Markdown 超链接（首页、目录、全站地图、215 条资源及各自镜像） |
| `llms-full.txt` | 全部资源页正文的纯文本/链接合集 |
| `sitemap.md` | 全站页面清单，纯 Markdown 超链接 |
| `sitemap/` | 人可读的全站地图 HTML，含每个资源页的 `.md` 镜像链接 |
| `index.md`、`index/index.md` | 首页与资源目录的 Markdown 镜像 |
| `folders/<slug>/index.md` | 215 个资源页各自的 Markdown 镜像（front matter + 正文 + 规范链接 + 同类资源） |
| `sitemap-md.xml` | 所有 Markdown 镜像 URL 的 XML sitemap |

每个 HTML 页 `<head>` 都带 `rel=canonical`、`rel=alternate type="text/markdown"`（指向本页镜像）与 `llms.txt`；页脚有全站地图入口。`robots.txt` 里同时列出两份 sitemap 与 GEO 发现提示。

**隐私一致性**：`data/mobile_apps.json` 里的手机版软件在 HTML 页只给二维码；`gen_geo.py` 同样不会把 `pan_url` 写进任何 Markdown 镜像或 `llms-full.txt`。

IndexNow 读取 `sitemap.xml` + `sitemap-md.xml`，把 HTML 页与 Markdown 镜像一起去重后提交给 Bing。验证文件要求域名下可访问，所以**第一次部署（或换域名）后**提交会返回
`403 SiteVerificationNotCompleted`。等 ESA 部署完成再补交一次即可：

```bat
python tools\indexnow.py
```

日常改了内容，`build.bat` 会自动提交；提交失败只打印 WARN，不会中断构建。
`sitemap.xml` 与 `robots.txt` 都由 Hugo 生成，`sitemap-md.xml` 由 `gen_geo.py` 生成。


## ESA Pages 接入（控制台做一次）

**边缘计算和 AI → 函数和 Pages → 创建 → 导入 GitHub 仓库** → 授权 → 选 `hugo-download-site` → 生产分支 `main`。
仓库里已有 `esa.jsonc`（`installCommand`/`buildCommand` 为空、`assets.directory: ./public`、`404Page`），控制台构建信息留空即可。
正式访问绑定自定义域名（国内需已备案），ESA 自动签发 HTTPS。

## 目录结构

```
hugo.toml                 站点配置
content/_index.md         首页（介绍，仅 front matter）
content/index/_index.md   资源目录页（驱动 /index/）
content/folders/<slug>/   215 个文件夹页（每条分享一个）
layouts/index.html        首页模板（纯介绍）
layouts/dirlist/list.html 资源目录模板
layouts/sitemap/list.html 全站地图 HTML（含 .md 镜像链接）
layouts/folders/single.html 文件夹页模板（截图区按需渲染、手机版软件走二维码）
layouts/robots.txt        robots（含两份 sitemap 与 GEO 提示）
layouts/partials/         head / foot
data/mobile_apps.json     手机版软件名单（这些资源不显示链接）
static/css/main.css       样式
static/js/main.js         搜索筛选
static/js/folder.js       二维码弹窗
static/qr/                构建生成的二维码（gen_qr.py 产出）
static/<key>.txt          IndexNow 域名验证文件
static/screenshots/       放截图（自行放入）
tools/intros.json         215 条资源的简介与正文（文案源）
tools/apply_intros.py     把 intros.json 写回页面
tools/merge_intros.py     合并分批文案并校验
tools/build_intro_batches.py  切分批次的输入文件
tools/gen_qr.py           生成手机版软件的二维码
tools/indexnow.py         提交 URL 给 Bing IndexNow
tools/gen_geo.py          构建后生成 llms.txt / sitemap.md / 全站 Markdown 镜像 / sitemap-md.xml
tools/indexnow.json       IndexNow 的 host / key 配置
tools/gen_folders.py      从 qsave JSON 生成页面
tools/category-rules.json 分类关键词
esa.jsonc                 ESA Pages 配置
build.bat                 本地构建脚本
public/                   构建产物（提交进仓库，ESA 托管此目录）
```
