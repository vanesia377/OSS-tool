import importlib.metadata, platform
from core.models import Result
from core.storage import ROOT, load

def versions():
    names = ['clickhouse-connect', 'polars', 'streamlit', 'PyYAML']
    return {'python': platform.python_version(), **{n: importlib.metadata.version(n) for n in names}}

def run(claim, params):
    if claim != 'P1':
        return Result(claim, 'UNVERIFIED', 'Chưa triển khai kiểm chứng claim này trong Pha 1.',
                      evidence=[{'kind':'scope', 'output':'NOT_RUN — Phase 1 scaffolding only'}])
    from core.db import client
    truth = load(ROOT / 'data/generated/ground_truth.json')
    if not truth:
        return Result(claim, 'UNVERIFIED', 'Chưa có seed/ground truth. Chạy python -m data.seed.')
    c = client()
    comparisons, evidence = [], []
    for item in truth['sql_cases']:
        print(f'Running {item["id"]}: {item["sql"]}', flush=True)
        rows = [list(r) for r in c.query(item['sql']).result_rows]
        import json
        rows = json.loads(json.dumps(rows, default=str))
        comparisons.append(dict(id=item['id'], sql=item['sql'], expected=item['expected'], actual=rows,
                                correct=rows == item['expected']))
        evidence.append({'command': item['sql'], 'output': str(rows)[:1800]})
    version = c.query('SELECT version(), currentUser()').result_rows
    evidence.append({'command':'SELECT version(), currentUser()', 'output':str(version)})
    good = all(x['correct'] for x in comparisons)
    return Result(claim, 'CONFIRMED' if good else 'REFUTED',
                  f"{sum(x['correct'] for x in comparisons)}/{len(comparisons)} đối chiếu dữ liệu nền đúng; không xác nhận B1–B14.",
                  evidence=evidence, comparisons=comparisons, execution='COMPLETED',
                  artifacts=['data/generated/ground_truth.json','data/generated/manifest.json'],
                  versions={'clickhouse':version[0][0]})
