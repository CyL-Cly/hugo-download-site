# 资源分享站（Hugo + 阿里云 ESA Pages）

用 [Hugo](https://gohugo.io/) 生成的静态资源分享站，托管在阿里云 ESA Pages。
数据源来自 `qsave share ls --json`（夸克网盘账号里的 **215 条有效分享**），每条分享一个独立页面：简介、真实网盘链接、截图位。

- 仓库：https://github.com/CyL-Cly/hugo-download-site （public，`main`）
- 构建：**本机** `hugo.exe v0.169.0` → 提交 `public/` → ESA 只做静态托管（无 Node、无云端构建）

## 页面结构

**首页** `/`：只有资源分享站介绍（用途、免责声明）与一个「浏览资源目录」入口，不放网盘入口，也不列文件夹。

**资源目录** `/index/`：215 个文件夹列表（搜索、分类筛选）。列表模板在 `layouts/dirlist/list.html`。

**每个文件夹页面** `/folders/<slug>/`：

- 标题、简介、分类 / 体积 / 文件数 / 分享日期
- 「打开网盘文件夹 ↗」按钮 → 指向该条分享的真实夸克链接
- 正文介绍（来自 `tools/intros.json`）
- **截图**：只有真正配了图片才会出现「截图」区；没有图片时整块不渲染，不会留空占位

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

`build.bat` 调用 `.tools\hugo\hugo.exe` 重新生成 `public/`；push 后 ESA 自动更新，不需要云端构建。
`.tools/` 与 `.tmp-shares.json` 已在 `.gitignore`，二进制和凭据不进仓库。

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
layouts/folders/single.html 文件夹页模板（截图区按需渲染）
layouts/partials/         head / foot
static/css/main.css       样式
static/js/main.js         搜索筛选
static/screenshots/       放截图（自行放入）
tools/intros.json         215 条资源的简介与正文（文案源）
tools/apply_intros.py     把 intros.json 写回页面
tools/merge_intros.py     合并分批文案并校验
tools/build_intro_batches.py  切分批次的输入文件
tools/gen_folders.py      从 qsave JSON 生成页面
tools/category-rules.json 分类关键词
esa.jsonc                 ESA Pages 配置
build.bat                 本地构建脚本
public/                   构建产物（提交进仓库，ESA 托管此目录）
```
