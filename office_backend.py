"""Desktop Office/WPS COM sessions. Never attach to a running user session."""
from contextlib import contextmanager

import pythoncom
import win32com.client
import win32process


PROGIDS = {
    "office": {"Word": ("Word.Application",), "Excel": ("Excel.Application",),
               "PowerPoint": ("PowerPoint.Application",)},
    "wps": {"Word": ("KWPS.Application", "WPS.Application"),
            "Excel": ("KET.Application", "ET.Application"),
            "PowerPoint": ("KWPP.Application", "WPP.Application")},
}


class Session:
    def __init__(self, app, existing_pids):
        self.app = app
        self.existing_pids = existing_pids
        self.may_quit = False
        self.observe_document(app)

    def observe_document(self, document):
        # Word exposes its window handle through the document, while Excel and
        # PowerPoint normally expose it on Application. WPS varies by version.
        for get_window in (lambda: self.app, lambda: document.ActiveWindow,
                           lambda: document.Windows.Item(1)):
            try:
                pid = win32process.GetWindowThreadProcessId(int(get_window().Hwnd))[1]
                if pid:
                    self.may_quit = pid not in self.existing_pids
                    return
            except Exception:
                continue


@contextmanager
def application(kind, engine="auto", log=lambda message: None):
    pythoncom.CoInitialize()
    app = None
    errors = []
    session = None
    try:
        if engine not in ("auto", "office", "wps"):
            raise ValueError(f"Unknown engine: {engine}")
        for provider in (("office", "wps") if engine == "auto" else (engine,)):
            for progid in PROGIDS[provider][kind]:
                try:
                    existing_pids = set(win32process.EnumProcesses())
                    app = win32com.client.DispatchEx(progid)
                    session = Session(app, existing_pids)
                    break
                except Exception as exc:
                    errors.append(f"{progid}: {exc}")
            if app is not None:
                log(f"{kind}: {'WPS Office' if provider == 'wps' else 'Microsoft Office'}")
                break
        if app is None:
            raise RuntimeError("Office/WPS component unavailable: " + " | ".join(errors))
        yield session
    finally:
        if app is not None and session is not None and session.may_quit:
            try:
                documents = getattr(app, {"Word": "Documents", "Excel": "Workbooks",
                                          "PowerPoint": "Presentations"}[kind])
                if documents.Count == 0:
                    app.Quit()
            except Exception as exc:
                log(f"Application cleanup: {exc}")
        pythoncom.CoUninitialize()


def close_document(document, log, presentation=False):
    if document is not None:
        try:
            if presentation:
                document.Close()
            else:
                document.Close(False)
        except Exception as exc:
            log(f"Document cleanup: {exc}")
