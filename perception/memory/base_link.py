"""Windows base station -> Pi loopback PostgreSQL tunnel, with reconnect and one-instance lock."""
import argparse
import msvcrt
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--host',default='underbot@100.123.136.69');a=p.parse_args()
 private=ROOT/'.private'
 with (private/'base-link.lock').open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise SystemExit('Base link is already running.')
  command=['ssh','-N','-i',str(private/'pi_access_ed25519'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','-R','127.0.0.1:55433:127.0.0.1:55432','-L','127.0.0.1:11435:127.0.0.1:11434',a.host]
  try:
   while True:
    child=subprocess.Popen(command)
    try:child.wait()
    finally:
     if child.poll() is None:child.terminate();child.wait(timeout=10)
    print('Base link disconnected; reconnecting in 10 seconds.',flush=True)
    time.sleep(10)
  except KeyboardInterrupt:pass
if __name__=='__main__':main()
