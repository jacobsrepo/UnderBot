"""Fixed read-only memory lookup; run with the perception Python environment."""
import json
from pathlib import Path
import sys


def snapshot(config_path):
    import psycopg
    config = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    with psycopg.connect(config['local_dsn'], connect_timeout=3,
                        options='-c statement_timeout=3000 -c default_transaction_read_only=on') as db:
        if not config.get('authoritative', False):
            row = db.execute("SELECT value > now() - interval '7 days' FROM memory_state WHERE key='gallery_sync'").fetchone()
            if not row or not row[0]:
                return {'available': False, 'reason': 'Robot gallery is stale; synchronize it first.'}
        rows = db.execute('SELECT name FROM people WHERE active ORDER BY name LIMIT 101').fetchall()
        return {'available': True, 'source': 'PostgreSQL enrolled people',
                'people': [r[0] for r in rows[:100]], 'truncated': len(rows) > 100}


if __name__ == '__main__':
    try:
        result = snapshot(sys.argv[1])
    except Exception as exc:
        # Do not expose DSNs, passwords, or raw database error messages.
        result = {'available': False, 'reason': 'PostgreSQL memory is unavailable.',
                  'error_code': type(exc).__name__}
    print(json.dumps(result))
