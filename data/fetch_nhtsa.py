"""Fetch public recall flat file; preserve access/failure evidence. No fake fallback."""
import csv, io, json, urllib.request, zipfile, hashlib
from datetime import datetime, timezone
from core.storage import ROOT, atomic_json
URL='https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL.zip'

def main():
    out=ROOT/'data/generated'; out.mkdir(exist_ok=True)
    evidence=dict(url=URL, accessed_at=datetime.now(timezone.utc).isoformat(), source='NHTSA recall flat file', status='UNVERIFIED')
    try:
        req=urllib.request.Request(URL, headers={'User-Agent':'vf-verification-research/0.1'})
        with urllib.request.urlopen(req, timeout=60) as r:
            payload=r.read(100*1024*1024+1)
        if len(payload)>100*1024*1024: raise RuntimeError('File exceeds 100 MiB download cap')
        z=zipfile.ZipFile(io.BytesIO(payload)); member=next(n for n in z.namelist() if n.lower().endswith('.txt'))
        # Official flat recall layout: COMPNAME at index 6, DESC_DEFECT at 19.
        rows=[]
        with z.open(member) as f:
            for row in csv.reader(io.TextIOWrapper(f,encoding='utf-8',errors='replace'), delimiter='\t'):
                if len(row)>20 and 'SUSPENSION' in row[6].upper():
                    rows.append(dict(campaign=row[1], make=row[2], model=row[3], year=row[4], component=row[6], description=row[19]))
        if not rows: raise RuntimeError('No SUSPENSION rows: layout/source must be investigated')
        atomic_json(out/'nhtsa_suspension.json', rows)
        evidence.update(status='DOWNLOADED', filtered_rows=len(rows), sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), excerpt=rows[:2],
                        note='Public records kept separately; synthetic distribution not calibrated in Phase 1. Field layout needs official documentation review.')
    except Exception as e:
        evidence.update(status='UNVERIFIED', error=f'{type(e).__name__}: {e}', retry='python -m data.fetch_nhtsa')
    atomic_json(out/'nhtsa_source.json',evidence)
    print(json.dumps(evidence, ensure_ascii=False,indent=2))
if __name__=='__main__': main()
