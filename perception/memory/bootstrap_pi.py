"""Run on the Pi as its ordinary user; sudo uses the local postgres peer account."""
import getpass
import json
from pathlib import Path
import secrets
import subprocess
from .store import initialize

ROOT=Path(__file__).resolve().parents[1]

def main():
 private=ROOT/'.private';private.mkdir(mode=0o700,exist_ok=True);private.chmod(0o700)
 cfgpath=private/'robot.json'
 if cfgpath.exists():
  initialize(json.loads(cfgpath.read_text())['local_dsn']);print('Existing local memory verified.');return
 password=secrets.token_hex(24)
 # Fixed role/database names, generated hexadecimal password: no user-controlled SQL.
 command=f"CREATE ROLE underbot_app LOGIN PASSWORD '{password}';\nCREATE DATABASE underbot OWNER underbot_app;\n"
 subprocess.run(['sudo','-u','postgres','psql','-v','ON_ERROR_STOP=1'],input=command,text=True,check=True)
 passfile=private/'pgpass'
 passfile.write_text(f'127.0.0.1:5432:underbot:underbot_app:{password}\n');passfile.chmod(0o600)
 cfg={'robot_id':'underbot-pi','local_dsn':f"host=127.0.0.1 port=5432 dbname=underbot user=underbot_app passfile='{passfile}'",'base_dsn':f"host=127.0.0.1 port=55433 dbname=underbot_base user=underbot_sync passfile='{passfile}'",'authoritative':False,'gallery_max_age_hours':168,'threshold':.5,'margin':.08}
 cfgpath.write_text(json.dumps(cfg,indent=2));cfgpath.chmod(0o600)
 initialize(cfg['local_dsn']);print('Local PostgreSQL memory initialized; base sync credential still required.')
if __name__=='__main__':main()
