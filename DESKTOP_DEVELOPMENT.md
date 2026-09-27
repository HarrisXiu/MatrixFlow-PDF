# MatrixFlow PDF — development guide

MatrixFlow PDF (矩流 PDF) is a Windows desktop application with a React/Vite frontend and a Python service hosted by pywebview/WebView2. The executable embeds the compiled frontend and needs no development server.

## Source layout

| Path | Responsibility |
| --- | --- |
| `frontend/src/main.jsx` | Queue, settings, activity, preferences and titlebar controls |
| `frontend/src/styles.css` | Responsive charcoal/mint theme and code rain |
| `frontend/src/locales.js` | Japanese and Traditional Chinese UI strings |
| `desktop.py` | Frameless window, native drag/drop and lifecycle |
| `app_paths.py` | Storage paths and migration from the previous application name |
| `desktop_service.py` | Synchronized API, queue, presets, dialogs and window actions |
| `blank_pages.py` | Conservative visual blank-page detection with PDFium |
| `conversion_core.py` | Conversion, PDF processing, naming and shared translations |
| `office_backend.py` | Office/WPS COM adapters and session cleanup |
| `assets/` | Icon master, Windows ICO, generation prompt and executable version metadata |
| `MatrixFlowPDF.spec` | PyInstaller packaging definition |
| `test_artifacts/sample.*` | Input fixtures for real Office/WPS conversion checks |

## Setup and packaging

Use Windows, Python 3.12, Node.js 24 and WebView2 Runtime. Office documents require the corresponding Office or COM-enabled WPS components; PDF/image processing does not.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe desktop.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MatrixFlowPDF.spec
```

The output is `dist/MatrixFlowPDF.exe`. Packaging includes the React build, native window icon and Windows product metadata. Build the frontend before packaging Python.

## Frontend development

Run `npm.cmd --prefix frontend run dev`. The browser preview does not expose native file dialogs, conversion or window controls. Use `desktop.py` with a freshly built frontend to exercise those features. Restart the desktop application after changing native window behavior.

The header is the drag region; double-clicking maximizes/restores the window. Code rain is optional and respects reduced-motion preferences. The run bar remains visible and narrow windows stack the workspace vertically.

## Verification

```powershell
.\.venv\Scripts\python.exe -B -m unittest test_blank_pages test_app_paths test_desktop_service test_office_backend -v
npm.cmd --prefix frontend exec -- vitest run --root frontend
.\.venv\Scripts\python.exe verify_desktop_startup.py
.\.venv\Scripts\python.exe verify_desktop_engines.py
```

Python tests cover configuration migration, output preservation, cancellation, queue operations, presets, PDF processing and engine selection. React tests exercise the queue, titlebar actions and preferences. The smoke script requires both Office and WPS and exports the three supplied Office fixtures through the desktop service.

Build the frontend before running `verify_desktop_startup.py`. This check opens a hidden WebView2 window, waits for the real Python bridge and confirms that the compiled interface connects without a startup error, then closes the window.

To regenerate the sample documents, install `python-docx`, `openpyxl` and `python-pptx` in a development environment and run `test_artifacts_setup.py`. These packages are not runtime dependencies.

## Configuration and compatibility

Default storage: `%APPDATA%/MatrixFlowPDF`. Override it with `MATRIXFLOW_DATA_DIR`; the legacy `OFFICE2PDF_DATA_DIR` remains an alias with lower priority.

The JSON filename remains `pdf_pro_config_v4.json` to preserve its schema and compatibility. On first launch without an existing target configuration:

1. If no override is set, look in `%APPDATA%/Office2PDF`.
2. Then look beside the executable and in the working directory.
3. Copy the first existing configuration into the new directory, leaving the original untouched.

Existing new settings are never replaced. An explicit override skips the old AppData directory, allowing isolated development runs.

## Conversion behavior

Auto mode tries WPS only when the required Office component cannot start. It does not switch engines after a document/export failure. Existing output files are preserved by adding numeric suffixes.

Cancellation waits for the current synchronous COM operation to finish before releasing the document. Closing the window during conversion requests cancellation. COM session ownership protects existing user sessions from being closed.

## Branding

Display name: **MatrixFlow PDF**. Chinese name: **矩流 PDF**. Tagline: **让文档有序流转。**

Executable: `MatrixFlowPDF.exe`; npm package: `matrixflow-pdf`; icon master: `assets/matrixflow-pdf.png`. Windows icon and frontend favicon derive from the same artwork. The original MIT copyright attribution remains in `LICENSE`.

## Queue ordering and blank-page removal

`modify_queue` supports relative `move_before`/`move_after` operations using source/target paths and `sort_name`/`sort_type` with `asc`/`desc`. All operations run under the service lock and reject mutation while converting. `queue_sort` exposes the active column/direction and clears after manual moves or new files. The frontend separates internal row drags from external file drops.

`blank_page_action` is `keep` by default; `remove` filters each converted unit after range selection and before split/merge/watermark/page-number generation. All-blank inputs become skipped. Candidate pages are rendered by [pypdfium2](https://pypdfium2.readthedocs.io/en/stable/python_api.html). Text/annotations are retained first, then every rendered color channel must stay at least 252/255 to classify a page as blank. Rendering uses 108 dpi and an eight-million-pixel limit; oversized or uncertain pages are retained. PDFium calls are serialized with a process lock. Scans with background noise are intentionally retained. Source PDFs are unchanged.

The startup smoke check also drives table sorting and HTML drag events through the real WebView2 bridge. Python tests verify that queue ordering affects merged page order and blank removal preserves sparse content, numbering and previews.
