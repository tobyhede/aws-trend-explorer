"""Select lower-rated rows with language that may indicate a component or topology change."""
from build import bulk,load,P,holdout
import re,json
def screen():
    assigned=bulk()
    excluded=set(load('reader_a.json'))|{r['url'] for r in holdout()}
    words=r'(?:without|no longer|eliminat(?:es?|ing)|remov(?:es?|ing)|replac(?:es?|ing)) (?:the |a |any |need (?:to|for) |having to |requiring |an |separate |additional |your |own |external |dedicated |self.managed |custom |to |for |manag(?:e|ing) |provision(?:ing)? |deploy(?:ing)? |maintain(?:ing)? |build(?:ing)? ){0,12}(?:infrastructure|servers?|proxy|gateway|pipelines?|clusters?|components?|databases?|data stores?|staging|middleware|network appliances?|orchestrator|connectors?)\b'
    rows=[r for i in range(3) for r in load(f'batch{i}.json') if r['url'] not in excluded and assigned[r['url']]['rating'] in ['1','2'] and re.search(words,r['body'],re.I)]
    return rows
if __name__=='__main__':
    rows=screen();(P/'screened.json').write_text(json.dumps(rows));print(len(rows))
