"""UI-independent helpers; UI never imports individual tool implementations."""
import json, subprocess, sys
from core.storage import ROOT, ARTIFACTS, load
from core.registry import CLAIMS

def start(claim, params, timeout, force):
    import uuid
    log = ARTIFACTS / f'live-{uuid.uuid4().hex}.log'
    cmd=[sys.executable,'-u','-m','core.run','--claim',claim,'--params',json.dumps(params,ensure_ascii=False),'--timeout',str(timeout)]
    if force: cmd.append('--no-cache')
    with log.open('w') as f:
        proc=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    return proc,log

def results():
    return {k:load(ARTIFACTS/'results'/f'{k}.json',dict(claim=k,status='UNVERIFIED',summary='Chưa chạy',execution='NOT_RUN',evidence=[])) for k in CLAIMS}

def health():
    code="from core.db import client; import json; c=client(); print(json.dumps(c.query('SELECT version(), currentUser()').result_rows))"
    from core.run import redact
    try:
        p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=8)
        return dict(up=p.returncode==0,output=redact((p.stdout+p.stderr)[-1500:]))
    except subprocess.TimeoutExpired:
        return dict(up=False,output='ClickHouse health check timed out after 8s')
