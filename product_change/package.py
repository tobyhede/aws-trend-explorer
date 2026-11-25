"""Package current data and code with earlier analyses clearly marked as superseded."""
import zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def package():
    root=HERE.parent
    destination=root.parent/'aws_trend_explorer.zip'
    temporary=destination.with_suffix('.building.zip')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        for file in sorted(root.rglob('*')):
            if file.is_file() and not any(p.startswith('.') or p=='__pycache__' for p in file.relative_to(root).parts):
                archive.write(file,file.relative_to(root))
        for source,target in [('historical/README.md','historical-methods.md'),('subtype_validation/README.md','subtype-methods.md')]:
            if not (root/target).is_file():
                archive.write(root.parent/source,target)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        assert all(i.file_size for i in archive.infolist())
        print(len(archive.infolist()),'verified archive members')
    temporary.replace(destination)
if __name__=='__main__':package()
