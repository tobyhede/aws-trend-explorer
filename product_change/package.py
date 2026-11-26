"""Package current data and code with earlier analyses clearly marked as superseded.

The release bundle includes the public dataset and the explorer page (hosted/site/), which serve.py serves.
It leaves out the rest of hosted/: the publishing and checking scripts.
"""
import zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def package():
    root=HERE.parent
    destination=root.parent/'aws_trend_explorer.zip'
    temporary=destination.with_suffix('.building.zip')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        for file in sorted(root.rglob('*')):
            parts=file.relative_to(root).parts
            if file.is_file() and (parts[0]!='hosted' or parts[:2]==('hosted','site')) and not any(p.startswith('.') or p=='__pycache__' for p in parts):
                archive.write(file,file.relative_to(root))
        for source,target in [('historical/README.md','historical-methods.md'),('subtype_validation/README.md','subtype-methods.md')]:
            if not (root/target).is_file():
                archive.write(root.parent/source,target)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        assert all(i.file_size for i in archive.infolist())
        names=archive.namelist()
        assert not any(n.startswith('hosted/') and not n.startswith('hosted/site/') for n in names)
        assert 'hosted/site/index.html' in names and 'hosted/site/app.js' in names
        assert len([n for n in names if n.startswith('product_change/public/') and n.endswith('.parquet')])==1
        print(len(archive.infolist()),'verified archive members')
    temporary.replace(destination)
if __name__=='__main__':package()
