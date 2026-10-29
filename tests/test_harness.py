import json, os
from dataclasses import asdict
import pytest
from core.models import Result
from core.storage import ROOT, load
from core.run import fingerprint, redact

def test_non_unverified_requires_evidence():
    with pytest.raises(ValueError): Result('B1','CONFIRMED','unsupported').to_dict()

def test_scope_does_not_invent_tool_result():
    from core.checks import run
    result=run('B5',{})
    assert result.status=='UNVERIFIED' and result.execution=='NOT_RUN'
    assert not result.comparisons

def test_cache_separates_inputs():
    assert fingerprint('B5',{'few_shot':True}) != fingerprint('B5',{'few_shot':False})

def test_credentials_redacted(monkeypatch):
    monkeypatch.setenv('TEST_API_KEY','secret-test-value')
    assert redact('error secret-test-value')=='error [REDACTED]'

def test_ground_truth_has_known_dirt_and_benchmark_coverage():
    gt=load(ROOT/'data/generated/ground_truth.json')
    assert len(gt['sql_cases'])>=30
    assert {v for r in gt['dirty_rows'] for v in r['violations']} == {'km_null','km_negative','cost_null','quantity_negative','duplicate_claim'}
    assert len({r['row_id'] for r in gt['dirty_rows']})==len(gt['dirty_rows'])
    assert all(c['expected'] is not None for c in gt['sql_cases'])

@pytest.mark.skipif(os.getenv('CH_TEST')!='1',reason='Set CH_TEST=1 for live ClickHouse integration')
def test_true_ground_truth_and_tampered_oracle(monkeypatch):
    import core.checks as checks
    truth=load(ROOT/'data/generated/ground_truth.json')
    good=checks.run('P1',{})
    assert good.status=='CONFIRMED' and len(good.comparisons)==39
    truth['sql_cases'][0]['expected']=[[-1]]
    monkeypatch.setattr(checks,'load',lambda path: truth)
    bad=checks.run('P1',{})
    assert bad.status=='REFUTED'
    assert bad.comparisons[0]['actual']==[[200000]]
    assert bad.comparisons[0]['correct'] is False

@pytest.mark.skipif(os.getenv('CH_TEST')!='1',reason='Set CH_TEST=1 for live ClickHouse integration')
def test_reader_and_anomaly():
    from core.db import client
    c=client()
    assert c.query('SELECT currentUser()').first_row[0]=='vf_reader'
    # Read-only setting and grant are infrastructure prerequisites, not full B12.
    assert c.query("SELECT value FROM system.settings WHERE name='readonly'").first_row[0]=='1'
    assert c.query("SELECT count(), uniqExact(dl_ma), uniqExact(v.dong_xe), any(v.dong_xe) FROM dms_claim_raw c JOIN dms_vehicle_raw v USING(xe_ma) WHERE lo_sx='LOT-DAMPER-2026-08'").first_row==(10000,1,1,'VF8')
