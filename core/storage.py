from pathlib import Path
import json, os, tempfile, fcntl
ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        name = f.name
    os.replace(name, path)

def load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default

def verdict(claim, status, note):
    if status not in ('CONFIRMED','PARTIAL','REFUTED','UNVERIFIED'):
        raise ValueError(status)
    from datetime import datetime, timezone
    path = ARTIFACTS / 'verdicts.json'
    with (ARTIFACTS / 'verdicts.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        values = load(path, {})
        values[claim] = dict(status=status, note=note, at=datetime.now(timezone.utc).isoformat())
        atomic_json(path, values)
