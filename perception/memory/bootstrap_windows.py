"""Create an isolated loopback-only UnderBot instance using installed PostgreSQL 18."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import psycopg
from psycopg import sql
from .store import initialize

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.private'
BIN=Path(os.environ.get('UNDERBOT_PG_BIN',r'C:\Program Files\PostgreSQL\18\bin'))

def main():
 PRIVATE.mkdir(exist_ok=True)
 identity=subprocess.check_output(['whoami'],text=True).strip()
 subprocess.run(['icacls',str(PRIVATE),'/inheritance:r','/grant:r',identity+':(OI)(CI)F','SYSTEM:(OI)(CI)F'],check=True,capture_output=True)
 data=PRIVATE/'pgdata'
 credentials=PRIVATE/'postgres-credentials.json'
 if not credentials.exists():
  credentials.write_text(json.dumps({u:secrets.token_hex(24) for u in ['underbot_admin','underbot_base_app','underbot_edge_app','underbot_sync']}))
 passwords=json.loads(credentials.read_text())
 if not (data/'PG_VERSION').exists():
  pw=PRIVATE/'init-password.tmp'
  pw.write_text(passwords['underbot_admin'])
  try:
   subprocess.run([str(BIN/'initdb.exe'),'-D',str(data),'-U','underbot_admin','--pwfile',str(pw),'--auth-host=scram-sha-256','--auth-local=scram-sha-256','--encoding=UTF8','--locale=C'],check=True,capture_output=True)
  finally:pw.unlink(missing_ok=True)
 status=subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(data),'status'],capture_output=True)
 if status.returncode:
  subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(data),'-l',str(PRIVATE/'postgres.log'),'-o','-p 55432 -h 127.0.0.1','-w','start'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 with psycopg.connect(host='127.0.0.1',port=55432,user='underbot_admin',password=passwords['underbot_admin'],dbname='postgres',autocommit=True) as db:
  for user in ['underbot_base_app','underbot_edge_app','underbot_sync']:
   if not db.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(user,)).fetchone():
    db.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(user),sql.Literal(passwords[user])))
  for name,owner in [('underbot_base','underbot_base_app'),('underbot_edge_test','underbot_edge_app')]:
   if not db.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone():
    db.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(name),sql.Identifier(owner)))
 passfile=PRIVATE/'pgpass'
 passfile.write_text('\n'.join(f'127.0.0.1:55432:*:{u}:{p}' for u,p in passwords.items())+'\n')
 def dsn(database,user):return f"host=127.0.0.1 port=55432 dbname={database} user={user} passfile='{passfile.as_posix()}'"
 base=dsn('underbot_base','underbot_base_app');edge=dsn('underbot_edge_test','underbot_edge_app')
 initialize(base);initialize(edge)
 with psycopg.connect(base) as db:
  db.execute('GRANT CONNECT ON DATABASE underbot_base TO underbot_sync')
  db.execute('GRANT USAGE ON SCHEMA public TO underbot_sync')
  db.execute('GRANT SELECT ON people,faces TO underbot_sync')
  db.execute('GRANT INSERT,SELECT ON observations TO underbot_sync')
 for name,cfg in [('base',{'robot_id':'underbot-base','local_dsn':base,'authoritative':True}),('edge-test',{'robot_id':'underbot-pc-test','local_dsn':edge,'base_dsn':dsn('underbot_base','underbot_sync'),'authoritative':False,'gallery_max_age_hours':168,'threshold':.5,'margin':.08})]:
  (PRIVATE/f'{name}.json').write_text(json.dumps(cfg,indent=2))
 print('UnderBot PostgreSQL ready on 127.0.0.1:55432; base and edge-test databases initialized. Credentials are private.')
if __name__=='__main__':main()
