"""Deployment check while the SSH database tunnel is deliberately unavailable."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from . import store
root=Path(__file__).resolve().parents[1]
cfg=store.config(root/'.private/robot.json')
refs=store.gallery(cfg['local_dsn'])
assert refs, 'Local gallery missing'
try:store.sync(cfg['local_dsn'],cfg['base_dsn'])
except Exception:pass
else:raise AssertionError('Base still reachable; offline test invalid')
test_id='deployment-test-'+uuid.uuid4().hex
store.record(cfg['local_dsn'],test_id,datetime.now(timezone.utc),{'synthetic':True,'purpose':'offline_queue_verification','people':[]})
with store.connect(cfg['local_dsn']) as db:
 pending=db.execute('SELECT count(*) FROM observations WHERE robot_id=%s AND NOT uploaded',(test_id,)).fetchone()[0]
assert pending==1
(root/'.private/offline-test-id.txt').write_text(test_id)
print(json.dumps({'base_unreachable':True,'local_references':len(refs),'queued_test_events':pending,'test_id':test_id}))
