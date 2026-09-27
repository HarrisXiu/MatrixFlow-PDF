"""Smoke-test the compiled React UI against a real hidden WebView2 bridge."""
import tempfile
import time
from pathlib import Path

import webview
from desktop_service import ConversionService, DesktopAPI


def main():
    failures = []
    with tempfile.TemporaryDirectory() as folder:
        service = ConversionService(folder)
        service.save({'matrix_motion': False})
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
                        return
                    time.sleep(.1)
                raise AssertionError('Frontend did not connect to the native API')
            except Exception as exc:
                failures.append(exc)
            finally:
                window.destroy()

        webview.start(verify, gui='edgechromium', private_mode=True)
    if failures:
        raise failures[0]


if __name__ == '__main__':
    main()
