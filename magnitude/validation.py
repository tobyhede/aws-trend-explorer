import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
def holdout():
    pilot={r['url'] for r in json.loads((P/'pilot.json').read_text())}
    rows=[r for i in range(3) for r in json.loads((P/f'batch{i}.json').read_text()) if r['url'] not in pilot]
    return sorted(rows,key=lambda r:hashlib.sha256(('magnitude-independent-v1'+r['url']).encode()).digest())[:80]
if __name__=='__main__':
    for i,r in enumerate(holdout()):print(i,r['title'],'|',r['body'][:850])
