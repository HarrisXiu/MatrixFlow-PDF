import unittest
from unittest.mock import MagicMock, patch

from office_backend import application


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.dispatch = patch('office_backend.win32com.client.DispatchEx').start()
        self.initialize = patch('office_backend.pythoncom.CoInitialize').start()
        self.uninitialize = patch('office_backend.pythoncom.CoUninitialize').start()
        patch('office_backend.win32process.EnumProcesses', return_value=[100]).start()
        self.window_pid = patch('office_backend.win32process.GetWindowThreadProcessId',
                                return_value=(1, 200)).start()
        self.app = MagicMock()
        self.app.Hwnd = 123
        self.app.Documents.Count = 0
        self.dispatch.return_value = self.app
        self.addCleanup(patch.stopall)

    def test_auto_falls_back_when_office_cannot_start(self):
        self.dispatch.side_effect = [RuntimeError('not installed'), self.app]
        with application('Word') as session:
            self.assertIs(session.app, self.app)
        self.assertEqual([c.args[0] for c in self.dispatch.call_args_list],
                         ['Word.Application', 'KWPS.Application'])
        self.app.Quit.assert_called_once()
        self.uninitialize.assert_called_once()

    def test_explicit_engine_does_not_switch(self):
        self.dispatch.side_effect = RuntimeError('unavailable')
        with self.assertRaisesRegex(RuntimeError, 'unavailable'):
            with application('Word', 'office'):
                self.fail('must not open session')
        self.dispatch.assert_called_once_with('Word.Application')
        self.uninitialize.assert_called_once()

    def test_both_unavailable_give_all_component_errors(self):
        self.dispatch.side_effect = RuntimeError('missing')
        with self.assertRaisesRegex(RuntimeError, 'KWPS.Application'):
            with application('Word'):
                self.fail('must not open session')
        self.assertEqual(self.dispatch.call_count, 3)

    def test_export_failure_does_not_silently_change_engine(self):
        with self.assertRaisesRegex(ValueError, 'bad file'):
            with application('Word'):
                raise ValueError('bad file')
        self.dispatch.assert_called_once()
        self.app.Quit.assert_called_once()
        self.uninitialize.assert_called_once()

    def test_existing_user_process_is_not_quit(self):
        self.window_pid.return_value = (1, 100)
        with application('Word', 'wps'):
            pass
        self.app.Quit.assert_not_called()

    def test_user_document_opened_during_session_prevents_quit(self):
        self.app.Documents.Count = 1
        with application('Word'):
            pass
        self.app.Quit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
