"""Validate named photo folders and optionally enroll them atomically."""
import argparse
import json
from pathlib import Path
import uuid
import cv2
import numpy as np
from . import store
from .face import FaceEngine, MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--consent', action='store_true')
    args = parser.parse_args()
    if args.apply and not args.consent:
        parser.error('--apply requires --consent')
    cfg = store.config(args.config)
    if not cfg.get('authoritative'):
        raise ValueError('Use the authoritative database')
    folders = sorted(p for p in Path(args.root).iterdir() if p.is_dir())
    if not folders:
        raise ValueError('No person folders')
    engine = FaceEngine(Path(__file__).resolve().parents[1] / 'models')
    prepared, reports = [], []
    for folder in folders:
        vectors, rejected = [], []
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
        for path in files:
            image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
            features = engine.features(image) if image is not None else []
            if len(features) != 1:
                rejected.append({'file': path.name, 'reason': f'Expected one clear face; found {len(features)}'})
            else:
                vectors.append(features[0][1])
        prepared.append((folder.name, vectors))
        reports.append({'name': folder.name, 'files': len(files), 'usable': len(vectors), 'rejected': rejected})
    if any(not vectors for _, vectors in prepared):
        print(json.dumps({'applied': False, 'reason': 'A folder has no usable face samples', 'people': reports}))
        raise SystemExit(1)
    with store.connect(cfg['local_dsn']) as db:
        # Serialize enrollment jobs, and recheck existing samples inside this transaction.
        db.execute('SELECT pg_advisory_xact_lock(728413)')
        for (name, vectors), report in zip(prepared, reports):
            rows = db.execute('SELECT id,active FROM people WHERE lower(name)=lower(%s)', (name,)).fetchall()
            if len(rows) > 1 or (rows and not rows[0][1]):
                raise ValueError('Ambiguous or revoked person record: ' + name)
            pid = rows[0][0] if rows else uuid.uuid4()
            existing = [np.asarray(row[0], dtype=np.float32) for row in
                        db.execute('SELECT embedding FROM faces WHERE person_id=%s AND model=%s', (pid, MODEL)).fetchall()]
            additions = []
            for vector in vectors:
                if not any(np.allclose(vector, ref, atol=1e-6) for ref in existing + additions):
                    additions.append(vector)
            report.update({'new_person': not bool(rows), 'new_samples': len(additions),
                           'duplicates_skipped': len(vectors) - len(additions),
                           'total_samples': len(existing) + len(additions)})
            if args.apply:
                if not rows:
                    db.execute('INSERT INTO people(id,name) VALUES(%s,%s)', (pid, name))
                for vector in additions:
                    db.execute('INSERT INTO faces(id,person_id,model,embedding) VALUES(%s,%s,%s,%s)',
                               (uuid.uuid4(), pid, MODEL, vector.tolist()))
    print(json.dumps({'applied': args.apply, 'people': reports}))


if __name__ == '__main__':
    main()
