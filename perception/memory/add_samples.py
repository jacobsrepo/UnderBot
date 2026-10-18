"""Append validated face samples to one existing person; original photos are not copied."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from . import store
from .face import FaceEngine, MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--images', nargs='+', required=True)
    parser.add_argument('--consent', action='store_true', required=True)
    parser.add_argument('--models', default='models')
    args = parser.parse_args()
    settings = store.config(args.config)
    if not settings.get('authoritative'):
        raise ValueError('Add enrollment samples only to the authoritative database')
    dsn = settings['local_dsn']
    with store.connect(dsn) as db:
        people = db.execute('SELECT id,name FROM people WHERE active AND lower(name)=lower(%s)',
                            (args.name.strip(),)).fetchall()
        if len(people) != 1:
            raise ValueError('Expected exactly one active existing person; no new identity was created')
        person_id, name = people[0]
        references = [np.asarray(row[0], dtype=np.float32) for row in
                      db.execute('SELECT embedding FROM faces WHERE person_id=%s AND model=%s',
                                 (person_id, MODEL)).fetchall()]
    engine = FaceEngine(args.models)
    additions, report = [], []
    for filename in args.images:
        path = Path(filename)
        image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f'Cannot decode {path.name}; no samples added')
        features = engine.features(image)
        if len(features) != 1:
            raise ValueError(f'{path.name}: expected one sufficiently clear face, got {len(features)}; no samples added')
        vector = features[0][1]
        previous = max((float(vector @ reference) for reference in references), default=None)
        duplicate = any(np.allclose(vector, reference, atol=1e-6) for reference in references + additions)
        if not duplicate:
            additions.append(vector)
        report.append({'file': path.name, 'accepted': not duplicate,
                       'duplicate': duplicate, 'best_previous_similarity': previous})
    if additions:
        store.enroll(dsn, name, [v.tolist() for v in additions], MODEL, str(person_id))
    with store.connect(dsn) as db:
        total = db.execute('SELECT count(*) FROM faces WHERE person_id=%s AND model=%s',
                           (person_id, MODEL)).fetchone()[0]
    print(json.dumps({'name': name, 'added': len(additions), 'total_samples': total,
                      'images': report, 'status': 'enrolled; live accuracy not yet validated'}))


if __name__ == '__main__':
    main()
