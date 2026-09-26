"""Windows entry point: compiled React UI hosted by WebView2, with a local Python bridge."""
import sys
from pathlib import Path
import webview
from webview.dom import DOMEventHandler
from desktop_service import ConversionService, DesktopAPI
from app_paths import prepare_data_dir


def main():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    data=prepare_data_dir()
    service=ConversionService(data)
    api=DesktopAPI(service)
    webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY'] = True
    window=webview.create_window('矩流 PDF · MatrixFlow PDF',str(base/'frontend'/'build'/'index.html'),
        js_api=api,width=1280,height=860,min_size=(560,480),background_color='#101512',
        text_select=True,frameless=True,easy_drag=False,shadow=True)
    api._window=window
    window.events.maximized += lambda: setattr(api, '_maximized', True)
    window.events.restored += lambda: setattr(api, '_maximized', False)
    def bind():
        window.dom.document.events.dragover += DOMEventHandler(lambda event:None,True,False,debounce=300)
        def drop(event):
            try:
                service.add([f.get('pywebviewFullPath') for f in event.get('dataTransfer',{}).get('files',[])])
            except Exception as exc: service.queue_log(str(exc),True)
        window.dom.document.events.drop += DOMEventHandler(drop,True,False)
    window.events.loaded += bind
    def closing():
        if service.processing:
            service.cancel()
            return False
        return True
    window.events.closing += closing
    webview.start(gui='edgechromium',private_mode=True,icon=str(base/'assets'/'matrixflow-pdf.ico'))


if __name__=='__main__':
    main()
