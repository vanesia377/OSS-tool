"""Deterministic synthetic DMS. Ground truth computed in Python, never from SQL."""
import argparse, calendar, hashlib, json, random
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
import polars as pl
from core.storage import ROOT, atomic_json, load
from core.db import client

OUT = ROOT / 'data/generated'
SEED = 20261029
PARTS = [(f'PT{n:012d}', f'{name} {axle} {side}', kind, axle, side)
         for n,(name,kind,axle,side) in enumerate(
             ((name,kind,axle,side) for name,kind in [('Giảm chấn','giam_chan'),('Lò xo','lo_xo'),('Rotuyn','rotuyn'),('Cao su càng','cao_su_cang'),('Thanh cân bằng','thanh_can_bang')]
              for axle in ['trước','sau'] for side in ['trái','phải']), 1)]

def generate(n):
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    dealers = [{'dl_ma':f'DL{i:02}', 'ten_dl':f'Đại lý tổng hợp {i}', 'tinh':'Hà Nội' if i<5 else 'Đà Nẵng'} for i in range(1,11)]
    vehicles = [{'xe_ma':f'XE{i:06}', 'dong_xe':f'VF{[5,6,7,8,9][i%5]}', 'ngay_giao':date(2021,1,1)+timedelta(days=i%730),
                 'cccd':f'001{100000000+i:09}', 'bien_so':f'{30+i%10}A-{i%1000:03}.{i%100:02}',
                 'sdt':f'09{i:08}', 'ho_ten':f'Khách hàng giả {i}'} for i in range(1,40001)]
    master = [dict(zip(['ma_pt','ten_pt','nhom_pt','vi_tri','ben'], p), don_gia=500000+(i%5)*250000) for i,p in enumerate(PARTS)]
    claims, lines, dirty = [], [], []
    monthly, dealer_counts, type_counts, model_counts = Counter(), Counter(), Counter(), Counter()
    sum_cost, sum_km, km_count = 0, 0, 0
    dates = [date(2023,m,1) for m in range(1,13)] + [date(y,m,1) for y in [2024,2025,2026] for m in range(1,13) if date(y,m,1) <= date(2026,10,1)]
    weights = [1.8 if d.month in (6,7,8) else 1 for d in dates]
    for i in range(n):
        month = rng.choices(dates, weights)[0]
        day = month + timedelta(days=rng.randrange(calendar.monthrange(month.year,month.month)[1]))
        v = vehicles[rng.randrange(len(vehicles))]
        dealer = rng.choice(dealers)['dl_ma']
        part = rng.choice(master)
        anomaly = i % 20 == 0
        if anomaly:
            month = date(2026,8,1); day = month + timedelta(days=i%28)
            v = vehicles[(i%8000)*5+2]  # VF8, fixed planted cohort
            dealer = 'DL03'; part = master[2]  # rear left damper
        km = rng.randrange(1000,120000)
        cost = part['don_gia'] + rng.randrange(50,250)*1000
        reasons = ['Giảm chấn chảy dầu','Tieng keu khi qua o ga','Rung lắc hệ thống treo','Cao su bị nứt','Độ ồn bất thường']
        row = dict(row_id=i, ma_yc_bh=f'BH{i:09}', xe_ma=v['xe_ma'], dl_ma=dealer, ngay_bh=day,
                   km_vh=km, chi_phi=cost, mo_ta_loi=reasons[i%5], ma_loi=f'LOI{i%5}',
                   so_hd=f'{700000000000+i:012}', lo_sx='LOT-DAMPER-2026-08' if anomaly else 'LOT-NORMAL')
        quantity = 1
        violations = []
        if i%10007 == 1: row['km_vh']=None; violations.append('km_null')
        if i%10007 == 2: row['km_vh']=-100; violations.append('km_negative')
        if i%10007 == 3: row['chi_phi']=None; violations.append('cost_null')
        if i%10007 == 4: quantity=-1; violations.append('quantity_negative')
        if i%10007 == 5: row['ma_yc_bh']=f'BH{i-1:09}'; violations.append('duplicate_claim')
        if violations: dirty.append({'row_id':i, 'violations':violations})
        claims.append(row)
        lines.append(dict(row_id=i, ma_yc_bh=row['ma_yc_bh'], ma_pt=part['ma_pt'], sl_yc_bh=quantity, don_gia=part['don_gia']))
        monthly[day.strftime('%Y-%m-01')]+=1
        dealer_counts[dealer]+=1; type_counts[part['nhom_pt']]+=1; model_counts[v['dong_xe']]+=1
        sum_cost += row['chi_phi'] or 0
        if row['km_vh'] is not None: sum_km+=row['km_vh']; km_count+=1
    tables = {'dms_claim_raw':claims,'dms_claim_part_raw':lines,'dms_part_master_raw':master,'dms_dealer_raw':dealers,'dms_vehicle_raw':vehicles}
    for name,rows in tables.items(): pl.DataFrame(rows).write_parquet(OUT / f'{name}.parquet')
    cases=[]
    def case(sql, expected, question):
        cases.append(dict(id=f'Q{len(cases)+1:02}', question=question, sql=sql, expected=expected))
    case('SELECT count() FROM dms_claim_raw', [[n]], 'Có bao nhiêu dòng yêu cầu bảo hành?')
    case('SELECT sum(chi_phi) FROM dms_claim_raw', [[sum_cost]], 'Tổng chi phí bảo hành là bao nhiêu?')
    case('SELECT sum(km_vh), count(km_vh) FROM dms_claim_raw', [[sum_km,km_count]], 'Tổng km và số dòng có km?')
    for dl in dealers:
        key=dl['dl_ma']; case(f"SELECT count() FROM dms_claim_raw WHERE dl_ma='{key}'", [[dealer_counts[key]]], f'Đại lý {key} có bao nhiêu yêu cầu?')
    for month in sorted(monthly)[-12:]:
        case(f"SELECT count() FROM dms_claim_raw WHERE toStartOfMonth(ngay_bh)=toDate('{month}')", [[monthly[month]]], f'Tháng {month[:7]} có bao nhiêu yêu cầu?')
    case('SELECT toString(toStartOfMonth(ngay_bh)) AS thang, count() FROM dms_claim_raw GROUP BY thang ORDER BY thang', [[k,v] for k,v in sorted(monthly.items())], 'Số yêu cầu theo tháng?')
    for typ in sorted(type_counts):
        case(f"SELECT count() FROM dms_claim_part_raw p JOIN dms_part_master_raw m USING(ma_pt) WHERE m.nhom_pt='{typ}'", [[type_counts[typ]]], f'Số dòng phụ tùng nhóm {typ}?')
    for model in sorted(model_counts):
        case(f"SELECT count() FROM dms_claim_raw c JOIN dms_vehicle_raw v USING(xe_ma) JOIN dms_dealer_raw d USING(dl_ma) WHERE v.dong_xe='{model}'", [[model_counts[model]]], f'Số yêu cầu dòng xe {model} trên các đại lý hợp lệ?')
    kms=sorted(r['km_vh'] for r in claims if r['km_vh'] is not None)
    case('SELECT quantileExact(0.5)(km_vh) FROM dms_claim_raw', [[kms[len(kms)//2]]], 'Trung vị km vận hành?')
    case('SELECT dl_ma, count() AS n, sum(count()) OVER () AS total FROM dms_claim_raw GROUP BY dl_ma ORDER BY dl_ma', [[k,v,n] for k,v in sorted(dealer_counts.items())], 'Số yêu cầu và tổng toàn hệ thống theo đại lý dùng window?')
    case("SELECT arrayJoin(['trước','sau']) AS vi_tri ORDER BY vi_tri", [['sau'],['trước']], 'Liệt kê hai vị trí treo bằng arrayJoin?')
    mapping = [dict(description=d, column=c, group=g) for d,c,g in [
        ('mã phụ tùng','ma_pt','abbreviation'),('số lượng yêu cầu bảo hành','sl_yc_bh','abbreviation'),('ngày bảo hành','ngay_bh','abbreviation'),('mã đại lý','dl_ma','abbreviation'),('quãng đường vận hành','km_vh','abbreviation'),
        ('mô tả lỗi','mo_ta_loi','vi_accent'),('mo ta loi','mo_ta_loi','vi_no_accent'),('tên phụ tùng','ten_pt','vi_accent'),('ten phu tung','ten_pt','vi_no_accent'),('dòng xe','dong_xe','vi_accent'),('dong xe','dong_xe','vi_no_accent'),('chi phí bảo hành','chi_phi','vi_accent')]]
    truth=dict(seed=SEED, rows=n, as_of='2026-10-29', synthetic=True, pii='All fabricated; not real persons',
               counts={k:len(v) for k,v in tables.items()}, dirty_rows=dirty, mapping=mapping, sql_cases=cases,
               planted_anomaly=dict(lot='LOT-DAMPER-2026-08', dealer='DL03', model='VF8', part=master[2]['ma_pt'], month='2026-08', rows=(n+19)//20),
               aggregates=dict(total_cost=sum_cost, monthly=dict(monthly), dealers=dict(dealer_counts), part_types=dict(type_counts)),
               metric_definitions_note='MTBF and exposure metrics require declared fleet/time exposure assumptions; not inferred as actual reliability.')
    atomic_json(OUT / 'ground_truth.json', truth)
    atomic_json(OUT / 'manifest.json', dict(seed=SEED, rows=n, source='synthetic-only unless nhtsa_source.json says DOWNLOADED',
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.parquet'))}))
    print(f'Generated {n} claims, {len(cases)} SQL cases, {len(dirty)} dirty row labels.', flush=True)

DDL = {
'dms_claim_raw':'row_id UInt64, ma_yc_bh String, xe_ma String, dl_ma String, ngay_bh Date, km_vh Nullable(Int64), chi_phi Nullable(Int64), mo_ta_loi String, ma_loi String, so_hd String, lo_sx String',
'dms_claim_part_raw':'row_id UInt64, ma_yc_bh String, ma_pt String, sl_yc_bh Int64, don_gia Int64',
'dms_part_master_raw':'ma_pt String, ten_pt String, nhom_pt String, vi_tri String, ben String, don_gia Int64',
'dms_dealer_raw':'dl_ma String, ten_dl String, tinh String',
'dms_vehicle_raw':'xe_ma String, dong_xe String, ngay_giao Date, cccd String, bien_so String, sdt String, ho_ten String'}

def ingest():
    c = client(admin=True)
    c.command('CREATE DATABASE IF NOT EXISTS vf_mock')
    for name,ddl in DDL.items():
        # Only dedicated mock tables; explicit --replace prevents accidental data loss.
        c.command(f'CREATE TABLE IF NOT EXISTS vf_mock.{name} ({ddl}) ENGINE=MergeTree ORDER BY tuple()')
        count=c.query(f'SELECT count() FROM vf_mock.{name}').first_row[0]
        if count: raise RuntimeError(f'{name} contains data; refuse to overwrite. Use --replace for dedicated mock tables.')
        frame=pl.read_parquet(OUT / f'{name}.parquet')
        for batch in frame.iter_slices(50000): c.insert_arrow(f'vf_mock.{name}', batch.to_arrow())
        print(f'Loaded {name}: {len(frame)}', flush=True)
    c.command('CREATE USER IF NOT EXISTS vf_reader IDENTIFIED WITH no_password')
    c.command('GRANT SELECT ON vf_mock.* TO vf_reader')
    c.command('ALTER USER vf_reader SETTINGS readonly=1')
    c.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--rows',type=int,default=200000); p.add_argument('--generate-only',action='store_true'); p.add_argument('--replace',action='store_true'); a=p.parse_args()
    if not 200000 <= a.rows <= 1000000: p.error('--rows must be 200000..1000000')
    generate(a.rows)
    if not a.generate_only:
        if a.replace:
            c=client(admin=True)
            for name in DDL: c.command(f'DROP TABLE IF EXISTS vf_mock.{name}')
            c.close()
        ingest()
