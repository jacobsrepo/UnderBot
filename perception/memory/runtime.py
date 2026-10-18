"""Database work stays off the inference thread; gallery expires even during outages."""
from datetime import datetime, timezone
import queue
import threading
import time
from . import store
from .face import FaceEngine, match

class Recognition:
    def __init__(self, config_path, model_dir):
        self.settings=store.config(config_path)
        self.engine=FaceEngine(model_dir)
        self.references=[]
        self.gallery_loaded=0.0
        self.state='starting'
        self.events=queue.Queue(maxsize=30)
        self.stop=threading.Event()
        self.last_event=0.0
        self.thread=threading.Thread(target=self._work,daemon=True)
        self.thread.start()
    def _work(self):
        refresh=0.0
        while not self.stop.is_set():
            try:
                if time.monotonic()>=refresh:
                    self.references=store.gallery(self.settings['local_dsn'],self.settings.get('gallery_max_age_hours',168),self.settings.get('authoritative',False))
                    self.gallery_loaded=time.monotonic()
                    self.state='ready' if self.references else 'empty_or_expired_gallery'
                    refresh=time.monotonic()+5
                try:event=self.events.get(timeout=.2)
                except queue.Empty:continue
                store.record(self.settings['local_dsn'],self.settings['robot_id'],event[0],event[1])
            except Exception:
                self.state='database_unavailable'
                # Drop queued event on DB failure; never block camera inference or grow RAM.
                self.stop.wait(2)
    def annotate(self, frame, annotated, people, captured_at=None):
        import cv2
        people=[p for p in people if p.get('label') == 'person']
        now=time.monotonic()
        # In-memory references have a short lease; DB freshness is checked at reload.
        refs=self.references if now-self.gallery_loaded<15 else []
        for person in people:
            person['identity']=None
        for (x,y,w,h),vector in (self.engine.features(frame) if refs else []):
            containing=[p for p in people if p['xyxy'][0]<=x+w/2<=p['xyxy'][2] and p['xyxy'][1]<=y+h/2<=p['xyxy'][3]]
            if len(containing)!=1:continue
            identity=match(vector,refs,self.settings.get('threshold',.5),self.settings.get('margin',.08))
            containing[0]['identity']=identity
            if identity:
                cv2.putText(annotated,identity['name'],(int(x),max(20,int(y)-8)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,0),2)
        if now-self.last_event>=2:
            try:
                self.events.put_nowait((captured_at or datetime.now(timezone.utc),{'people':[{'category':'person','identity':p.get('identity')} for p in people], 'recognition_state':self.state}))
            except queue.Full:self.state='event_queue_full'
            self.last_event=now
        return self.state
    def close(self):
        self.stop.set()
        self.thread.join(timeout=1)
