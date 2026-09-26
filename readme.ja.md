# MatrixFlow PDF · 矩流 PDF

**ドキュメントを、スムーズに。** Windows 向けのローカル一括文書変換・PDF 加工ツール。

[English](README.md) · [简体中文](readme.zh-cn.md) · [繁體中文](readme.zh-tw.md) · [日本語](readme.ja.md)

<img src="assets/matrixflow-pdf.png" alt="MatrixFlow PDF" width="96" />

React の画面と Python の変換サービスを組み合わせ、チャコールとミントグリーンの配色を採用しています。コードレインは無効にできます。ウィンドウ操作を統合したタイトルバーと常時表示の実行バーで、小さいウィンドウでも操作できます。

## 主な機能

- Word（`.doc`、`.docx`）、Excel（`.xls`、`.xlsx`、`.xlsm`）、PowerPoint（`.ppt`、`.pptx`）、画像（`.jpg`、`.jpeg`、`.png`）を PDF に変換。既存 PDF の加工にも対応。
- Microsoft Office、WPS Office、自動モードを選択。自動モードでは Office コンポーネントを起動できない場合のみ WPS を試し、文書の読み込み・出力エラーはログに表示。
- ファイル結合、ページ・Excel シート単位の分割、ページ範囲・シートの選択。
- 2 種類の透かし、ページ番号、パスワード、メタデータ削除、圧縮、先頭ページの透かしプレビュー。
- 命名ルール、出力先、プリセット保存。同名ファイルがある場合は番号を付けて既存ファイルを保持。
- ドラッグ＆ドロップ、キューの絞り込み・並べ替え、失敗項目の再試行、進捗・ログ表示。
- 設定から日本語・英語・簡体字・繁体字を即時切り替え。動きの軽減設定にも対応。

## 使い方

1. Windows 10/11（64bit）と Microsoft Edge WebView2 Runtime を用意します。
2. Office 文書の変換には、対応する Microsoft Office または COM 対応 WPS コンポーネントが必要です。PDF・画像処理には不要です。WPS の対応範囲はインストールされた COM 機能に依存し、`.wps`、`.et`、`.dps` は対象外です。
3. [MatrixFlowPDF.exe](dist/MatrixFlowPDF.exe) を実行します。利用者側で Python や Node.js を用意する必要はありません。
4. ファイルを追加し、ファイル行の範囲ボタンからページやシートを指定します。
5. エンジン、出力先、加工オプションを選んで変換を開始します。エラーはアクティビティで確認し、失敗した項目を再試行できます。

変換はローカルで行います。ブラウザーの開発プレビューでは画面のみ表示され、変換やウィンドウ操作はデスクトップ版で利用します。

## 命名・透かしタグ

| タグ | 意味 |
| --- | --- |
| `{name}` / `{sheet}` / `{parent}` | 元ファイル名、シート名、親フォルダー |
| `{seq}` / `{fseq}` / `{pseq}` | 全体、入力ファイル、ページの連番 |
| `{total}` / `{ptotal}` | 入力数、現在の文書・処理単位のページ数 |
| `{username}` / `{rand}` | Windows ユーザー名、4 桁乱数 |
| `{date:yyyy-mm-dd}` | 日付。`yyyy`、`mm`、`dd`、`HH`、`MM`、`SS` に対応 |

ページ番号例：`- {n} / {total} -`。ページ範囲例：`1-3,5`、`2`、`-3`、`8-`。

## 開発・ビルド

Windows、Python 3.12、Node.js 24、WebView2 Runtime が必要です。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe desktop.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MatrixFlowPDF.spec
```

出力先は `dist/MatrixFlowPDF.exe` です。[開発手順](DESKTOP_DEVELOPMENT.md)も参照してください。

## 設定とアップグレード

設定とプリセットは `%APPDATA%/MatrixFlowPDF` に保存されます。`MATRIXFLOW_DATA_DIR` で保存先を変更できます。新しい設定がない場合、初回起動時に `%APPDATA%/Office2PDF` の旧設定をコピーします。実行ファイルの隣や作業ディレクトリの設定にも対応します。元の設定と既存の新設定は上書きしません。互換性のため `OFFICE2PDF_DATA_DIR` と `pdf_pro_config_v4.json` の名前を引き続きサポートします。

## ライセンス

[MIT License](LICENSE)。元の著作権表示を保持しています。
