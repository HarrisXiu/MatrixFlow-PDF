"""Headless regression tests for the React/Python bridge and conversion workflow."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pypdf import PdfReader, PdfWriter
from desktop_service import ConversionService, DesktopAPI


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.service = ConversionService(self.folder / 'settings')
        self.service.save({'out_mode':'custom','output_dir':str(self.folder/'out'), 'auto_open':False})
        self.source = self.folder / 'input.pdf'
        writer = PdfWriter()
        for _ in range(2): writer.add_blank_page(width=595,height=842)
        with self.source.open('wb') as stream: writer.write(stream)

    def tearDown(self):
        self.temp.cleanup()

    def wait_job(self):
        deadline=time.monotonic()+20
        while self.service.processing and time.monotonic()<deadline:
            time.sleep(.02)
        self.assertFalse(self.service.processing, 'worker did not finish')

    def test_export_and_retry(self):
        bad=self.folder/'bad.pdf';bad.write_bytes(b'not a pdf')
        self.service.add([str(self.source),str(bad)])
        self.service.start({});self.wait_job()
        self.assertEqual([f['status'] for f in self.service.files],['success','failed'])
        output=self.folder/'out'/'input.pdf'
        self.assertEqual(len(PdfReader(output).pages),2)
        stamp=output.stat().st_mtime_ns
        bad.write_bytes(self.source.read_bytes())
        self.service.start({},retry=True);self.wait_job()
        self.assertEqual([f['status'] for f in self.service.files],['success','success'])
        self.assertEqual(output.stat().st_mtime_ns,stamp)

    def test_merge_range_watermark_and_password(self):
        second=self.folder/'second.pdf';second.write_bytes(self.source.read_bytes())
        self.service.add([str(self.source),str(second)])
        self.service.set_range(str(self.source),'2')
        self.service.start({'merge_all':True,'wm1_text':'CONFIDENTIAL','wm1_pos':'diag',
                            'pg_enabled':True,'password':'test-only'})
        self.wait_job()
        reader=PdfReader(self.folder/'out'/'input.pdf')
        self.assertTrue(reader.is_encrypted)
        self.assertTrue(reader.decrypt('test-only'))
        self.assertEqual(len(reader.pages),3)
        self.assertTrue(all(f['status']=='success' for f in self.service.files))

    def test_split_and_configuration_snapshot(self):
        self.service.add([str(self.source)])
        self.service.start({'split_pdf_page':True,'naming_tpl':'{name}_{pseq}'})
        self.service.save({'naming_tpl':'changed'})
        self.wait_job()
        self.assertEqual(len(list((self.folder/'out').glob('input_*.pdf'))),2)
        self.assertFalse(list((self.folder/'out').glob('changed*')))

    def test_cancellation(self):
        self.service.add([str(self.source)])
        original=self.service.cv_pdf
        def cancel(*args):
            result=original(*args);self.service.cancel();return result
        with patch.object(self.service,'cv_pdf',side_effect=cancel):
            self.service.start({});self.wait_job()
        self.assertEqual(self.service.files[0]['status'],'cancelled')
        self.assertFalse((self.folder/'out'/'input.pdf').exists())

    def test_queue_presets_and_migration(self):
        other=self.folder/'second.pdf';other.write_bytes(self.source.read_bytes())
        self.service.add([str(self.source),str(other),str(self.source)])
        self.assertEqual(len(self.service.files),2)
        self.service.modify_queue('up',[str(other)])
        self.assertEqual(self.service.files[0]['path'],str(other))
        self.service.modify_queue('remove',[str(other)])
        self.assertEqual(len(self.service.files),1)
        self.service.preset('save','WPS',{'engine':'wps','matrix_motion':False})
        self.service.preset('load','WPS')
        restored=ConversionService(self.folder/'settings')
        self.assertEqual(restored.config.engine,'wps')
        self.assertFalse(restored.config.matrix_motion)
        self.assertIn('WPS',restored.presets)

    def test_invalid_settings_and_ranges(self):
        self.service.add([str(self.source)])
        for value in ('abc','0x20','1,,3'):
            with self.assertRaises(ValueError): self.service.set_range(str(self.source),value)
        with self.assertRaises(ValueError): self.service.save({'wm_alpha':5})

    def test_existing_output_is_preserved(self):
        self.service.add([str(self.source)])
        self.service.start({});self.wait_job()
        original=(self.folder/'out'/'input.pdf').read_bytes()
        self.service.start({});self.wait_job()
        self.assertEqual((self.folder/'out'/'input.pdf').read_bytes(),original)
        self.assertTrue((self.folder/'out'/'input_1.pdf').exists())

    def test_window_controls(self):
        api=DesktopAPI(self.service)
        api._window=MagicMock()
        api.window_control('minimize')
        api._window.minimize.assert_called_once()
        self.assertTrue(api.window_control('maximize'))
        api._window.maximize.assert_called_once()
        self.assertFalse(api.window_control('maximize'))
        api._window.restore.assert_called_once()
        api.window_control('close')
        deadline=time.monotonic()+2
        while not api._window.destroy.called and time.monotonic()<deadline: time.sleep(.01)
        api._window.destroy.assert_called_once()

    def test_file_picker_validates_native_filter_and_adds_selection(self):
        import webview
        from webview.util import parse_file_type

        document = self.folder / 'selected.docx'
        document.write_bytes(b'file picker fixture')
        api = DesktopAPI(self.service)
        api._window = MagicMock()

        def native_dialog(dialog_type, *, allow_multiple, file_types):
            self.assertEqual(dialog_type, webview.FileDialog.OPEN)
            self.assertTrue(allow_multiple)
            extensions = set()
            for file_type in file_types:
                _, patterns = parse_file_type(file_type)
                extensions.update(patterns.split(';'))
            self.assertEqual(extensions, {
                '*.doc', '*.docx', '*.xls', '*.xlsx', '*.xlsm', '*.ppt',
                '*.pptx', '*.pdf', '*.png', '*.jpg', '*.jpeg',
            })
            return (str(self.source), str(document))

        api._window.create_file_dialog.side_effect = native_dialog
        result = api.pick_files()
        self.assertEqual([item['path'] for item in result['files']],
                         [str(self.source), str(document)])
        self.assertEqual([item['type'] for item in result['files']], ['PDF', 'Word'])

    def test_cancelled_file_picker_preserves_queue(self):
        self.service.add([str(self.source)])
        api = DesktopAPI(self.service)
        api._window = MagicMock()
        api._window.create_file_dialog.return_value = None
        result = api.pick_files()
        self.assertEqual([item['path'] for item in result['files']], [str(self.source)])


if __name__=='__main__': unittest.main()
