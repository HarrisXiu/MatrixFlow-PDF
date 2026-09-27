"""UI-independent Office/WPS conversion engine, shared by the React desktop shell."""
import os
import json
import datetime
import re
import threading
import tempfile
import io
import random
import getpass
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import pythoncom
import winreg
from pypdf import PdfWriter, PdfReader
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from office_backend import application, close_document


def tr(core, key):
    return {'running': '转换中', 'finishing': '生成输出'}.get(key, key)

I18N = {
    "ja": {
        "win_title": "MatrixFlow PDF v6.0",
        "file_list": "変換ファイル(ドロップで登録・ダブルクリックでページ指定)",
        "col_type": "種別",
        "col_name": "ファイル名",
        "col_range": "範囲",
        "col_out": "出力先",
        "btn_up": "上へ",
        "btn_down": "下へ",
        "btn_remove": "削除",
        "btn_clear": "全消去",
        "btn_clear_list": "リスト全クリア",
        "btn_add_folder": "フォルダ追加",
        "frame_wm": "透かし・ページ番号設定",
        "lbl_font": "フォント:",
        "lbl_size": "サイズ:",
        "lbl_alpha": "不透明度:",
        "btn_start": "PDF変換開始",
        "btn_cancel": "キャンセル",
        "msg_no_file": "ファイルがありません。",
        "err_save_config": "設定保存エラー:",
        "lbl_presets": "設定プリセット:",
        "btn_load": "読込",
        "btn_save": "保存",
        "btn_delete": "削除",
        "btn_preview_wm": "選択ファイルの1頁目をプレビュー",
        "pos_page_center": "中央下",
        "lbl_watermark": "透かし",
        "wm_label": "透かし",
        "pos_none": "なし",
        "pos_diag_center": "中央斜め",
        "pos_large_center": "中央大",
        "pos_top_left": "左上",
        "pos_top_center": "上中央",
        "pos_top_right": "右上",
        "pos_bottom_left": "左下",
        "pos_bottom_center": "下中央",
        "pos_bottom_right": "右下",
        "pos_page_center": "中央下(ページ番号用)",
        "lbl_page_num": "ページ番号:",
        "frame_detail": "出力・分割詳細設定",
        "chk_merge": "【全結合】1つのPDFにまとめる",
        "chk_split_page": "ページ毎分割",
        "chk_include_ppt": "(PPTも)",
        "chk_by_sheet": "シート毎",
        "chk_by_all_pages": "全ページ毎",
        "lbl_excel_opt": "--- Excelオプション (印刷範囲優先) ---",
        "chk_fit_width": "横幅1ページに収める",
        "chk_fit_height": "縦幅1ページに収める",
        "frame_exec": "保存設定・実行",
        "lbl_naming": "ファイル名・命名ルール:",
        "btn_tag_help": "タグ説明",
        "opt_same_dir": "元と同じ場所",
        "opt_custom_dir": "カスタム:",
        "btn_browse": "参照",
        "lbl_password": "パスワード:",
        "chk_meta_clear": "メタ削除",
        "chk_compress": "PDF軽量化",
        "chk_open_done": "完了後開く",
        "chk_open_folder": "フォルダ開く",
        "chk_clear_after": "リストクリア",
        "st_ready": "待機中...",
        "log_font_loaded": "フォント一覧の読み込みが完了しました。",
        "log_font_err": "フォント取得エラー:",
        "log_font_using": "使用フォント:",
        "log_font_fail": "フォント登録失敗:",
        "title_warn": "警告",
        "msg_no_files": "ファイルがありません",
        "st_converting": "変換中...",
        "st_conv_file": "変換中:",
        "st_finalizing": "最終処理中...",
        "log_fatal": "致命的エラー:",
        "val_all_pages": "全ページ",
        "log_ppt_err": "PPT変換エラー",
        "title_info": "情報",
        "msg_no_preview": "プレビューするファイルがありません。",
        "st_preview_gen": "プレビュー生成中:",
        "log_conv_fail": "変換に失敗しました:",
        "msg_no_output": "処理対象のファイルが生成されなかったため、終了します。",
        "msg_preview_ok": "プレビューを表示しました。",
        "msg_preview_fail": "プレビュー失敗:",
        "title_tag_help": "命名ルールのタグ説明",
        "title_overwrite": "上書き確認",
        "msg_exists": "存在します:",
        "btn_overwrite": "上書き",
        "btn_seq": "連番",
        "btn_abort": "中止",
        "msg_all_done": "すべての処理が完了しました。",
        "log_preset_load": "プリセットを読込。",
        "lbl_preset_name": "プリセット名:",
        "title_confirm": "確認",
        "msg_ask_delete": "削除しますか？",
        "title_range": "範囲編集",
        "pg_pos_bc": "中央下",
        "pg_pos_br": "右下",
        "msg_lang_restart": "言語を変更しました。アプリを再起動して適用しますか？",
        "lbl_output_example": "出力例",
        "help_tags": (
            "【利用可能なタグ】\n\n"
            "{name} : 元のファイル名\n"
            "{sheet} : Excelシート名\n"
            "{parent} : 親フォルダの名前\n"
            "{seq} : 全体の通し番号\n"
            "{fseq} : ファイル毎の番号\n"
            "{pseq} : ページ毎の番号\n"
            "{total} : 全ファイル数\n"
            "{ptotal} : ファイル内の総ページ数\n"
            "{username} : PCユーザー名\n"
            "{rand} : 4桁のランダム数字\n\n"
            "【日付・時刻】\n"
            "{date:yyyy-mm-dd} -> 2024-02-06\n"
            "※HH:時, MM:分, SS:秒"
        ),
    },
    "en": {
        "win_title": "MatrixFlow PDF v6.0",
        "file_list": "Files (Drag & Drop to add / Double-click to set range)",
        "col_type": "Type",
        "col_name": "File Name",
        "col_range": "Range",
        "col_out": "Output Preview",
        "btn_up": "Up",
        "btn_down": "Down",
        "btn_remove": "Remove",
        "btn_clear": "Clear List",
        "btn_clear_list": "Clear List",
        "btn_add_folder": "Add Folder",
        "frame_wm": "Watermark & Page Number",
        "lbl_font": "Font:",
        "lbl_size": "Size:",
        "lbl_alpha": "Opacity:",
        "btn_start": "Start Conversion",
        "btn_cancel": "Cancel",
        "msg_no_file": "No files selected.",
        "err_save_config": "Error saving settings:",
        "lbl_presets": "Presets:",
        "btn_load": "Load",
        "btn_save": "Save",
        "btn_delete": "Delete",
        "btn_preview_wm": "Preview 1st page of selected file",
        "pos_page_center": "Bottom Center (Mid)",
        "lbl_watermark": "Watermark",
        "wm_label": "Watermark",
        "pos_none": "None",
        "pos_diag_center": "Diagonal Center",
        "pos_large_center": "Large Center",
        "pos_top_left": "Top Left",
        "pos_top_center": "Top Center",
        "pos_top_right": "Top Right",
        "pos_bottom_left": "Bottom Left",
        "pos_bottom_center": "Bottom Center",
        "pos_bottom_right": "Bottom Right",
        "pos_page_center": "Bottom Center (Page)",
        "lbl_page_num": "Page Numbers:",
        "frame_detail": "Output & Split Settings",
        "chk_merge": "[Merge] Combine into a single PDF",
        "chk_split_page": "Split by Page",
        "chk_include_ppt": "(Include PPT)",
        "chk_by_sheet": "By Sheet",
        "chk_by_all_pages": "By All Pages",
        "lbl_excel_opt": "--- Excel Options (Prioritize Print Area) ---",
        "chk_fit_width": "Fit width to 1 page",
        "chk_fit_height": "Fit height to 1 page",
        "frame_exec": "Export Settings & Run",
        "lbl_naming": "Naming Rules:",
        "btn_tag_help": "Tag Guide",
        "opt_same_dir": "Same as source",
        "opt_custom_dir": "Custom:",
        "btn_browse": "Browse...",
        "lbl_password": "Password:",
        "chk_meta_clear": "Strip Metadata",
        "chk_compress": "Compress PDF",
        "chk_open_done": "Open when done",
        "chk_open_folder": "Open folder",
        "chk_clear_after": "Clear list",
        "st_ready": "Ready...",
        "log_font_loaded": "Font list loaded successfully.",
        "log_font_err": "Error fetching fonts:",
        "log_font_using": "Font used:",
        "log_font_fail": "Failed to register font:",
        "title_warn": "Warning",
        "msg_no_files": "No files selected",
        "st_converting": "Converting...",
        "st_conv_file": "Converting:",
        "st_finalizing": "Finalizing...",
        "log_fatal": "Critical Error:",
        "val_all_pages": "All Pages",
        "log_ppt_err": "PPT Conversion Error",
        "title_info": "Info",
        "msg_no_preview": "No file to preview.",
        "st_preview_gen": "Generating preview:",
        "log_conv_fail": "Conversion failed:",
        "msg_no_output": "No output files were generated. Process aborted.",
        "msg_preview_ok": "Preview displayed successfully.",
        "msg_preview_fail": "Preview failed:",
        "title_tag_help": "Naming Rule Tag Guide",
        "title_overwrite": "Confirm Overwrite",
        "msg_exists": "File already exists:",
        "btn_overwrite": "Overwrite",
        "btn_seq": "Add Seq Number",
        "btn_abort": "Abort",
        "msg_all_done": "All processes completed successfully.",
        "log_preset_load": "Preset loaded.",
        "lbl_preset_name": "Preset Name:",
        "title_confirm": "Confirm",
        "msg_ask_delete": "Are you sure you want to delete?",
        "title_range": "Edit Range",
        "pg_pos_bc": "Bottom Center",
        "pg_pos_br": "Bottom Right",
        "msg_lang_restart": "Language changed. Restart the app to apply?",
        "lbl_output_example": "Output example",
        "help_tags": (
            "[Available Tags]\n\n"
            "{name} : Original filename\n"
            "{sheet} : Excel sheet name\n"
            "{parent} : Parent folder name\n"
            "{seq} : Global sequence number\n"
            "{fseq} : File sequence number\n"
            "{pseq} : Page sequence number\n"
            "{total} : Total file count\n"
            "{ptotal} : Total pages in file\n"
            "{username} : PC username\n"
            "{rand} : 4-digit random number\n\n"
            "[Date & Time]\n"
            "{date:yyyy-mm-dd} -> 2024-02-06\n"
            "* HH:Hour, MM:Min, SS:Sec"
        ),
    },
    "zh_cn": {
        "win_title": "MatrixFlow PDF v6.0",
        "file_list": "转换文件（拖拽添加 / 双击设置页码范围）",
        "col_type": "类型",
        "col_name": "文件名",
        "col_range": "范围",
        "col_out": "输出预览",
        "btn_up": "上移",
        "btn_down": "下移",
        "btn_remove": "移除",
        "btn_clear": "全部清除",
        "btn_clear_list": "清空列表",
        "btn_add_folder": "添加文件夹",
        "frame_wm": "水印与页码设置",
        "lbl_font": "字体:",
        "lbl_size": "大小:",
        "lbl_alpha": "不透明度:",
        "btn_start": "开始转换 PDF",
        "btn_cancel": "取消",
        "msg_no_file": "没有选择文件。",
        "err_save_config": "设置保存错误:",
        "lbl_presets": "设置预设:",
        "btn_load": "读取",
        "btn_save": "保存",
        "btn_delete": "删除",
        "btn_preview_wm": "预览所选文件第 1 页",
        "pos_page_center": "下方居中",
        "lbl_watermark": "水印",
        "wm_label": "水印",
        "pos_none": "无",
        "pos_diag_center": "居中斜排",
        "pos_large_center": "居中大字",
        "pos_top_left": "左上",
        "pos_top_center": "顶部居中",
        "pos_top_right": "右上",
        "pos_bottom_left": "左下",
        "pos_bottom_center": "底部居中",
        "pos_bottom_right": "右下",
        "pos_page_center": "下方居中（页码用）",
        "lbl_page_num": "页码:",
        "frame_detail": "输出与拆分详细设置",
        "chk_merge": "【全部合并】合并为一个 PDF",
        "chk_split_page": "按页拆分",
        "chk_include_ppt": "（含 PPT）",
        "chk_by_sheet": "按工作表",
        "chk_by_all_pages": "按全部页面",
        "lbl_excel_opt": "--- Excel 选项（优先打印区域） ---",
        "chk_fit_width": "宽度适配一页",
        "chk_fit_height": "高度适配一页",
        "frame_exec": "保存设置与执行",
        "lbl_naming": "文件名命名规则:",
        "btn_tag_help": "标签说明",
        "opt_same_dir": "与原文件相同",
        "opt_custom_dir": "自定义:",
        "btn_browse": "浏览...",
        "lbl_password": "密码:",
        "chk_meta_clear": "删除元数据",
        "chk_compress": "PDF 瘦身",
        "chk_open_done": "完成后打开",
        "chk_open_folder": "打开文件夹",
        "chk_clear_after": "清空列表",
        "st_ready": "待机中...",
        "log_font_loaded": "字体列表加载完成。",
        "log_font_err": "获取字体出错:",
        "log_font_using": "使用字体:",
        "log_font_fail": "字体注册失败:",
        "title_warn": "警告",
        "msg_no_files": "没有选择文件",
        "st_converting": "转换中...",
        "st_conv_file": "转换中:",
        "st_finalizing": "正在完成最后处理...",
        "log_fatal": "致命错误:",
        "val_all_pages": "全部页面",
        "log_ppt_err": "PPT 转换错误",
        "title_info": "信息",
        "msg_no_preview": "没有可预览的文件。",
        "st_preview_gen": "正在生成预览:",
        "log_conv_fail": "转换失败:",
        "msg_no_output": "未生成任何输出文件，已终止。",
        "msg_preview_ok": "预览已显示。",
        "msg_preview_fail": "预览失败:",
        "title_tag_help": "命名规则标签说明",
        "title_overwrite": "覆盖确认",
        "msg_exists": "已存在:",
        "btn_overwrite": "覆盖",
        "btn_seq": "加序号",
        "btn_abort": "中止",
        "msg_all_done": "全部处理完成。",
        "log_preset_load": "预设已读取。",
        "lbl_preset_name": "预设名称:",
        "title_confirm": "确认",
        "msg_ask_delete": "确定要删除吗？",
        "title_range": "编辑范围",
        "pg_pos_bc": "下方居中",
        "pg_pos_br": "右下",
        "msg_lang_restart": "语言已切换。重启应用以应用新语言吗？",
        "lbl_output_example": "输出示例",
        "help_tags": (
            "【可用标签】\n\n"
            "{name} : 原文件名\n"
            "{sheet} : Excel 工作表名\n"
            "{parent} : 上级文件夹名\n"
            "{seq} : 全局序号\n"
            "{fseq} : 文件内序号\n"
            "{pseq} : 页面序号\n"
            "{total} : 文件总数\n"
            "{ptotal} : 文件内总页数\n"
            "{username} : 电脑用户名\n"
            "{rand} : 4 位随机数字\n\n"
            "【日期与时间】\n"
            "{date:yyyy-mm-dd} -> 2024-02-06\n"
            "※HH:时, MM:分, SS:秒"
        ),
    },
    "zh_tw": {
        "win_title": "MatrixFlow PDF v6.0",
        "file_list": "轉換檔案（拖曳加入 / 雙擊設定頁碼範圍）",
        "col_type": "類型",
        "col_name": "檔案名稱",
        "col_range": "範圍",
        "col_out": "輸出位置",
        "btn_up": "上移",
        "btn_down": "下移",
        "btn_remove": "移除",
        "btn_clear": "全部清除",
        "btn_clear_list": "清空清單",
        "btn_add_folder": "加入資料夾",
        "frame_wm": "浮水印與頁碼設定",
        "lbl_font": "字型:",
        "lbl_size": "大小:",
        "lbl_alpha": "不透明度:",
        "btn_start": "開始轉換 PDF",
        "btn_cancel": "取消",
        "msg_no_file": "尚未選擇檔案。",
        "err_save_config": "設定儲存錯誤:",
        "lbl_presets": "設定預設:",
        "btn_load": "讀取",
        "btn_save": "儲存",
        "btn_delete": "刪除",
        "btn_preview_wm": "預覽所選檔案第 1 頁",
        "pos_page_center": "下方置中",
        "lbl_watermark": "浮水印",
        "wm_label": "浮水印",
        "pos_none": "無",
        "pos_diag_center": "置中斜排",
        "pos_large_center": "置中大字",
        "pos_top_left": "左上",
        "pos_top_center": "上方置中",
        "pos_top_right": "右上",
        "pos_bottom_left": "左下",
        "pos_bottom_center": "下方置中",
        "pos_bottom_right": "右下",
        "pos_page_center": "下方置中（頁碼用）",
        "lbl_page_num": "頁碼:",
        "frame_detail": "輸出與分割詳細設定",
        "chk_merge": "【全部合併】合併為單一 PDF",
        "chk_split_page": "按頁分割",
        "chk_include_ppt": "（含 PPT）",
        "chk_by_sheet": "按工作表",
        "chk_by_all_pages": "按全部頁面",
        "lbl_excel_opt": "--- Excel 選項（優先列印範圍） ---",
        "chk_fit_width": "寬度適應單頁",
        "chk_fit_height": "高度適應單頁",
        "frame_exec": "儲存設定與執行",
        "lbl_naming": "檔案命名規則:",
        "btn_tag_help": "標籤說明",
        "opt_same_dir": "與原始檔相同",
        "opt_custom_dir": "自訂:",
        "btn_browse": "瀏覽...",
        "lbl_password": "密碼:",
        "chk_meta_clear": "移除中繼資料",
        "chk_compress": "PDF 瘦身",
        "chk_open_done": "完成後開啟",
        "chk_open_folder": "開啟資料夾",
        "chk_clear_after": "清空清單",
        "st_ready": "待機中...",
        "log_font_loaded": "字型清單載入完成。",
        "log_font_err": "取得字型錯誤:",
        "log_font_using": "使用字型:",
        "log_font_fail": "字型註冊失敗:",
        "title_warn": "警告",
        "msg_no_files": "尚未選擇檔案",
        "st_converting": "轉換中...",
        "st_conv_file": "轉換中:",
        "st_finalizing": "正在完成最後處理...",
        "log_fatal": "嚴重錯誤:",
        "val_all_pages": "全部頁面",
        "log_ppt_err": "PPT 轉換錯誤",
        "title_info": "資訊",
        "msg_no_preview": "沒有可預覽的檔案。",
        "st_preview_gen": "正在產生預覽:",
        "log_conv_fail": "轉換失敗:",
        "msg_no_output": "未產生任何輸出檔案，已中止。",
        "msg_preview_ok": "預覽已顯示。",
        "msg_preview_fail": "預覽失敗:",
        "title_tag_help": "命名規則標籤說明",
        "title_overwrite": "覆蓋確認",
        "msg_exists": "已存在:",
        "btn_overwrite": "覆蓋",
        "btn_seq": "加編號",
        "btn_abort": "中止",
        "msg_all_done": "全部處理完成。",
        "log_preset_load": "預設已讀取。",
        "lbl_preset_name": "預設名稱:",
        "title_confirm": "確認",
        "msg_ask_delete": "確定要刪除嗎？",
        "title_range": "編輯範圍",
        "pg_pos_bc": "下方置中",
        "pg_pos_br": "右下",
        "msg_lang_restart": "語言已切換。重新啟動應用程式以套用新語言嗎？",
        "lbl_output_example": "輸出範例",
        "help_tags": (
            "【可用標籤】\n\n"
            "{name} : 原始檔案名稱\n"
            "{sheet} : Excel 工作表名稱\n"
            "{parent} : 上層資料夾名稱\n"
            "{seq} : 全域流水號\n"
            "{fseq} : 檔案內流水號\n"
            "{pseq} : 頁面流水號\n"
            "{total} : 檔案總數\n"
            "{ptotal} : 檔案內總頁數\n"
            "{username} : 電腦使用者名稱\n"
            "{rand} : 4 位隨機數字\n\n"
            "【日期與時間】\n"
            "{date:yyyy-mm-dd} -> 2024-02-06\n"
            "※HH:時, MM:分, SS:秒"
        ),
    },
}


POS_MAP = [
    ("None", "pos_none"),
    ("diag", "pos_diag_center"),
    ("large", "pos_large_center"),
    ("tl", "pos_top_left"),
    ("tc", "pos_top_center"),
    ("tr", "pos_top_right"),
    ("bl", "pos_bottom_left"),
    ("bc", "pos_bottom_center"),
    ("br", "pos_bottom_right"),
]


@dataclass
class AppConfig:
    matrix_motion: bool = True
    engine: str = "auto"
    lang: str = ""  # 手动选择的语言（空 = 自动检测）
    output_dir: str = ""
    out_mode: str = "original"
    naming_tpl: str = "{name}"
    auto_open: bool = True
    open_folder: bool = False
    clear_after: bool = False
    compress_pdf: bool = False  # 追加
    blank_page_action: str = 'keep'

    wm1_text: str = ""
    wm1_pos: str = "None"
    wm2_text: str = ""
    wm2_pos: str = "None"

    wm_font: str = ""
    wm_size: int = 60
    wm_color: str = "#C0C0C0"
    wm_alpha: float = 0.3

    pg_enabled: bool = False
    pg_pos: str = "bc"
    pg_format: str = "- {n} / {total} -"

    merge_all: bool = False
    split_word_page: bool = False
    split_ppt_page: bool = False
    split_pdf_page: bool = False
    split_excel_sheet: bool = False
    split_excel_page: bool = False

    password: str = ""
    excel_fit: bool = False
    excel_fit_tall: bool = False
    clear_metadata: bool = False

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.expanduser(r"~\Desktop")


class ConversionCore:
    def build_registry_font_items(self):
        items_for_combo = []
        self.font_map = {}
        if winreg is None:
            return []
        fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
        ]
        seen_names = set()
        for root, keypath in roots:
            try:
                with winreg.OpenKey(root, keypath) as k:
                    i = 0
                    while True:
                        try:
                            name_raw, val, _ = winreg.EnumValue(k, i)
                            i += 1
                            if not isinstance(val, str):
                                continue
                            file_name = re.split(r"[,&]", val)[0].strip()
                            full_path = os.path.join(fonts_dir, file_name)
                            if not os.path.exists(full_path):
                                continue
                            clean_raw = re.sub(r"\s*\(.*?\)", "", name_raw).replace(";", "")
                            sub_names = [n.strip() for n in clean_raw.split("&")]
                            for idx, sub_name in enumerate(sub_names):
                                if sub_name and sub_name not in seen_names:
                                    seen_names.add(sub_name)
                                    self.font_map[sub_name] = (full_path, idx)
                                    items_for_combo.append(sub_name)
                        except OSError:
                            break
            except:
                continue
        items_for_combo.sort()
        return items_for_combo


    def _register_reportlab_font(self, chosen_font: str) -> Tuple[str, str]:
        chosen = chosen_font or ""
        if chosen in self.font_map:
            p, idx = self.font_map[chosen]
            internal_name = f"WM_{chosen.replace(' ', '_')}_{idx}"
            try:
                if internal_name not in pdfmetrics.getRegisteredFontNames():
                    if p.lower().endswith(".ttc"):
                        pdfmetrics.registerFont(TTFont(internal_name, p, subfontIndex=idx))
                    else:
                        pdfmetrics.registerFont(TTFont(internal_name, p))
                return internal_name, f"{self._('log_font_using')}: {chosen}"
            except Exception as e:
                self.queue_log(f"{self._('log_font_fail')}: {e}")

        try:
            pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
            return "HeiseiKakuGo-W5", f"{self._('log_font_using')}: HeiseiKakuGo-W5 (CID)"
        except:
            return "Helvetica", f"{self._('log_font_using')}: Helvetica"


    def main_process(self, cfg: AppConfig, files=None):
        files = files if files is not None else [dict(f) for f in self.files]
        states = {f['path']: 'pending' for f in files}
        last_output = ''
        def state(f, value):
            states[f['path']] = value
            self.queue_progress(file_state=(f['path'], value))
        pythoncom.CoInitialize()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                units = []
                for i, f in enumerate(files):
                    if self.cancel_flag.is_set():
                        break
                    state(f, 'running')
                    self.queue_progress(label=f"{tr(self, 'running')} / {os.path.basename(f['path'])}")
                    try:
                        if f['type'] == 'Excel':
                            converted = self.cv_excel_units(f, tmp_dir, cfg)
                        else:
                            target = os.path.join(tmp_dir, f'file_{i}.pdf')
                            if f['type'] == 'Word':
                                ok = self.cv_word(f, target, cfg)
                            elif f['type'] == 'PowerPoint':
                                ok = self.cv_ppt(f, target, cfg)
                            elif f['type'] == 'Image':
                                ok = self.cv_img(f, target)
                            else:
                                ok = self.cv_pdf(f, target)
                            if ok and not self._is_all_range(f.get('range', '')):
                                ranged = os.path.join(tmp_dir, f'range_{i}.pdf')
                                ok = self.apply_range_to_pdf(target, f['range'], ranged)
                                target = ranged
                            converted = [(target, '')] if ok else []
                        if not converted:
                            raise RuntimeError(self._('log_conv_fail'))
                        if cfg.blank_page_action == 'remove':
                            from blank_pages import remove_blank_pages
                            retained = []
                            for unit_index, (path, sheet) in enumerate(converted):
                                filtered = os.path.join(tmp_dir, f'nonblank_{i}_{unit_index}.pdf')
                                usable, removed = remove_blank_pages(path, filtered, self.cancel_flag, self.queue_log)
                                if removed:
                                    pages = ', '.join(map(str, removed[:20])) + ('…' if len(removed) > 20 else '')
                                    self.queue_log(f"{os.path.basename(f['path'])}{' [' + sheet + ']' if sheet else ''}：移除 {len(removed)} 个空白页（所选页面：{pages}）")
                                if usable:
                                    retained.append((usable, sheet))
                            converted = retained
                            if not converted:
                                self.queue_log(f"{os.path.basename(f['path'])}：所选页面全部为空白页，已跳过，不生成空文件")
                                state(f, 'skipped')
                                self.queue_progress(progress=i + 1)
                                continue
                        units.extend({'path': path, 'orig': f, 'sheet': sheet, 'fseq': i + 1}
                                     for path, sheet in converted)
                        state(f, 'finishing')
                    except InterruptedError:
                        state(f, 'cancelled')
                    except Exception as exc:
                        state(f, 'failed')
                        self.queue_log(f"{os.path.basename(f['path'])}: {exc}", error=True)
                    self.queue_progress(progress=i + 1)

                sequence = 1
                if units and not self.cancel_flag.is_set():
                    self.queue_progress(label=tr(self, 'finishing'))
                    if cfg.merge_all:
                        try:
                            dest = self.get_final_dest(units[0], 1, 1, 1, cfg=cfg)
                            if dest:
                                self.finalize_pdfs([u['path'] for u in units], dest, units, cfg)
                                last_output = dest
                            for f in files:
                                if states[f['path']] == 'finishing':
                                    state(f, ('partial' if f.get('_conversion_errors') else 'success') if dest else 'skipped')
                        except Exception as exc:
                            self.queue_log(str(exc), error=True)
                            for f in files:
                                if states[f['path']] == 'finishing':
                                    state(f, 'failed')
                        self.queue_progress(progress=len(files) * 2)
                    else:
                        for i, f in enumerate(files):
                            if self.cancel_flag.is_set():
                                break
                            group = [u for u in units if u['orig'] is f]
                            if not group:
                                continue
                            wrote = False
                            skipped = False
                            try:
                                split_pages = {'Word': cfg.split_word_page, 'PowerPoint': cfg.split_ppt_page,
                                               'PDF': cfg.split_pdf_page, 'Excel': cfg.split_excel_page}.get(f['type'], False)
                                outputs = []
                                if split_pages:
                                    for u in group:
                                        reader = PdfReader(u['path'])
                                        for page_index, page in enumerate(reader.pages):
                                            target = os.path.join(tmp_dir, f'split_{i}_{len(outputs)}.pdf')
                                            writer = PdfWriter()
                                            writer.add_page(page)
                                            with open(target, 'wb') as stream:
                                                writer.write(stream)
                                            outputs.append(([target], [u], page_index + 1, len(reader.pages)))
                                elif f['type'] == 'Excel' and cfg.split_excel_sheet:
                                    outputs = [([u['path']], [u], 1, 0) for u in group]
                                else:
                                    outputs = [([u['path'] for u in group], group, 1, 0)]
                                for paths, output_units, page, total in outputs:
                                    if self.cancel_flag.is_set():
                                        break
                                    dest = self.get_final_dest(output_units[0], sequence, i + 1, page, total or 1, cfg)
                                    if not dest:
                                        skipped = True
                                        continue
                                    self.finalize_pdfs(paths, dest, output_units, cfg, page, total)
                                    wrote = True
                                    sequence += 1
                                    last_output = dest
                                state(f, 'cancelled' if self.cancel_flag.is_set() else
                                      ('partial' if f.get('_conversion_errors') or skipped else 'success') if wrote else 'skipped')
                            except Exception as exc:
                                state(f, 'partial' if wrote else 'failed')
                                self.queue_log(f"{os.path.basename(f['path'])}: {exc}", error=True)
                            self.queue_progress(progress=len(files) + i + 1)
                if last_output:
                    self.finish_action(last_output, cfg)
        except Exception as exc:
            self.queue_log(str(exc), error=True)
        finally:
            for f in files:
                if states[f['path']] in ('pending', 'running', 'finishing'):
                    state(f, 'cancelled' if self.cancel_flag.is_set() else 'failed')
            self.queue_progress(job_done=states, output=last_output,
                                clear_after=cfg.clear_after and all(s == 'success' for s in states.values()))
            pythoncom.CoUninitialize()


    def validate_export(self, path):
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise RuntimeError(f"PDF export missing: {path}")
        if not PdfReader(path).pages:
            raise RuntimeError(f"PDF export has no pages: {path}")


    def cv_excel_units(self, f: dict, tmp_dir: str, cfg: AppConfig) -> List[Tuple[str, str]]:
        units = []
        try:
            with application("Excel", cfg.engine, self.queue_log) as session:
                excel = session.app
                wb = None
                try:
                    excel.DisplayAlerts = False
                    wb = excel.Workbooks.Open(os.path.abspath(f["path"]), ReadOnly=True)
                    session.observe_document(wb)
                    names = [s.strip() for s in f.get("range", "").split(",") if s.strip()]
                    if not names or self._is_all_range(f.get("range", "")):
                        names = [s.Name for s in wb.Worksheets]
                    for name in names:
                        if self.cancel_flag.is_set():
                            break
                        try:
                            ws = wb.Worksheets(name)
                            if ws.Visible != -1:
                                continue
                            if cfg.excel_fit or cfg.excel_fit_tall:
                                ws.PageSetup.Zoom = False
                                if cfg.excel_fit:
                                    ws.PageSetup.FitToPagesWide = 1
                                if cfg.excel_fit_tall:
                                    ws.PageSetup.FitToPagesTall = 1
                            fd, target = tempfile.mkstemp(prefix="sheet_", suffix=".pdf", dir=tmp_dir)
                            os.close(fd)
                            ws.ExportAsFixedFormat(0, os.path.abspath(target))
                            self.validate_export(target)
                            units.append((target, name))
                        except Exception as exc:
                            f['_conversion_errors'] = True
                            self.queue_log(f"{self._('log_conv_fail')} {f['path']} [{name}]: {exc}", error=True)
                finally:
                    close_document(wb, self.queue_log)
        except Exception as exc:
            self.queue_log(f"{self._('log_conv_fail')} {f['path']}: {exc}")
        return units


    def cv_document(self, kind, f, out, cfg):
        try:
            with application(kind, cfg.engine, self.queue_log) as session:
                app = session.app
                doc = None
                try:
                    if kind == "Word":
                        doc = app.Documents.Open(os.path.abspath(f["path"]), ReadOnly=True)
                        session.observe_document(doc)
                        doc.ExportAsFixedFormat(os.path.abspath(out), 17)
                    else:
                        doc = app.Presentations.Open(os.path.abspath(f["path"]), True, False, False)
                        session.observe_document(doc)
                        doc.ExportAsFixedFormat(os.path.abspath(out), 2, PrintRange=None)
                    self.validate_export(out)
                    return True
                finally:
                    close_document(doc, self.queue_log, presentation=kind == "PowerPoint")
        except Exception as exc:
            self.queue_log(f"{self._('log_conv_fail')} {f['path']}: {exc}")
            return False


    def cv_word(self, f, out, cfg):
        return self.cv_document("Word", f, out, cfg)


    def cv_ppt(self, f, out, cfg):
        return self.cv_document("PowerPoint", f, out, cfg)


    def cv_img(self, f, out):
        try:
            with Image.open(f["path"]) as img:
                img.convert("RGB").save(out, "PDF")
            return True
        except:
            return False


    def cv_pdf(self, f, out):
        try:
            reader = PdfReader(f["path"])
            writer = PdfWriter()
            for p in reader.pages:
                writer.add_page(p)
            with open(out, "wb") as fs:
                writer.write(fs)
            return True
        except:
            return False


    def finalize_pdfs(
        self,
        src_list: List[str],
        dest: str,
        units: List[dict],
        cfg: AppConfig,
        page_offset: int = 1,
        total_override: int = 0,
    ):
        writer = PdfWriter()
        font_name, _ = self._register_reportlab_font(cfg.wm_font)

        readers = [PdfReader(s) for s in src_list]
        total_p = total_override if total_override > 0 else sum(len(r.pages) for r in readers)
        curr_p = page_offset

        # 透かし有無
        has_wm = any([cfg.wm1_text and cfg.wm1_pos != "None", cfg.wm2_text and cfg.wm2_pos != "None"])
        has_pg = cfg.pg_enabled

        for r in readers:
            for page in r.pages:
                page.transfer_rotation_to_content()

                if has_wm or has_pg:
                    w, h = float(page.mediabox.width), float(page.mediabox.height)
                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=(w, h))

                    # ---- Watermark (1/2) ----
                    for txt_raw, pos_id in [(cfg.wm1_text, cfg.wm1_pos), (cfg.wm2_text, cfg.wm2_pos)]:
                        if pos_id == "None" or not txt_raw:
                            continue

                        txt = self.apply_tags(txt_raw, units[0], curr_p, units[0].get("fseq", 1), curr_p, total_p)
                        c.saveState()

                        f_size = int(cfg.wm_size)
                        c.setFont(font_name, f_size)

                        rgb = [int(cfg.wm_color.lstrip("#")[j : j + 2], 16) / 255 for j in (0, 2, 4)]
                        c.setFillColorRGB(*rgb, alpha=float(cfg.wm_alpha))

                        if pos_id == "diag":
                            c.translate(w / 2, h / 2)
                            c.rotate(45)
                            c.drawCentredString(0, 0, txt)
                        elif pos_id == "large":
                            c.drawCentredString(w / 2, h / 2, txt)
                        else:
                            tw = c.stringWidth(txt, font_name, f_size)

                            if "l" in pos_id:
                                tx = 20
                            elif "r" in pos_id:
                                tx = w - tw - 20
                            else:
                                tx = (w - tw) / 2

                            if "t" in pos_id:
                                ty = h - f_size - 20
                            elif "b" in pos_id:
                                ty = 20
                            else:
                                ty = h / 2

                            c.drawString(tx, ty, txt)

                        c.restoreState()

                    # ---- Page number ----

                    if has_pg:
                        pg_txt = cfg.pg_format.replace("{n}", str(curr_p)).replace("{total}", str(total_p))
                        pg_txt = self.apply_tags(pg_txt, units[0], curr_p, units[0].get("fseq", 1), curr_p, total_p)

                        c.saveState()

                        # ★固定：10.5pt / 黒（必ずここで定義）
                        pg_size = 10.5
                        c.setFont(font_name, pg_size)
                        c.setFillColorRGB(0, 0, 0)  # 黒固定

                        tw = c.stringWidth(pg_txt, font_name, pg_size)

                        # bc=中央下, br=右下
                        margin_x = 20
                        margin_y = 24
                        if cfg.pg_pos == "br":
                            x = w - tw - margin_x
                            y = margin_y
                        else:  # "bc" default
                            x = (w - tw) / 2
                            y = margin_y

                        c.drawString(x, y, pg_txt)
                        c.restoreState()

                    c.showPage()
                    c.save()
                    packet.seek(0)
                    page.merge_page(PdfReader(packet).pages[0])

                writer.add_page(page)
                curr_p += 1

        if cfg.clear_metadata:
            writer.add_metadata({})
        if cfg.password:
            writer.encrypt(cfg.password)
        if cfg.compress_pdf:
            if hasattr(writer, "compress_contents"):
                writer.compress_contents()
            elif hasattr(writer, "compress_content_streams"):
                writer.compress_content_streams()

        with open(dest, "wb") as f:
            writer.write(f)


    def _is_all_range(self, s: str) -> bool:
        s = (s or "").strip()
        if not s:
            return True
        return s in ("全ページ", "All Pages", self._("val_all_pages"))


    def parse_page_spec(self, spec: str, total_pages: int) -> List[int]:
        """
        spec例: "1-3,5,8-" / "2" / "1-" / "-3"（-3は1-3扱い）
        戻り値: 0-based page indices（重複排除、昇順）
        """
        if self._is_all_range(spec):
            return list(range(total_pages))

        spec = spec.replace(" ", "")
        out = set()

        for token in [t for t in spec.split(",") if t]:
            m = re.fullmatch(r"(\d+)?-(\d+)?", token)
            if m:
                a, b = m.group(1), m.group(2)
                start = int(a) if a else 1
                end = int(b) if b else total_pages
                start = max(1, start)
                end = min(total_pages, end)
                if start <= end:
                    for p in range(start, end + 1):
                        out.add(p - 1)
                continue

            if token.isdigit():
                p = int(token)
                if 1 <= p <= total_pages:
                    out.add(p - 1)

        return sorted(out)


    def apply_range_to_pdf(self, src_pdf: str, range_spec: str, dst_pdf: str) -> bool:
        """
        src_pdf を range_spec に従って抽出して dst_pdf へ。
        range_spec が全ページなら単純コピー（読み書き）する。
        """
        try:
            r = PdfReader(src_pdf)
            total = len(r.pages)
            idxs = self.parse_page_spec(range_spec, total)
            if not idxs:
                return False

            w = PdfWriter()
            for i in idxs:
                w.add_page(r.pages[i])

            with open(dst_pdf, "wb") as f:
                w.write(f)
            return True
        except:
            return False


    def apply_tags(self, tpl: str, u_info: dict, seq: int, fseq: int, pseq: int, ptotal: int = 1) -> str:
        now = datetime.datetime.now()
        path = u_info["orig"]["path"]
        name = os.path.splitext(os.path.basename(path))[0]
        sheet = u_info.get("sheet", "")
        parent = os.path.basename(os.path.dirname(path))  # 親フォルダ名

        res = tpl
        res = res.replace("{name}", name)
        res = res.replace("{sheet}", sheet)
        res = res.replace("{parent}", parent)
        res = res.replace("{seq}", str(seq))
        res = res.replace("{fseq}", str(fseq))
        res = res.replace("{pseq}", str(pseq))
        res = res.replace("{total}", str(len(self.files)))
        res = res.replace("{ptotal}", str(ptotal))
        res = res.replace("{username}", getpass.getuser())
        res = res.replace("{rand}", f"{random.randint(0, 9999):04d}")

        # 日付・時刻タグの処理 {date:yyyy-mm-dd HH:MM:SS} 等
        def _repl(m):
            fmt = m.group(1)
            # Pythonのstrftime形式に変換
            fmt = fmt.replace("yyyy", "%Y").replace("mm", "%m").replace("dd", "%d")
            fmt = fmt.replace("HH", "%H").replace("MM", "%M").replace("SS", "%S")
            return now.strftime(fmt)

        res = re.sub(r"{date:(.*?)}", _repl, res)
        return res


    def get_final_dest(self, u_info, seq, fseq, pseq, ptotal=1, cfg=None):
        cfg = cfg or self.config
        out_name = self.apply_tags(cfg.naming_tpl, u_info, seq, fseq, pseq, ptotal)
        base = (
            os.path.dirname(u_info["orig"]["path"]) if cfg.out_mode == "original" else cfg.output_dir
        )
        if not os.path.exists(base):
            os.makedirs(base, exist_ok=True)
        dest = os.path.join(base, re.sub(r'[\\/:*?"<>|]+', "_", out_name) + ".pdf")
        return self.confirm_overwrite_or_rename(dest)


    def get_excel_sheets(self, p):
        try:
            with application("Excel", self.config.engine, self.queue_log) as session:
                ex = session.app
                wb = None
                try:
                    wb = ex.Workbooks.Open(os.path.abspath(p), ReadOnly=True)
                    session.observe_document(wb)
                    return [s.Name for s in wb.Worksheets]
                finally:
                    close_document(wb, self.queue_log)
        except Exception as exc:
            self.queue_log(f"{self._('log_conv_fail')} {p}: {exc}")
            return []
