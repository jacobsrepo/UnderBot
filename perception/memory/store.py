import json
from pathlib import Path
import uuid
import psycopg
from psycopg.types.json import Jsonb

SCHEMA = Path(__file__).with_name('schema.sql').read_text()

def connect(dsn):
    return psycopg.connect(dsn, connect_timeout=3, options='-c statement_timeout=5000')

def initialize(dsn):
    with connect(dsn) as db:
        db.execute(SCHEMA)

def config(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def gallery(dsn, max_age_hours=168, authoritative=False):
    with connect(dsn) as db:
        if not authoritative:
            fresh = db.execute("SELECT value > now() - %s * interval '1 hour' FROM memory_state WHERE key='gallery_sync'", (max_age_hours,)).fetchone()
            if not fresh or not fresh[0]:
                return []
        rows = db.execute('SELECT p.id,p.name,f.model,f.embedding FROM people p JOIN faces f ON p.id=f.person_id WHERE p.active').fetchall()
        return [(str(i), n, m, e) for i,n,m,e in rows]

def enroll(dsn, name, vectors, model, person_id=None):
    identity = uuid.UUID(person_id) if person_id else uuid.uuid4()
    with connect(dsn) as db:
        db.execute('INSERT INTO people(id,name) VALUES(%s,%s) ON CONFLICT(id) DO UPDATE SET name=excluded.name,active=true,updated_at=now()', (identity,name))
        for vector in vectors:
            db.execute('INSERT INTO faces(id,person_id,model,embedding) VALUES(%s,%s,%s,%s)', (uuid.uuid4(),identity,model,vector))
    return str(identity)

def revoke(dsn, person_id):
    with connect(dsn) as db:
        db.execute('DELETE FROM faces WHERE person_id=%s', (person_id,))
        db.execute('UPDATE people SET active=false,updated_at=now() WHERE id=%s', (person_id,))

def record(dsn, robot, captured_at, payload):
    with connect(dsn) as db:
        db.execute('INSERT INTO observations(id,robot_id,captured_at,payload) VALUES(%s,%s,%s,%s)', (uuid.uuid4(),robot,captured_at,Jsonb(payload)))

def sync(local_dsn, base_dsn):
    # Base is the sole authority for enrollment. A complete snapshot propagates deletions.
    with connect(base_dsn) as remote:
        remote.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        people = remote.execute('SELECT id,name,active,updated_at FROM people').fetchall()
        faces = remote.execute('SELECT id,person_id,model,embedding,created_at FROM faces').fetchall()
    with connect(local_dsn) as local:
        local.execute('DELETE FROM faces')
        local.execute('DELETE FROM people')
        for row in people:
            local.execute('INSERT INTO people VALUES(%s,%s,%s,%s)',row)
        for row in faces:
            local.execute('INSERT INTO faces VALUES(%s,%s,%s,%s,%s)',row)
        local.execute("INSERT INTO memory_state VALUES('gallery_sync',now()) ON CONFLICT(key) DO UPDATE SET value=excluded.value")
        pending = local.execute('SELECT id,robot_id,captured_at,payload FROM observations WHERE NOT uploaded ORDER BY created_at LIMIT 250').fetchall()
    # Mark uploaded only after remote commit. UUID conflicts make retries safe.
    with connect(base_dsn) as remote:
        for i,r,t,p in pending:
            remote.execute('INSERT INTO observations(id,robot_id,captured_at,payload,uploaded) VALUES(%s,%s,%s,%s,true) ON CONFLICT(id) DO NOTHING',(i,r,t,Jsonb(p)))
    with connect(local_dsn) as local:
        if pending:
            local.execute('UPDATE observations SET uploaded=true WHERE id=ANY(%s)',([r[0] for r in pending],))
    return len(pending)

def prune(dsn):
    # Explicit bounds: uploaded events 24 h, unuploaded 7 days, total 100k rows.
    with connect(dsn) as db:
        expired=db.execute("DELETE FROM observations WHERE created_at < now()-interval '7 days' OR (uploaded AND created_at < now()-interval '24 hours')").rowcount
        capped=db.execute('DELETE FROM observations WHERE id IN (SELECT id FROM observations ORDER BY created_at DESC OFFSET 100000)').rowcount
    return expired+capped
