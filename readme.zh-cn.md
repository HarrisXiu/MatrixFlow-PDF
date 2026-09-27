# 矩流 PDF · MatrixFlow PDF

**让文档有序流转。** 面向 Windows 的本地批量文档转换与 PDF 处理工具。

[English](README.md) · [简体中文](readme.zh-cn.md) · [繁體中文](readme.zh-tw.md) · [日本語](readme.ja.md)

<img src="assets/matrixflow-pdf.png" alt="矩流 PDF" width="96" />

「矩」呼应 Matrix 与代码雨，「流」代表文档的转换与处理流程。矩流 PDF 使用 React 前端和 Python 转换服务，采用深灰与薄荷绿配色，提供无边框窗口、集成窗口控制和始终可见的运行栏，适合日常批量办公。

## 队列排序与空白页处理

按住文件左侧的彩色类型标签拖动，在目标行的上半部或下半部松开，分别插到该文件前面或后面；绿色指示线显示插入位置。点击表头的 **名称** 或 **类型**，可切换升序和降序。名称采用不区分大小写的自然数字顺序（文件2排在文件10之前），类型按扩展名分组后按名称排序。排序会同步改变实际转换、合并顺序；筛选状态下也可使用，转换期间不可改序。

在 **高级 → 空白页处理** 中选择 **保留空白页**（默认）或 **智能识别并移除**。移除在范围选择之后、拆分合并与添加水印页码之前执行。程序用 PDFium 检查页面实际显示内容，可移除纯白、近乎纯白的页面和干净的白色扫描页；含文字、批注、表单、可见标记或无法确认的页面会保留。采用保守判断，带明显底灰、污点的扫描页可能保留。移除数量会写入运行记录；整份输入全为空白时跳过，不生成空 PDF，也不修改原文件。

## 主要功能

- **批量转换**：Word（`.doc`、`.docx`）、Excel（`.xls`、`.xlsx`、`.xlsm`）、PowerPoint（`.ppt`、`.pptx`）、图片（`.jpg`、`.jpeg`、`.png`）转 PDF，以及已有 PDF 的处理。
- **双引擎支持**：选择 Microsoft Office、WPS Office 或自动模式。自动模式优先 Office，仅在组件无法启动时尝试 WPS；文档打开或导出失败会显示在日志中。
- **拆分与合并**：合并多个文件，按页拆分，按 Excel 工作表拆分，选择页码范围或工作表。
- **PDF 加工**：两个可配置水印、页码、密码、元数据清理和压缩；可先生成首页水印预览。
- **命名与预设**：使用命名标签、自定义输出目录、保存与加载预设；输出重名时自动追加序号，保留已有文件。
- **任务管理**：拖入文件、队列筛选与排序、失败重试、进度与活动日志。
- **界面偏好**：简体中文、繁体中文、英语、日语即时切换；代码雨可关闭，并遵循系统减少动态效果设置。

## 开始使用

1. 使用 Windows 10/11（64 位），安装 Microsoft Edge WebView2 Runtime。
2. 转换 Office 文档时，安装对应的 Microsoft Office 或支持 COM 自动化的 WPS 组件。PDF、图片处理无需办公套件。WPS 的兼容性取决于所安装组件；目前不支持 `.wps`、`.et`、`.dps` 原生格式。
3. 运行 [MatrixFlowPDF.exe](dist/MatrixFlowPDF.exe)。前端与 Python 服务已打包，使用者无需安装 Node.js 或 Python。
4. 拖入文件或点击添加文件，通过文件行的范围按钮选择页码或工作表。
5. 选择引擎、输出位置与处理选项，点击开始转换；出现错误时查看活动日志并重试失败项。

转换在本地完成。浏览器中的开发预览仅展示界面，本地转换和窗口控制需要在桌面程序中使用。

## 命名与水印标签

| 标签 | 含义 |
| --- | --- |
| `{name}` / `{sheet}` / `{parent}` | 原文件名、Excel 工作表名、上级文件夹 |
| `{seq}` / `{fseq}` / `{pseq}` | 全局序号、输入文件序号、页序号 |
| `{total}` / `{ptotal}` | 输入文件数量、当前文档或单元的页数 |
| `{username}` / `{rand}` | Windows 用户名、四位随机数 |
| `{date:yyyy-mm-dd}` | 日期；支持 `yyyy`、`mm`、`dd`、`HH`、`MM`、`SS` |

页码格式使用 `{n}` 和 `{total}`，例如 `- {n} / {total} -`。页码范围示例：`1-3,5`、`2`、`-3`、`8-`。

## 从源码运行与打包

开发环境：Windows、Python 3.12、Node.js 24、WebView2 Runtime。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe desktop.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MatrixFlowPDF.spec
```

产物为 `dist/MatrixFlowPDF.exe`。源码结构、测试和开发预览见[开发说明](DESKTOP_DEVELOPMENT.md)。

## 配置与旧版本升级

配置和预设保存在 `%APPDATA%/MatrixFlowPDF`。可通过 `MATRIXFLOW_DATA_DIR` 指定其他目录。

首次启动时，如果新目录没有配置，会复制 `%APPDATA%/Office2PDF` 中的旧配置；也兼容 exe 同目录或当前工作目录中的配置。旧配置保持原样，已有的新配置不会被覆盖。为兼容旧版本，保留 `OFFICE2PDF_DATA_DIR` 环境变量别名与 `pdf_pro_config_v4.json` 文件名。

## 许可证

[MIT License](LICENSE)，保留原作者版权声明。
