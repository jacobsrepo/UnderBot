import hashlib
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]/'models'
HASHES={'face_detection_yunet_2023mar.onnx':'8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4', 'face_recognition_sface_2021dec.onnx':'0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'}
FILES={
 'face_detection_yunet_2023mar.onnx':'face_detection_yunet',
 'face_recognition_sface_2021dec.onnx':'face_recognition_sface',
}
def main():
 ROOT.mkdir(exist_ok=True)
 for name,folder in FILES.items():
  # Git LFS pointer supplies the exact object hash for integrity checking.
  pointer=urllib.request.urlopen(f'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/{folder}/{name}',timeout=30).read().decode()
  expected=next(line.split('sha256:')[1] for line in pointer.splitlines() if line.startswith('oid sha256:'))
  if expected != HASHES[name]:raise ValueError('Upstream model changed; review before updating the pinned hash')
  target=ROOT/name
  if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
   temp=target.with_suffix('.download')
   urllib.request.urlretrieve(f'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/{folder}/{name}',temp)
   if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise ValueError('Model checksum mismatch')
   temp.replace(target)
  print(name,expected)
if __name__=='__main__':main()
