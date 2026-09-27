# MatrixFlow PDF · 矩流 PDF

**Let your documents flow.** A local Windows workspace for batch document conversion and PDF processing.

[English](README.md) · [简体中文](readme.zh-cn.md) · [繁體中文](readme.zh-tw.md) · [日本語](readme.ja.md)

<img src="assets/matrixflow-pdf.png" alt="MatrixFlow PDF" width="96" />

MatrixFlow PDF combines a React interface with a Python conversion service. Its charcoal and mint-green design, optional code rain, integrated window controls and persistent run bar keep batch tasks easy to manage, including in smaller windows.

## Queue ordering and blank pages

Drag anywhere on a file row onto the upper or lower half of another row to insert it before or after that file. A green line marks the destination. Click **Name** or **Type** in the table header to toggle ascending/descending order. Name sorting ignores case and uses natural numbers (file2 before file10); type sorting groups extensions and then names. These operations change the actual conversion/merge order, including when the list is filtered, and are disabled during conversion.

In **Advanced → Blank pages**, choose **Keep blank pages** (default) or **Detect and remove**. Removal runs after page-range selection and before splitting, merging, watermarks and page numbering. It renders candidate pages with PDFium and removes entirely white or near-white pages, including clean white scans. Pages containing text, annotations/forms, visible marks, uncertain render results or obvious scan noise are kept. This conservative detector may retain noisy or off-white scans. Removal counts appear in Activity. All-blank inputs are skipped without producing empty PDFs; source files are never changed.

## Features

- Convert Word (`.doc`, `.docx`), Excel (`.xls`, `.xlsx`, `.xlsm`), PowerPoint (`.ppt`, `.pptx`) and images (`.jpg`, `.jpeg`, `.png`) to PDF; process existing PDFs.
- Choose Microsoft Office, WPS Office or Auto. Auto tries WPS only if the required Office component cannot start; document/export errors remain visible in the activity log.
- Merge files, split by page or Excel sheet, and select page ranges or worksheets.
- Apply two configurable watermarks, page numbers, passwords, metadata removal and compression.
- Preview a watermark on the first page, customize output names, and save reusable presets.
- Filter and reorder the queue, retry failed items, and track progress. Existing output files are preserved by adding numeric suffixes to new files.
- Switch between English, Simplified Chinese, Traditional Chinese and Japanese in Preferences. Code rain can be disabled and respects reduced-motion settings.

## Run the application

1. Use Windows 10/11 (64-bit) with Microsoft Edge WebView2 Runtime.
2. For Office documents, install the corresponding Microsoft Office or COM-enabled WPS components. PDF/image processing does not require an office suite. WPS support depends on the installed COM components; native `.wps`, `.et` and `.dps` files are not supported.
3. Run [MatrixFlowPDF.exe](dist/MatrixFlowPDF.exe). The frontend and Python service are bundled; end users do not need Node.js or Python.
4. Add files using the file picker or drag and drop. Use the range button in a file row to select pages or sheets.
5. Choose an output folder, conversion engine and processing options, then start conversion. Use Activity to inspect errors or retry failed files.

Conversion runs locally. Browser development previews display the interface but do not perform native conversion or window actions.

## Naming and watermark tags

| Tag | Meaning |
| --- | --- |
| `{name}` / `{sheet}` / `{parent}` | Source filename, Excel sheet name, parent folder |
| `{seq}` / `{fseq}` / `{pseq}` | Global, input-file and page sequence numbers |
| `{total}` / `{ptotal}` | Input count and current document/unit page count |
| `{username}` / `{rand}` | Windows username and random four-digit number |
| `{date:yyyy-mm-dd}` | Date; supports `yyyy`, `mm`, `dd`, `HH`, `MM`, `SS` |

Page-number formats use `{n}` and `{total}`, for example `- {n} / {total} -`. Page-range examples: `1-3,5`, `2`, `-3`, `8-`.

## Build from source

Requires Python 3.12, Node.js 24 and WebView2 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe desktop.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MatrixFlowPDF.spec
```

Output: `dist/MatrixFlowPDF.exe`. See [development, testing and packaging](DESKTOP_DEVELOPMENT.md).

## Settings and upgrades

Settings and presets live in `%APPDATA%/MatrixFlowPDF`. Set `MATRIXFLOW_DATA_DIR` to use a different directory.

On first launch, existing settings from `%APPDATA%/Office2PDF` are copied into the new directory if it has no configuration. A configuration beside the executable or in the working directory is also supported. Original settings are preserved, and an existing new configuration is never replaced. The legacy `OFFICE2PDF_DATA_DIR` variable and `pdf_pro_config_v4.json` filename remain supported for compatibility.

## License

[MIT](LICENSE). Original copyright attribution is preserved.
