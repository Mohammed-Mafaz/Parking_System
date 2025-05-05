# #detectors/yolo_detector.py
# from ultralytics import YOLO
# import cv2

# model = YOLO("yolov8s.pt")  # or yolov8n/yolov8m as you need

# def detect_vehicles(frame):
#     """
#     Returns list of (x1,y1,x2,y2, class_name, confidence)
#     for each car/truck/bus detected.
#     """
#     result = model(frame)[0]
#     dets = []
#     for box in result.boxes:
#         cls = int(box.cls)
#         name = model.names[cls]
#         if name in ("car","truck","bus"):
#             x1,y1,x2,y2 = map(int, box.xyxy[0])
#             conf = float(box.conf[0])
#             dets.append((x1,y1,x2,y2, name, conf))
#     return dets

# detectors/yolo_plate_detector.py
from ultralytics import YOLO
import cv2

# Load model specialized for license plates if available
# You can fine-tune a YOLOv8 model on license plate data for best results.
plate_model = YOLO("yolov8s.pt")  # or path to a plate-specific weights file

# Helper: detect only the highest-confidence plate bounding box
def detect_plate_bbox(frame, imgsz=640):
    """
    Runs YOLOv8 on the frame to find license plate bounding box.
    Returns (x1,y1,x2,y2) or None if no plate found.
    """
        # Skip zero-sized inputs
    if frame is None or frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
        return []

    # Resize detection for speed/accuracy tradeoff
    results = plate_model(frame, imgsz=imgsz)[0]
    if not results.boxes:
        return None
    # pick the box with highest confidence
    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0].cpu().numpy())
    return x1, y1, x2, y2