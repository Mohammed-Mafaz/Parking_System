# # detectors/plate_detector.py
# from ultralytics import YOLO
# import cv2

# # either point at your custom .pt file:
# plate_model = YOLO("detectors\models\license_plate_detector.pt")

# def detect_plate_boxes(frame):
#     """
#     Returns a list of (x1,y1,x2,y2, confidence) for each plate found.
#     """
#     res = plate_model(frame)[0]
#     boxes = []
#     for box in res.boxes:
#         x1,y1,x2,y2 = map(int, box.xyxy[0])
#         conf = float(box.conf[0])
#         boxes.append((x1, y1, x2, y2, conf))
#     return boxes




# # # File: detectors/plate_detector.py
# from ultralytics import YOLO
# import cv2


# # Load your YOLO model trained on license plates
# plate_model = YOLO("yolov8s.pt")  # replace with your actual .pt path


# def detect_plate_boxes(frame, conf_thresh=0.2):
#     """
#     Detect license-plate bounding boxes in the frame.
#     Returns list of (x1, y1, x2, y2, confidence).
#     """
#     res = plate_model(frame)[0]
#     boxes = []
#     for box in res.boxes:
#         conf = float(box.conf[0])
#         if conf < conf_thresh:
#             continue
#         x1, y1, x2, y2 = map(int, box.xyxy[0])
#         boxes.append((x1, y1, x2, y2, conf))
#     return boxes

# detectors/yolo_plate_detector.py
from ultralytics import YOLO
import cv2

plate_model = YOLO("yolov8s.pt")

def detect_plate_bbox(frame, imgsz=640):
    results = plate_model(frame, imgsz=imgsz)[0]
    if not results.boxes:
        return None
    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(
        int,
        best.xyxy[0].cpu().numpy()
    )
    return x1, y1, x2, y2
