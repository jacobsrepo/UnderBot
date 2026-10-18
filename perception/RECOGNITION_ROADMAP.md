# Recognition roadmap

Current YOLO models detect general object categories and human skeleton keypoints.
They do not identify Sam or your particular laboratory equipment.

| Goal | Additional component |
| --- | --- |
| Sam, friends, professor | Separate face detector and embedding matcher; enroll people with their agreement, store a protected gallery, allow deletion, and reject unknown/uncertain matches. Adding identities usually means gallery enrollment, not retraining YOLO. |
| Equipment category or model | Labeled images and fine-tuning a pretrained object detector. Include varied views, lighting, backgrounds, confusing items and negative examples. |
| Exact physical equipment unit | QR/AprilTag asset ID or serial-number OCR; identical units cannot reliably be distinguished from appearance alone. |
| Particular medicine package | Package detection plus printed name/strength OCR, barcode decoding and catalog lookup. Reject mismatches. Appearance alone cannot verify medication contents or a suitable dose; retain human verification. |

Keep camera capture shared, with separate detection, pose, face recognition and OCR
nodes publishing timestamped results. The human pose model does not supply equipment
6D pose or safe grasp points. Those need calibrated depth/geometry and further work.
Nothing in this setup currently enrolls identities or trains custom categories.

## Improve deliberately

1. Begin with 3-5 useful object classes and define success criteria.
2. Collect and annotate representative examples intentionally; recording is off by default.
3. Split train/validation/test by session, location or object instance. Adjacent video
   frames must not leak across splits. Keep a final test set untouched.
4. Fine-tune the pretrained model; inspect per-class precision, recall, mAP and failures.
   Measure false identity matches and unknown rejection separately for face recognition.
5. Test on the deployment hardware for FPS, memory and latency. Train on suitable
   workstation/cloud hardware; benchmark lightweight inference on the Pi.
6. Version dataset, model and configuration; compare a candidate with the previous
   model, keep rollback, and deploy only after evaluation.
7. Review errors, correct labels, collect missing situations, then retrain.

Leaving YOLO running does not automatically teach it new categories or names.
Keep code/configuration in this repository, with versioned datasets and weights stored
separately. Do not commit face galleries, recordings, credentials or personal data.
The dashboard displays results; training and recognition run in separate components.

Sources:
- [OpenCV face detection and recognition](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html)
- [Ultralytics training](https://docs.ultralytics.com/modes/train/)
- [Ultralytics validation](https://docs.ultralytics.com/modes/val/)
- [Pose estimation](https://docs.ultralytics.com/tasks/pose/)
