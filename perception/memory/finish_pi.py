"""Finish Pi credential setup without displaying secrets."""
from pathlib import Path
import json
from . import store

def main():
 root=Path(__file__).resolve().parents[1]/'.private'
 cfg=store.config(root/'robot.json')
 passfile=root/'pgpass'
 sync_line=(root/'base-sync.pgpass').read_text().strip()
 lines=[x for x in passfile.read_text().splitlines() if not x.startswith('127.0.0.1:55433:')]
 passfile.write_text('\n'.join(lines+[sync_line])+'\n');passfile.chmod(0o600)
 count=store.sync(cfg['local_dsn'],cfg['base_dsn'])
 refs=store.gallery(cfg['local_dsn'])
 print(json.dumps({'sync':'connected','uploaded':count,'local_face_references':len(refs)}))
if __name__=='__main__':main()
