# Hugo 下载站（部署到阿里云 ESA Pages）

用 Hugo 生成的静态下载索引站，GitHub 仓库 `CyL-Cly/hugo-download-site`（public），通过阿里云 ESA Pages 导入仓库托管。

> `public/` 只是 Hugo 的**默认输出目录名**（相当于 Vite 的 `dist/`），与仓库公开/私有无关。它就是 ESA 要托管的那堆 HTML/CSS/JS。想改名可在 `hugo.toml` 里设 `publishDir`。

## 构建方式（无 Node）

ESA 构建机只预装 Node/npm，不预装 Hugo；且从 GitHub 下载 Hugo 二进制在国内易被重置。因此采用**本地构建 + 提交产物**：

- 本机用 `.tools\hugo\hugo.exe`（v0.169.0）构建
- `esa.jsonc` 把 `installCommand`、`buildCommand` 都设为 `""`，跳过云端构建
- `assets.directory` 指向 `./public`，ESA 只做静态托管
- 站点无 Node 依赖，Hugo 只是构建期工具，产物是纯静态文件

## 怎么编辑页面

**只需要编辑一个文件：`data/downloads.toml`**（站点内容全部来自这里）。

### 增 / 改 / 删条目

每个 `[[items]]` 块就是页面上一行卡片：

```toml
[[items]]
name        = "软件名"                 # 显示的标题
category    = "tool"                   # 必须匹配下面 categories 里的 id
description = "一句话说明"             # 副标题
version     = "v1.2.3"                # 版本号
date        = "2026-11-05"            # 发布日期
platform    = "Windows / Linux"       # 适用平台
size        = "约 30 MB"              # 体积（可留空 ""）
url         = "https://.../releases"  # 下载链接；留空 "" 则显示「未发布」按钮
checksum    = ""                      # 校验值（可留空）
tags        = ["cli", "go"]           # 标签，可被搜索
```

- **新增**：复制一整个 `[[items]]` 块，改字段即可。
- **修改**：直接改对应字段值。
- **删除**：删掉整个 `[[items]]` 块。
- **分类**：在文件顶部的 `[[categories]]` 里增删，`id` 与条目的 `category` 对应筛选按钮。

> 大文件不要放进仓库（GitHub 单文件硬限 100MB，Pages 也不适合分发大二进制）。`url` 指向对象存储 / GitHub Releases / 网盘分享即可，本页只做「索引」。

### 改站点标题 / 文案 / 样式

| 想改什么 | 编辑哪个文件 |
| --- | --- |
| 站点标题、语言、描述 | `hugo.toml` |
| 首页大标题、引导语、页脚 | `layouts/index.html` |
| 颜色、字体、间距、响应式 | `static/css/main.css`（全部是 `:root` 设计令牌） |
| 搜索 / 筛选交互 | `static/js/main.js` |
| 404 页 | `layouts/404.html` |
| 构建命令、产物目录 | `esa.jsonc`（优先级高于 ESA 控制台设置） |

## 改完后的发布流程（每次都要做）

```bat
build.bat
git add -A
git commit -m "update downloads"
git push
```

`build.bat` 调用 `.tools\hugo\hugo.exe` 重新生成 `public/`；提交后 ESA 检测到 `main` 分支 push 会自动更新站点（不需要云端构建）。

> `.tools/` 已在 `.gitignore` 中，二进制不进仓库。换机器时把 `hugo_0.169.0_windows-amd64.zip` 解压到 `.tools\hugo\` 即可。

## ESA Pages 首次接入（控制台做一次）

- 开通 ESA「函数和 Pages」服务 → **边缘计算和 AI → 函数和 Pages → 创建 → 导入 GitHub 仓库**
- 授权 GitHub 账号；仓库是 public，会直接出现在列表里
- 生产分支 `main`；仓库里已有 `esa.jsonc`，构建信息可全部留空（文件优先，会跳过 install/build）
- 等部署完成，拿到 `.er.aliyun-esa.net` 测试域名（需 token，60 分钟有效）
- 正式访问请绑定自定义域名（国内访问需已备案域名），ESA 自动签发 HTTPS

## 目录结构

```
hugo.toml            Hugo 配置
data/downloads.toml  ← 页面内容（唯一需要日常编辑的文件）
layouts/index.html   首页模板
layouts/404.html     404 页（配合 esa.jsonc 的 404Page 策略）
static/css/main.css  样式（设计令牌）
static/js/main.js    搜索与筛选
esa.jsonc            ESA Pages 配置（跳过云端构建，托管 public/）
build.bat            本地构建脚本
public/              构建产物（提交进仓库，ESA 托管此目录）
```
