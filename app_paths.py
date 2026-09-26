"""Application storage and non-destructive migration from the previous name."""
import os
import shutil
import sys
from pathlib import Path


def prepare_data_dir():
    override = os.environ.get('MATRIXFLOW_DATA_DIR') or os.environ.get('OFFICE2PDF_DATA_DIR')
    appdata = None if override else Path(os.environ.get('APPDATA') or Path.home())
    data = Path(override) if override else appdata / 'MatrixFlowPDF'
    data.mkdir(parents=True, exist_ok=True)
    # Retain the established file/schema name for existing presets and settings.
    filename = 'pdf_pro_config_v4.json'
    target = data / filename
    if not target.exists():
        candidates = [] if override else [appdata / 'Office2PDF' / filename]
        candidates += [Path(sys.executable).parent / filename, Path.cwd() / filename]
        for source in candidates:
            if source.is_file() and source.resolve() != target.resolve():
                shutil.copyfile(source, target)
                break
    return data
