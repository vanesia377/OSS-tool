import json, sys, time
from core.checks import run, versions
from core.storage import atomic_json

if __name__ == '__main__':
    claim, params_path, output = sys.argv[1:]
    started = time.monotonic()
    print(f'Start {claim}', flush=True)
    result = run(claim, json.load(open(params_path)))
    result.duration = time.monotonic() - started
    result.versions = {**versions(), **result.versions}
    atomic_json(output, result.to_dict())
    print(result.summary, flush=True)
