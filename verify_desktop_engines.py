"""Run real Office/WPS exports through the new UI-independent service."""
import tempfile
import time
from pathlib import Path
from desktop_service import ConversionService
from pypdf import PdfReader

fixtures=Path(__file__).parent/'test_artifacts'
for engine in ('wps','office'):
    with tempfile.TemporaryDirectory() as folder:
        service=ConversionService(Path(folder)/'settings')
        service.add([str(fixtures/f'sample.{ext}') for ext in ('docx','xlsx','pptx')])
        service.start({'engine':engine,'auto_open':False,'out_mode':'custom','output_dir':folder,
                       'naming_tpl':'{name}_{seq}', 'excel_fit':True})
        deadline=time.monotonic()+90
        while service.processing and time.monotonic()<deadline: time.sleep(.1)
        assert not service.processing, f'{engine} timed out'
        assert all(f['status']=='success' for f in service.files), service.snapshot()['logs']
        assert len(list(Path(folder).glob('*.pdf')))==3
        assert all(len(PdfReader(p).pages)>0 for p in Path(folder).glob('*.pdf'))
        print(f'PASS {engine}: Word, Excel and PowerPoint exports through desktop service',flush=True)
