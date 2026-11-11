from pathlib import Path
from collections import Counter
import hashlib,json
import pandas as pd
B=Path(__file__).resolve().parents[1]
for line in (B/'MANIFEST.sha256').read_text(encoding='utf-8').splitlines():
    h,p=line.split('  ',1)
    assert hashlib.sha256((B/p).read_bytes()).hexdigest()==h,p
c=pd.read_csv(B/'data/processed/cleaned_events_100_students.csv')
a=pd.read_csv(B/'data/analysis/junyi_interaction_seeds_7500.csv')
s=json.loads((B/'data/derived/students_100_junyi.json').read_text(encoding='utf-8'))
g=json.loads((B/'data/derived/knowledge_graph_junyi.json').read_text(encoding='utf-8'))
m=pd.read_csv(B/'data/derived/initial_mastery_long.csv')
assert len(a)==7500 and len(s)==100 and len(g['nodes'])==18 and len(m)==1800
assert c.source_row_1based.is_unique
assert c.is_correct.isin([0,1]).all() and a.is_correct.isin([0,1]).all()
assert m.initial_mastery.between(.05,.98).all()
assert set(a.student_id)<=set(c.student_id)=={x['id'] for x in s}
ck=Counter(zip(c.uuid,c.ucid,c.is_correct,c.total_sec_taken))
ak=Counter(zip(a.junyi_uuid,a.ucid,a.is_correct,a.total_sec_taken))
assert not (ak-ck)
mapping={x['_junyi_uuid']:x['id'] for x in s}
assert all(mapping[u]==i for u,i in zip(a.junyi_uuid,a.student_id))
assert a.is_correct.sum()==5146
print('PASS: hashes, row counts, IDs, codes, ranges, and seed-to-source links')
