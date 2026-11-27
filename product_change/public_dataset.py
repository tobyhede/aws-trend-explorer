"""Write the public dataset: every record of the release without saved announcement text.

Run after build.py. This selects fields from the database; it replays nothing and classifies nothing.
"""
import shutil
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
RELEASE_DATE = '2026-11-27'
COLLECTION_CUTOFF = '2026-10-28'
FIELDS = ['announcement_date', 'title', 'service', 'release_type', 'enhancement_facets',
          'product_change_level', 'product_change_reason', 'product_change_basis', 'source_url']
NAME = f'aws-announcements-{RELEASE_DATE}.parquet'
PATH = HERE / 'public' / NAME
# Present in the repository only; the release bundle leaves the hosted explorer out.
HOSTED_DATA = HERE.parent / 'hosted' / 'site' / 'data'


def build():
    PATH.parent.mkdir(exist_ok=True)
    with duckdb.connect(str(HERE.parent / 'announcements.duckdb'), read_only=True) as db:
        # Snappy is one of the two codecs the hosted explorer's reader (hyparquet) decodes without extra code.
        db.execute(f"""COPY (select {','.join(FIELDS)} from announcements
            where product_change_level is not null order by announcement_date, source_url)
            TO ? (FORMAT parquet, COMPRESSION snappy,
            KV_METADATA {{release_date: '{RELEASE_DATE}', collection_cutoff: '{COLLECTION_CUTOFF}'}})""", [str(PATH)])
        records = db.execute('select count(*) from read_parquet(?)', [str(PATH)]).fetchone()[0]
    assert records == 22588
    if HOSTED_DATA.parent.is_dir():
        HOSTED_DATA.mkdir(exist_ok=True)
        shutil.copyfile(PATH, HOSTED_DATA / NAME)
    print(f'Wrote {records:,} records without announcement text to {PATH.relative_to(HERE.parent)}')


if __name__ == '__main__':
    build()
