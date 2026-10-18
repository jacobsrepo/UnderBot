"""Enrollment, revocation, local schemas and retrying synchronization."""
import argparse
import json
from pathlib import Path
import time
import cv2
from . import store
from .face import FaceEngine, MODEL

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    sub.add_parser('status')
    s=sub.add_parser('sync');s.add_argument('--once',action='store_true')
    e=sub.add_parser('enroll');e.add_argument('--name',required=True);e.add_argument('--images',nargs='+',required=True);e.add_argument('--person-id');e.add_argument('--consent',action='store_true',required=True);e.add_argument('--models',default='models')
    d=sub.add_parser('revoke');d.add_argument('--person-id',required=True)
    a=p.parse_args();cfg=store.config(a.config);dsn=cfg['local_dsn']
    if a.command=='init':store.initialize(dsn)
    elif a.command=='status':
        with store.connect(dsn) as db:
            print(json.dumps({'people':db.execute('SELECT count(*) FROM people WHERE active').fetchone()[0], 'faces':db.execute('SELECT count(*) FROM faces').fetchone()[0], 'observations':db.execute('SELECT count(*) FROM observations').fetchone()[0], 'pending':db.execute('SELECT count(*) FROM observations WHERE NOT uploaded').fetchone()[0]}))
    elif a.command=='enroll':
        if not cfg.get('authoritative'):raise ValueError('Enroll on the base station authoritative database')
        if not a.name.strip():raise ValueError('Name is required')
        engine=FaceEngine(a.models);vectors=[]
        for file in a.images:
            image=cv2.imread(file)
            if image is None:raise ValueError('Cannot read enrollment image')
            features=engine.features(image)
            if len(features)!=1:raise ValueError('Each image must contain exactly one sufficiently clear face')
            vectors.append(features[0][1].tolist())
        identity=store.enroll(dsn,a.name.strip(),vectors,MODEL,a.person_id)
        print(json.dumps({'person_id':identity,'enrolled_examples':len(vectors),'status':'enrolled_unvalidated'}))
    elif a.command=='revoke':
        if not cfg.get('authoritative'):raise ValueError('Revoke on the authoritative base station')
        store.revoke(dsn,a.person_id)
    elif a.command=='sync':
        while True:
            try:
                print(json.dumps({'uploaded':store.sync(dsn,cfg['base_dsn']),'state':'connected'}),flush=True)
            except Exception:
                print(json.dumps({'state':'offline_retrying'}),flush=True)
                if a.once:raise SystemExit(1)
            try:
                removed=store.prune(dsn)
                if removed:print(json.dumps({'retention_removed':removed}),flush=True)
            except Exception:print('{"state":"local_database_unavailable"}',flush=True)
            if a.once:break
            time.sleep(10)

if __name__=='__main__':main()
