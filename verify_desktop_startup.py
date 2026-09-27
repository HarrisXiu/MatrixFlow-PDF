"""Smoke-test the compiled React UI against a real hidden WebView2 bridge."""
import tempfile
import time
from pathlib import Path

import webview
from pypdf import PdfWriter
from desktop_service import ConversionService, DesktopAPI


def main():
    failures = []
    with tempfile.TemporaryDirectory() as folder:
        service = ConversionService(folder)
        service.save({'matrix_motion': False})
        for name in ('file10.pdf', 'file2.pdf', 'file1.pdf'):
            path = Path(folder) / name
            writer = PdfWriter(); writer.add_blank_page(width=300, height=400)
            writer.write(str(path))
            service.add([str(path)])
        api = DesktopAPI(service)
        window = webview.create_window(
            'MatrixFlow PDF startup check',
            str(Path(__file__).parent / 'frontend' / 'build' / 'index.html'),
            js_api=api, hidden=True,
        )
        api._window = window

        def verify():
            try:
                assert window.events.loaded.wait(20), 'WebView2 did not finish loading'
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    state = window.evaluate_js('''(() => ({
                        snapshot: typeof window.pywebview?.api?.snapshot,
                        ready: document.querySelector('.window-controls button')?.disabled === false,
                        error: document.querySelector('.toast')?.textContent || ''
                    }))()''')
                    assert not state['error'], state['error']
                    if state['snapshot'] == 'function' and state['ready']:
                        print('PASS: compiled React UI connected to the real WebView2 API without a startup error', flush=True)
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError('Frontend did not connect to the native API')

                def wait_order(names):
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        actual = window.evaluate_js("Array.from(document.querySelectorAll('.filename strong'), e => e.textContent)")
                        if actual == names:
                            assert [Path(f['path']).name for f in service.files] == names
                            return
                        time.sleep(.1)
                    raise AssertionError(f'Queue order did not update: {actual}')

                window.evaluate_js("document.querySelector('[aria-label=\"按名称排序\"]').click()")
                wait_order(['file1.pdf', 'file2.pdf', 'file10.pdf'])
                window.evaluate_js('''(() => {
                    const source = document.querySelector('.file-table tbody tr');
                    if (!source.draggable) throw new Error('Queue row is not draggable');
                    const filename = source.querySelector('.filename strong');
                    const row = document.querySelectorAll('.file-table tbody tr')[2];
                    const transfer = new DataTransfer();
                    const options = {bubbles:true, cancelable:true, dataTransfer:transfer};
                    filename.dispatchEvent(new DragEvent('dragstart', options));
                    const rect = row.getBoundingClientRect();
                    options.clientY = rect.bottom - 2;
                    row.dispatchEvent(new DragEvent('dragover', options));
                    row.dispatchEvent(new DragEvent('drop', options));
                    source.dispatchEvent(new DragEvent('dragend', options));
                })()''')
                wait_order(['file2.pdf', 'file10.pdf', 'file1.pdf'])
                assert service.queue_sort is None
                assert not window.evaluate_js("document.querySelector('.drop-overlay,.toast') !== null")
                print('PASS: real WebView2 column sorting and full-row drag update the Python conversion queue', flush=True)
            except Exception as exc:
                failures.append(exc)
            finally:
                window.destroy()

        webview.start(verify, gui='edgechromium', private_mode=True)
    if failures:
        raise failures[0]


if __name__ == '__main__':
    main()
