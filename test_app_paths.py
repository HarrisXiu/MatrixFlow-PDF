"""Protect user configuration when adopting the new application name."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app_paths import prepare_data_dir


class StorageTests(unittest.TestCase):
    def test_migrate_once_without_changing_original_or_new_settings(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'APPDATA': folder}, clear=True):
            old = Path(folder) / 'Office2PDF' / 'pdf_pro_config_v4.json'
            old.parent.mkdir()
            old.write_text('{"presets":{"WPS":{}}}', encoding='utf-8')
            data = prepare_data_dir()
            self.assertEqual(data, Path(folder) / 'MatrixFlowPDF')
            target = data / old.name
            self.assertEqual(target.read_bytes(), old.read_bytes())
            target.write_text('{"current":{"engine":"office"}}', encoding='utf-8')
            prepare_data_dir()
            self.assertIn('office', target.read_text())
            self.assertIn('WPS', old.read_text())

    def test_new_override_takes_precedence_and_skips_old_appdata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / 'Office2PDF' / 'pdf_pro_config_v4.json'
            old.parent.mkdir()
            old.write_text('{}')
            with patch.dict(os.environ, {'APPDATA':folder, 'MATRIXFLOW_DATA_DIR':str(root/'new'), 'OFFICE2PDF_DATA_DIR':str(root/'legacy')}, clear=True), patch('app_paths.sys.executable',str(root/'python.exe')), patch('app_paths.Path.cwd',return_value=root):
                self.assertEqual(prepare_data_dir(), root/'new')
                self.assertFalse((root/'new'/old.name).exists())

    def test_legacy_override_and_portable_config_remain_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'pdf_pro_config_v4.json'
            source.write_text('{"current":{"engine":"wps"}}')
            with patch.dict(os.environ, {'OFFICE2PDF_DATA_DIR':str(root/'custom')}, clear=True), patch('app_paths.sys.executable',str(root/'MatrixFlowPDF.exe')), patch('app_paths.Path.cwd',return_value=root):
                data = prepare_data_dir()
                self.assertEqual(data,root/'custom')
                self.assertEqual((data/source.name).read_bytes(),source.read_bytes())
