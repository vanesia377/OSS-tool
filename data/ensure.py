"""Restart helper: never reset an existing database automatically."""
from core.db import client
from core.storage import ROOT, load
from data.seed import generate, ingest, DDL

if __name__=='__main__':
    c=client(admin=True)
    present=c.query("SELECT name FROM system.tables WHERE database='vf_mock'").result_rows
    if not present:
        if not (ROOT/'data/generated/ground_truth.json').exists(): generate(200000)
        ingest()
    else:
        print('Existing mock tables preserved; validate with core.run --claim P1. Partial loads require explicit investigation.')
