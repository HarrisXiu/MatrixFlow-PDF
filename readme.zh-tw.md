# 矩流 PDF · MatrixFlow PDF

**讓文件有序流轉。** 適用於 Windows 的本機批次文件轉換與 PDF 處理工具。

[English](README.md) · [简体中文](readme.zh-cn.md) · [繁體中文](readme.zh-tw.md) · [日本語](readme.ja.md)

<img src="assets/matrixflow-pdf.png" alt="矩流 PDF" width="96" />

矩流 PDF 採用 React 前端與 Python 轉換服務，搭配深灰、薄荷綠配色與可關閉的程式碼雨。無邊框標題列整合視窗控制；執行列保持可見，窄視窗採用縱向排列。

## 主要功能

- Word（`.doc`、`.docx`）、Excel（`.xls`、`.xlsx`、`.xlsm`）、PowerPoint（`.ppt`、`.pptx`）、圖片（`.jpg`、`.jpeg`、`.png`）轉 PDF，並可處理現有 PDF。
- Microsoft Office、WPS Office 與自動模式。自動模式優先 Office，只有元件無法啟動時才嘗試 WPS；開啟或匯出失敗會記錄於日誌。
- 合併檔案、按頁或 Excel 工作表分割、選擇頁碼範圍與工作表。
- 兩組浮水印、頁碼、密碼、中繼資料清理、壓縮與首頁浮水印預覽。
- 自訂命名規則與輸出位置、儲存預設；同名輸出自動加上序號，保留原檔。
- 拖曳加入、佇列篩選與排序、失敗重試、活動日誌與進度顯示。
- 偏好設定支援繁體中文、簡體中文、英語與日語即時切換，以及動態效果開關。

## 開始使用

1. 準備 Windows 10/11（64 位元）與 Microsoft Edge WebView2 Runtime。
2. Office 文件轉換需要安裝對應的 Microsoft Office 或支援 COM 的 WPS 元件。PDF、圖片處理不需要辦公套件。WPS 支援取決於安裝版本的 COM 能力；不支援 `.wps`、`.et`、`.dps` 原生格式。
3. 執行 [MatrixFlowPDF.exe](dist/MatrixFlowPDF.exe)，無需安裝 Python 或 Node.js。
4. 加入檔案，點擊檔案列的範圍按鈕設定頁碼或工作表。
5. 選擇引擎、輸出目錄與處理選項，開始轉換。錯誤可於活動日誌查看，並重試失敗項目。

所有轉換在本機完成。瀏覽器開發預覽僅展示介面；本機轉換與視窗控制需使用桌面程式。

## 命名與浮水印標籤

| 標籤 | 含義 |
| --- | --- |
| `{name}` / `{sheet}` / `{parent}` | 來源檔名、工作表名、上層資料夾 |
| `{seq}` / `{fseq}` / `{pseq}` | 全域、輸入檔案與頁面序號 |
| `{total}` / `{ptotal}` | 輸入數量、目前文件或單元頁數 |
| `{username}` / `{rand}` | Windows 使用者名稱、四位隨機數 |
| `{date:yyyy-mm-dd}` | 日期，支援 `yyyy`、`mm`、`dd`、`HH`、`MM`、`SS` |

頁碼格式例如 `- {n} / {total} -`；範圍例如 `1-3,5`、`2`、`-3`、`8-`。

## 開發與建置

需要 Windows、Python 3.12、Node.js 24 與 WebView2 Runtime。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe desktop.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MatrixFlowPDF.spec
```

輸出為 `dist/MatrixFlowPDF.exe`。詳見[開發說明](DESKTOP_DEVELOPMENT.md)。

## 設定與升級

設定與預設位於 `%APPDATA%/MatrixFlowPDF`，可用 `MATRIXFLOW_DATA_DIR` 指定其他目錄。新目錄沒有設定時，首次啟動會複製 `%APPDATA%/Office2PDF` 的舊設定，也支援執行檔旁或工作目錄中的設定。原設定保持不變，已有新設定不會覆寫。相容性保留項為 `OFFICE2PDF_DATA_DIR` 環境變數與 `pdf_pro_config_v4.json` 檔名。

## 授權

[MIT License](LICENSE)，保留原作者版權聲明。
