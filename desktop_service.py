"""Thread-safe bridge between the React application and local conversion engine."""
import copy
import json
import os
import re
from pathlib import Path
import threading
import time
import tempfile
from dataclasses import asdict, fields
from collections import deque
from conversion_core import ConversionCore, AppConfig, I18N, POS_MAP
from pypdf import PdfReader, PdfWriter


class ConversionService(ConversionCore):
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.processing = False
        self.cancel_flag = threading.Event()
        self.files = []
        self.queue_sort = None
        self.font_map = {}
        self.logs = deque(maxlen=400)
        self.actual_engine = ''
        self.progress = 0
        self.maximum = 1
        self.label = '准备就绪'
        self.last_output = ''
        self.presets = {}
        self.config = AppConfig(lang='zh_cn', auto_open=False)
        config_path = self.data_dir / 'pdf_pro_config_v4.json'
        if config_path.exists():
            try:
                saved = json.loads(config_path.read_text(encoding='utf-8'))
                self.config = self._config(saved.get('current', {}))
                self.presets = saved.get('presets', {})
            except (ValueError, TypeError):
                pass
        self.lang = self.config.lang if self.config.lang in I18N else 'zh_cn'
        self._ = lambda key: I18N[self.lang].get(key, key)
        self.fonts = self.build_registry_font_items()
        if not self.config.wm_font:
            self.config.wm_font = next((f for f in self.fonts if f in ('Microsoft YaHei','微软雅黑','Arial')), '')

    def _config(self, changes):
        names = {f.name for f in fields(AppConfig)}
        data = asdict(self.config) if hasattr(self, 'config') else {}
        data.update({k:v for k,v in changes.items() if k in names})
        cfg = AppConfig(**data)
        if cfg.engine not in ('auto','office','wps'):
            raise ValueError('无效的转换引擎')
        if cfg.blank_page_action not in ('keep', 'remove'):
            raise ValueError('空白页处理必须为保留或移除')
        if cfg.lang not in ('','zh_cn','zh_tw','en','ja'):
            raise ValueError('无效的语言')
        cfg.wm_size = int(cfg.wm_size)
        cfg.wm_alpha = float(cfg.wm_alpha)
        if not 10 <= cfg.wm_size <= 300 or not 0 <= cfg.wm_alpha <= 1:
            raise ValueError('水印字号需为 10–300，透明度需为 0–1')
        import re
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', cfg.wm_color):
            raise ValueError('无效的水印颜色')
        if not cfg.naming_tpl.strip():
            raise ValueError('请输入输出命名规则')
        return cfg

    def snapshot(self):
        with self.lock:
            rows = []
            for i, item in enumerate(self.files, 1):
                row = dict(item)
                row['name'] = os.path.basename(item['path'])
                unit = {'orig': item, 'sheet': item['sheets'][0] if item['sheets'] else '', 'fseq':i}
                row['output'] = self.apply_tags(self.config.naming_tpl, unit, i, i, 1) + '.pdf'
                rows.append(row)
            return {'files': rows, 'queue_sort': self.queue_sort, 'busy': self.processing, 'progress': self.progress,
                    'maximum': self.maximum, 'label': self.label, 'logs': list(self.logs),
                    'last_output':self.last_output, 'actual_engine':self.actual_engine,
                    'config':asdict(self.config), 'presets':list(self.presets), 'fonts':self.fonts,
                    'translations':I18N[self.lang], 'positions':POS_MAP}

    def save(self, changes):
        with self.lock:
            cfg = self._config(changes)
            self.config = cfg
            self.lang = cfg.lang or 'zh_cn'
            target = self.data_dir / 'pdf_pro_config_v4.json'
            temp = target.with_suffix('.tmp')
            temp.write_text(json.dumps({'current':asdict(cfg),'presets':self.presets},ensure_ascii=False,indent=2),encoding='utf-8')
            temp.replace(target)
        return asdict(cfg)

    def add(self, paths):
        types = {'.doc':'Word','.docx':'Word','.xls':'Excel','.xlsx':'Excel','.xlsm':'Excel',
                 '.ppt':'PowerPoint','.pptx':'PowerPoint','.pdf':'PDF','.png':'Image','.jpg':'Image','.jpeg':'Image'}
        with self.lock:
            if self.processing:
                raise ValueError('请等待当前任务结束后再添加文件')
            existing = {os.path.normcase(f['path']) for f in self.files}
            for path in paths:
                if not path:
                    continue
                p = Path(path).absolute()
                if p.suffix.lower() not in types or not p.is_file():
                    self.queue_log(f'已跳过不支持的文件：{p.name}')
                    continue
                if os.path.normcase(str(p)) in existing:
                    continue
                self.files.append({'path':str(p),'type':types[p.suffix.lower()], 'range':'',
                                   'sheets':[], 'status':'pending','size':p.stat().st_size})
                self.queue_sort = None
                existing.add(os.path.normcase(str(p)))
        return self.snapshot()

    def modify_queue(self, operation, paths):
        with self.lock:
            if self.processing:
                raise ValueError('转换期间不能修改文件队列')
            if operation == 'clear':
                self.files = []
                self.queue_sort = None
            elif operation == 'remove': self.files = [f for f in self.files if f['path'] not in paths]
            elif operation in ('sort_name', 'sort_type'):
                if len(paths) != 1 or paths[0] not in ('asc', 'desc'):
                    raise ValueError('排序方向必须为升序或降序')
                def natural_name(item):
                    return tuple((0, int(part)) if part.isascii() and part.isdigit() else (1, part)
                                 for part in re.split(r'([0-9]+)', Path(item['path']).name.casefold()))
                key = natural_name if operation == 'sort_name' else lambda item: (Path(item['path']).suffix.casefold(), natural_name(item))
                self.files.sort(key=key, reverse=paths[0] == 'desc')
                self.queue_sort = {'key': operation[5:], 'direction': paths[0]}
            elif operation in ('up','down') and paths:
                idx = next((i for i,f in enumerate(self.files) if f['path']==paths[0]),-1)
                dest = idx + (-1 if operation=='up' else 1)
                if idx >= 0 and 0 <= dest < len(self.files):
                    self.files[idx],self.files[dest] = self.files[dest],self.files[idx]
                    self.queue_sort = None
            elif operation in ('move_before', 'move_after'):
                if len(paths) != 2:
                    raise ValueError('请指定拖动文件和目标文件')
                source, target = paths
                source_index = next((i for i, f in enumerate(self.files) if f['path'] == source), None)
                target_index = next((i for i, f in enumerate(self.files) if f['path'] == target), None)
                if source_index is None or target_index is None:
                    raise ValueError('队列已变化，请重新拖动文件')
                if source != target:
                    item = self.files.pop(source_index)
                    target_index = next(i for i, f in enumerate(self.files) if f['path'] == target)
                    self.files.insert(target_index + (operation == 'move_after'), item)
                    self.queue_sort = None
        return self.snapshot()

    def set_range(self, path, value):
        with self.lock:
            if self.processing: raise ValueError('转换期间不能修改范围')
            item = next(f for f in self.files if f['path']==path)
            if item['type'] != 'Excel' and value:
                import re
                if not all(re.fullmatch(r'(\d+|\d*-\d+|\d+-)', t.strip()) for t in value.split(',')):
                    raise ValueError('页码格式示例：1-3,5,8-')
            item['range'] = value
        return self.snapshot()

    def sheets(self, path):
        with self.lock:
            if self.processing: raise ValueError('请等待当前任务结束')
            item = next(f for f in self.files if f['path']==path)
            self.processing = True
        try:
            names = self.get_excel_sheets(path)
            with self.lock: item['sheets'] = names
            return names
        finally:
            with self.lock: self.processing = False

    def start(self, changes, retry=False):
        with self.lock:
            if self.processing: raise ValueError('任务正在运行')
            self.save(changes)
            selected = [f for f in self.files if not retry or f['status'] in ('failed','partial')]
            if not selected: raise ValueError('请先添加需要转换的文件')
            for f in selected: f['status'] = 'pending'
            self.processing = True
            self.cancel_flag.clear()
            self.progress, self.maximum = 0, len(selected)*2
            self.label = '正在准备转换…'
            cfg = self._config({})
            worker = threading.Thread(target=self.main_process,args=(cfg,copy.deepcopy(selected)),daemon=True)
            worker.start()
        return True

    def cancel(self):
        self.cancel_flag.set()
        with self.lock: self.label = '正在取消，等待当前文档释放…'
        return True

    def queue_log(self, msg, error=False):
        with self.lock:
            error = error or any(self._(k) in msg for k in ('log_conv_fail','log_fatal','msg_preview_fail'))
            self.logs.append({'time':time.strftime('%H:%M:%S'),'message':str(msg),'error':error})
            if msg.startswith(('Word: ', 'Excel: ', 'PowerPoint: ')): self.actual_engine = msg

    def queue_progress(self, **event):
        with self.lock:
            if 'file_state' in event:
                path,status = event['file_state']
                for f in self.files:
                    if f['path']==path: f['status']=status
            for key in ('progress','label'):
                if key in event: setattr(self,key,event[key])
            if 'max' in event: self.maximum = event['max']
            if 'job_done' in event:
                states = list(event['job_done'].values())
                names={'success':'成功','failed':'失败','partial':'部分失败','cancelled':'已取消','skipped':'已跳过'}
                self.label=' · '.join(f'{names[k]} {states.count(k)}' for k in names if k in states)
                self.last_output=event['output']
                if 'cancelled' not in states: self.progress=self.maximum
                self.processing=False
                self.queue_log(self.label)
                if event.get('clear_after'): self.files=[]

    def confirm_overwrite_or_rename(self, dest):
        path=Path(dest)
        index=1
        while path.exists():
            path=Path(dest).with_name(f'{Path(dest).stem}_{index}{Path(dest).suffix}')
            index+=1
        return str(path)

    def finish_action(self, path, cfg):
        if cfg.auto_open and path: os.startfile(path)
        if cfg.open_folder and path: os.startfile(os.path.dirname(path))

    def preset(self, action, name, changes=None):
        name=name.strip()
        if not name: raise ValueError('请输入预设名称')
        with self.lock:
            if action=='save': self.presets[name]=asdict(self._config(changes or {}))
            elif action=='delete': self.presets.pop(name,None)
            elif action=='load': self.config=self._config(self.presets[name])
            self.save({})
        return self.snapshot()

    def preview(self, path, changes):
        with self.lock:
            if self.processing: raise ValueError('请等待当前任务结束')
            item=copy.deepcopy(next(f for f in self.files if f['path']==path))
            cfg=self._config(changes)
            self.processing=True
            self.label='正在生成预览…'
            self.cancel_flag.clear()
        def work():
            try:
                with tempfile.TemporaryDirectory() as folder:
                    target=os.path.join(folder,'source.pdf')
                    if item['type']=='Excel':
                        units=self.cv_excel_units(item,folder,cfg)
                        if not units: raise RuntimeError('未能导出工作表')
                        target=units[0][0]
                    else:
                        converter={'Word':lambda:self.cv_word(item,target,cfg),
                                   'PowerPoint':lambda:self.cv_ppt(item,target,cfg),
                                   'PDF':lambda:self.cv_pdf(item,target),'Image':lambda:self.cv_img(item,target)}[item['type']]
                        if not converter(): raise RuntimeError('未能生成预览')
                    reader=PdfReader(target)
                    pages=self.parse_page_spec(item['range'],len(reader.pages)) if item['type']!='Excel' else [0]
                    if not pages: raise ValueError('页码范围为空')
                    if cfg.blank_page_action == 'remove':
                        from blank_pages import remove_blank_pages
                        selected = os.path.join(folder, 'selected.pdf')
                        selection = PdfWriter()
                        for index in pages: selection.add_page(reader.pages[index])
                        with open(selected, 'wb') as stream: selection.write(stream)
                        filtered, _ = remove_blank_pages(selected, os.path.join(folder, 'nonblank.pdf'), self.cancel_flag, self.queue_log)
                        if not filtered: raise ValueError('所选页面全部为空白页，无法生成预览')
                        reader = PdfReader(filtered)
                        pages = [0]
                    writer=PdfWriter();writer.add_page(reader.pages[pages[0]])
                    first=os.path.join(folder,'first.pdf')
                    with open(first,'wb') as stream: writer.write(stream)
                    out=str(self.data_dir / 'preview.pdf')
                    self.finalize_pdfs([first],out,[{'orig':item,'sheet':'Preview','fseq':1}],cfg,1,1)
                    os.startfile(out)
                    self.queue_log('预览已打开')
            except Exception as exc: self.queue_log(str(exc),True)
            finally:
                with self.lock: self.processing=False; self.label='准备就绪'
        threading.Thread(target=work,daemon=True).start()
        return True


class DesktopAPI:
    def __init__(self, service):
        self._service=service
        self._window=None
        self._maximized=False
        self._closing=False

    def window_control(self, action):
        if action == 'minimize':
            self._window.minimize()
        elif action == 'maximize':
            if self._maximized:
                self._window.restore()
                self._maximized=False
            else:
                self._window.maximize()
                self._maximized=True
        elif action == 'close':
            if not self._closing:
                self._closing=True
                def close_when_ready():
                    if self._service.processing:
                        self._service.cancel()
                    while self._service.processing:
                        time.sleep(.1)
                    self._window.destroy()
                threading.Thread(target=close_when_ready,daemon=True).start()
        else:
            raise ValueError('Unknown window action')
        return self._maximized

    def snapshot(self): return self._service.snapshot()
    def save_config(self, config): return self._service.save(config)
    def modify_queue(self, operation, paths): return self._service.modify_queue(operation, paths)
    def set_range(self, path, value): return self._service.set_range(path, value)
    def sheets(self, path): return self._service.sheets(path)
    def start(self, config, retry=False): return self._service.start(config, retry)
    def cancel(self): return self._service.cancel()
    def preset(self, action, name, config=None): return self._service.preset(action,name,config)
    def preview(self, path, config): return self._service.preview(path,config)

    def pick_files(self):
        import webview
        paths=self._window.create_file_dialog(webview.FileDialog.OPEN,allow_multiple=True,
            file_types=('Supported files (*.doc;*.docx;*.xls;*.xlsx;*.xlsm;*.ppt;*.pptx;*.pdf;*.png;*.jpg;*.jpeg)',))
        return self._service.add(paths or [])

    def pick_folder(self, add=False):
        import webview
        paths=self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not paths: return None
        if add: return self._service.add([str(p) for p in Path(paths[0]).iterdir() if p.is_file()])
        return paths[0]

    def open_output(self):
        path=self._service.last_output
        if path and os.path.isfile(path): os.startfile(os.path.dirname(path))
        return True
