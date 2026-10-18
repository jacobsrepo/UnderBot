"""Tests use temporary schemas inside the local base and edge-test databases."""
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch
import numpy as np
from psycopg import sql
from memory import store
from memory.face import match, unit, MODEL

class Matching(unittest.TestCase):
 def test_known_unknown_ambiguous(self):
  a=np.eye(128,dtype=np.float32)[0];b=np.eye(128,dtype=np.float32)[1]
  refs=[('a','Test A',MODEL,a.tolist())]
  self.assertEqual(match(a,refs)['person_id'],'a')
  self.assertIsNone(match(b,refs))
  self.assertIsNone(match(a,refs+[('b','Test B',MODEL,a.tolist())]))
  self.assertIsNone(match(a,[('a','Test A','wrong-model',a.tolist())]))
 def test_invalid(self):
  for v in [[0]*128,[1]*127,[float('nan')]*128]:
   with self.assertRaises(ValueError):unit(v)

class Database(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  root=Path(__file__).parent/'.private'
  cls.base=json.loads((root/'base.json').read_text())['local_dsn']
  cls.edge=json.loads((root/'edge-test.json').read_text())['local_dsn']
  cls.schema='test_'+uuid.uuid4().hex
  cls.original=store.connect
  for dsn in [cls.base,cls.edge]:
   with cls.original(dsn) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(cls.schema)))
  def scoped(dsn):
   db=cls.original(dsn)
   db.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(cls.schema)))
   db.commit()
   return db
  cls.patcher=patch.object(store,'connect',side_effect=scoped);cls.patcher.start()
  store.initialize(cls.base);store.initialize(cls.edge)
 @classmethod
 def tearDownClass(cls):
  cls.patcher.stop()
  for dsn in [cls.base,cls.edge]:
   with cls.original(dsn) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(cls.schema)))
 def test_sync_offline_retry_revocation_expiry(self):
  v=np.eye(128,dtype=np.float32)[0].tolist()
  pid=store.enroll(self.base,'Test identity',[v],MODEL)
  self.assertEqual(store.gallery(self.edge),[])
  store.sync(self.edge,self.base)
  self.assertEqual(store.gallery(self.edge)[0][0],pid)
  store.record(self.edge,'test',datetime.now(timezone.utc),{'category':'person'})
  with self.assertRaises(Exception):store.sync(self.edge,'host=127.0.0.1 port=1 dbname=missing')
  self.assertEqual(store.gallery(self.edge)[0][0],pid)
  self.assertEqual(store.sync(self.edge,self.base),1)
  with store.connect(self.edge) as db:db.execute('UPDATE observations SET uploaded=false')
  self.assertEqual(store.sync(self.edge,self.base),1)
  with store.connect(self.base) as db:self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0],1)
  with store.connect(self.edge) as db:db.execute("UPDATE memory_state SET value=now()-interval '8 days'")
  self.assertEqual(store.gallery(self.edge),[])
  store.revoke(self.base,pid);store.sync(self.edge,self.base)
  self.assertEqual(store.gallery(self.edge),[])
  with store.connect(self.edge) as db:db.execute("UPDATE observations SET created_at=now()-interval '8 days'")
  self.assertEqual(store.prune(self.edge),1)

if __name__=='__main__':unittest.main(verbosity=2)
