"""Construct and freeze reference judgments without opening production predictions."""
import csv
import hashlib
import json
from pathlib import Path
from score import readings, LEVELS

HERE=Path(__file__).resolve().parent

def freeze():
    plan=json.loads((HERE/'adjudication_plan.json').read_text())
    for name,digest in plan['freeze_hashes'].items():
        assert hashlib.sha256((HERE/'blind'/name).read_bytes()).hexdigest()==digest
    a,b=readings('reader_a.tsv'),readings('reader_b.tsv')
    third=list(csv.reader((HERE/'blind/reader_c.tsv').open(),delimiter='\t'))
    assert [int(r[0]) for r in third]==plan['third_indices']
    assert all(len(r)==4 and r[1] in LEVELS and r[3] in ['high','medium','low'] for r in third)
    adjudicated=json.loads((HERE/'blind/adjudicated.json').read_text())
    assert {int(i) for i in adjudicated}==set(plan['third_indices'])
    result=[]
    for i in range(200):
        if str(i) in adjudicated:
            r=adjudicated[str(i)]
            assert r['level'] in LEVELS and r['confidence'] in ['high','medium','low'] and len(r['reason'])>12
            result.append({'index':i,'level':r['level'],'reason':r['reason'],'confidence':r['confidence'],'basis':'Third-reader adjudication after independent source reading'})
        else:
            assert a[i]['level']==b[i]['level'] and 'low' not in [a[i]['confidence'],b[i]['confidence']]
            confidence='high' if a[i]['confidence']==b[i]['confidence']=='high' else 'medium'
            result.append({'index':i,'level':a[i]['level'],'reason':a[i]['reason']+' Second reader: '+b[i]['reason'],'confidence':confidence,'basis':'Two independent source readers agreed'})
    content=json.dumps(result,indent=2)
    file=HERE/'blind/reference.json'
    if file.exists():assert file.read_text()==content,'Frozen reference differs; do not overwrite after scoring'
    else:file.write_text(content)
    manifest={'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'reference_records':200,'readers_blinded_to_production':True,'inputs':{name:hashlib.sha256((HERE/'blind'/name).read_bytes()).hexdigest() for name in ['reader_a.tsv','reader_b.tsv','reader_c.tsv','adjudicated.json','sample.json']}}
    output=HERE/'reference_freeze.json'
    text=json.dumps(manifest,indent=2)
    if output.exists():assert output.read_text()==text
    else:output.write_text(text)
    print('Frozen 200 reference labels without opening production predictions: '+manifest['sha256'])

if __name__=='__main__':freeze()
