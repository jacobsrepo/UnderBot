"""Read one image from stdin for deployment verification; never saves the image."""
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from .face import FaceEngine, match
from . import store

root=Path(__file__).resolve().parents[1]
cfg=store.config(root/'.private/robot.json')
refs=store.gallery(cfg['local_dsn'])
image=cv2.imdecode(np.frombuffer(sys.stdin.buffer.read(),dtype=np.uint8),cv2.IMREAD_COLOR)
if image is None:raise ValueError('Image could not be decoded')
cv2.setNumThreads(2)
engine=FaceEngine(root/'models')
start=time.monotonic();features=engine.features(image)
results=[match(vector,refs,cfg.get('threshold',.5),cfg.get('margin',.08)) for _,vector in features]
print(json.dumps({'faces':len(features),'matches':results,'inference_seconds':round(time.monotonic()-start,3),'test':'enrollment_image_only_not_independent_accuracy_validation'}))
assert len(results)==1 and results[0] is not None

import os
(root/'.private/ultralytics').mkdir(exist_ok=True)
os.environ['YOLO_CONFIG_DIR']=str(root/'.private/ultralytics')
os.environ['YOLO_AUTOINSTALL']='false'
import torch
from ultralytics import YOLO, settings
settings.update({'sync':False})
torch.set_num_threads(2)
assert torch.version.cuda is None
start=time.monotonic()
result=YOLO(str(root/'models/yolo26n.pt')).predict(image,imgsz=416,device='cpu',conf=.35,verbose=False)[0]
labels=[result.names[int(i)] for i in result.boxes.cls.tolist()]
assert 'person' in labels
assert all(match(vector,[]) is None for _,vector in features)
print(json.dumps({'generic_labels':labels,'empty_gallery_fallback':'person','detection_seconds':round(time.monotonic()-start,3),'torch':torch.__version__}))
