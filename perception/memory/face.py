from pathlib import Path
import hashlib
import cv2
import numpy as np

MODEL = 'opencv-sface-2021dec-128-0ba9fbfa01b5270c'

def unit(vector):
    v=np.asarray(vector,dtype=np.float32).reshape(-1)
    if v.size != 128 or not np.isfinite(v).all() or np.linalg.norm(v)<1e-8:
        raise ValueError('Invalid face embedding')
    return v/np.linalg.norm(v)

def match(vector, gallery, threshold=.5, margin=.08):
    query=unit(vector)
    scores={}
    for pid,name,model,values in gallery:
        if model != MODEL: continue
        score=float(query @ unit(values))
        if pid not in scores or score>scores[pid][0]:scores[pid]=(score,name)
    ranked=sorted(scores.items(),key=lambda x:x[1][0],reverse=True)
    if not ranked:return None
    pid,(score,name)=ranked[0]
    if score<threshold or (len(ranked)>1 and score-ranked[1][1][0]<margin):return None
    return {'person_id':pid,'name':name,'similarity':score}

class FaceEngine:
    def __init__(self, model_dir):
        p=Path(model_dir)
        self.detector=cv2.FaceDetectorYN.create(str(p/'face_detection_yunet_2023mar.onnx'),'',(320,320),.9,.3,100)
        self.recognizer=cv2.FaceRecognizerSF.create(str(p/'face_recognition_sface_2021dec.onnx'),'')
    def features(self,image):
        h,w=image.shape[:2]
        scale=min(1,640/max(h,w))
        small=cv2.resize(image,(round(w*scale),round(h*scale))) if scale<1 else image
        self.detector.setInputSize((small.shape[1],small.shape[0]))
        _,faces=self.detector.detect(small)
        output=[]
        if faces is None:return output
        for face in faces:
            if min(face[2:4])/scale<60:continue
            original=face.copy()
            original[:14]/=scale
            crop=self.recognizer.alignCrop(image,original)
            if cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()<20:continue
            vector=unit(self.recognizer.feature(crop))
            output.append((original[:4].tolist(),vector))
        return output
