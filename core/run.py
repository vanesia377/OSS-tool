"""Subprocess isolation, deadlines, persistent evidence and input/version cache."""
import argparse, hashlib, json, os, subprocess, sys, time, uuid, selectors, signal
from pathlib import Path
from core.storage import ROOT, ARTIFACTS, atomic_json, load
from core.checks import versions
from core.models import Result

def fingerprint(claim, params):
    files = sorted((ROOT / 'core').glob('*.py')) + [ROOT / 'uv.lock', ROOT / 'data/generated/ground_truth.json', ROOT / 'data/claims.json']
    h = hashlib.sha256(json.dumps([claim, params, versions()], sort_keys=True).encode())
    for p in files:
        if p.exists(): h.update(p.read_bytes())
    # No secrets included in keys or persisted input.
    for k in ('CH_HOST','CH_PORT','CH_READONLY_USER'):
        h.update(os.getenv(k, '').encode())
    return h.hexdigest()

def redact(text):
    for key, value in os.environ.items():
        if any(x in key.upper() for x in ('KEY','TOKEN','PASSWORD','SECRET')) and len(value) >= 4:
            text = text.replace(value, '[REDACTED]')
    return text

def run(claim, params=None, timeout=60, force=False):
    from core.registry import CLAIMS
    if claim not in CLAIMS: raise ValueError(f'Unknown claim {claim}')
    params = params or {}
    if any(any(s in k.lower() for s in ('key','token','password','secret')) for k in params):
        raise ValueError('Credentials must come from environment, not params')
    key = fingerprint(claim, params)
    cache = ARTIFACTS / 'cache' / f'{key}.json'
    if cache.exists() and not force:
        result = load(cache)
        print('CACHE HIT', flush=True)
        atomic_json(ARTIFACTS / 'results' / f'{claim}.json', result)
        return result
    directory = ARTIFACTS / 'runs' / f'{claim}-{uuid.uuid4().hex}'
    directory.mkdir(parents=True)
    atomic_json(directory / 'params.json', params)
    command = [sys.executable, '-m', 'core.worker', claim, str(directory / 'params.json'), str(directory / 'result.json')]
    started = time.monotonic()
    try:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        raw, pending = b'', b''
        try:
            while selector.get_map():
                if time.monotonic() - started > timeout:
                    raise subprocess.TimeoutExpired(command, timeout, output=raw)
                for event, _ in selector.select(0.1):
                    chunk = os.read(event.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(event.fileobj)
                        continue
                    raw += chunk
                    pending += chunk
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        print(redact(line.decode(errors='replace')), flush=True)
            if pending: print(redact(pending.decode(errors='replace')), flush=True)
            proc.wait(timeout=max(0.1, timeout-(time.monotonic()-started)))
        finally:
            selector.close()
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        log = redact(raw.decode(errors='replace'))
        result = load(directory / 'result.json')
        if proc.returncode or result is None:
            result = Result(claim, 'UNVERIFIED', 'FAILED_TO_RUN: xem lỗi thực trong bằng chứng.',
                evidence=[{'command':f'python -m core.worker {claim}', 'exit_code':proc.returncode, 'output':log[-8000:]}], execution='FAILED_TO_RUN').to_dict()
    except subprocess.TimeoutExpired as e:
        log = redact(str(e.stdout or '') + str(e.stderr or ''))
        result = Result(claim, 'SKIPPED_RESOURCE', f'Quá timeout {timeout}s; chạy lại với --timeout lớn hơn.',
            evidence=[{'command':f'python -m core.run --claim {claim} --timeout {timeout}', 'output':f'TimeoutExpired after {timeout}s; {log[-2000:]}'}], execution='TIMEOUT').to_dict()
    (directory / 'logs.txt').write_text(log)
    result = json.loads(redact(json.dumps(result, ensure_ascii=False)))
    result['duration'] = time.monotonic() - started
    result['logs'] = [str((directory / 'logs.txt').relative_to(ROOT))]
    result['versions'] = {**versions(), **result['versions']}
    result['cache_key'] = key
    result['run_id'] = directory.name
    from datetime import datetime, timezone
    result['at'] = datetime.now(timezone.utc).isoformat()
    atomic_json(directory / 'result.json', result)
    atomic_json(ARTIFACTS / 'results' / f'{claim}.json', result)
    if result['execution'] == 'COMPLETED': atomic_json(cache, result)
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--claim', required=True)
    p.add_argument('--params', default='{}', help='JSON object, never secrets')
    p.add_argument('--timeout', type=int, default=60)
    p.add_argument('--no-cache', action='store_true')
    a = p.parse_args()
    r = run(a.claim, json.loads(a.params), a.timeout, a.no_cache)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(1 if r['execution'] in ('FAILED_TO_RUN','TIMEOUT') or r['status']=='REFUTED' else 0)
