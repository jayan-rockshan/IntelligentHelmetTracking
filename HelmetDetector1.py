import os
import re
import cv2
import cvzone
import pytesseract
import mysql.connector
from ultralytics import YOLO
from threading import Lock
from datetime import datetime

# -----------------------------
# Plate cleanup + validation
# -----------------------------
def clean_plate_text(text):
    """Normalize OCR text and validate as SL/IN number plate."""
    if not text:
        return None

    # Normalize
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)  # keep only letters/numbers

    # ---- Sri Lanka ----
    # Old format (2 letters + 4 digits, e.g., WP1234)
    if re.match(r"^[A-Z]{2}\d{4}$", text):
        return text

    # New format (3 letters + 4 digits, e.g., ABC1234)
    if re.match(r"^[A-Z]{3}\d{4}$", text):
        return text

    # ---- India ----
    # Format: 2 letters (state) + 1–2 digits (RTO) + 1–2 letters (series) + 1–4 digits (number)
    if re.match(r"^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4}$", text):
        return text

    return None


class HelmetDetector:
    def __init__(
        self,
        video_path="Media/test2.mp4",
        helmet_weights="Weights/BikeFaceHelmet/best.pt",
        plate_weights="Weights/NoPlate1/best.pt",
        snaps_dir="Snaps",
        save_video=True,
        out_video_path="output/processed.mp4",
        db_cfg=None,
        tesseract_cmd=None  # e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        self.helmet_model = YOLO(helmet_weights)      # face/helmet/rider
        self.plate_model  = YOLO(plate_weights)       # plate model
        self.classNames = ['face', 'helmet', 'rider']

        self.frame_count = 0
        self.lock = Lock()

        os.makedirs(snaps_dir, exist_ok=True)
        self.snaps_dir = snaps_dir
        os.makedirs("logs", exist_ok=True)  # For rejected OCR text

        # Optional MP4 writer
        self.save_video = save_video
        self.writer = None
        self.out_video_path = out_video_path
        if self.save_video:
            os.makedirs(os.path.dirname(out_video_path), exist_ok=True)

        # DB connection
        self.db = None
        self.cursor = None
        if db_cfg:
            self.db = mysql.connector.connect(**db_cfg)
            self.cursor = self.db.cursor()

        # Tesseract location (Windows)
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _init_writer_if_needed(self, frame):
        if self.writer is not None or not self.save_video:
            return
        h, w = frame.shape[:2]
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.out_video_path, fourcc, fps, (w, h))

    def _insert_plate(self, frame_number, plate_text, plate_image_path):
        if not self.cursor:
            return
        sql = """
            INSERT INTO Plates (frame_number, plate_text, plate_image_path, detected_at)
            VALUES (%s, %s, %s, %s)
        """
        val = (frame_number, plate_text, plate_image_path, datetime.now())
        self.cursor.execute(sql, val)
        self.db.commit()

    def frames(self):
        """
        Generator that yields processed JPEG frames for MJPEG streaming.
        It also writes to DB and (optionally) to MP4.
        """
        while True:
            with self.lock:
                success, img = self.cap.read()
            if not success:
                break

            self.frame_count += 1

            # Run helmet/face/rider model
            results = self.helmet_model(img, stream=True)

            faces, helmets, riders = [], [], []

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    conf = round(float(box.conf[0]), 2)

                    cvzone.cornerRect(img, (x1, y1, x2-x1, y2-y1))
                    cvzone.putTextRect(img, f'{self.classNames[cls]} {conf}', (max(0,x1), max(35,y1)),
                                       scale=1, thickness=1)

                    if self.classNames[cls] == "face":
                        faces.append((x1,y1,x2,y2))
                    elif self.classNames[cls] == "helmet":
                        helmets.append((x1,y1,x2,y2))
                    elif self.classNames[cls] == "rider":
                        riders.append((x1,y1,x2,y2))

            # Riders with face visible and NO helmet
            for rx1, ry1, rx2, ry2 in riders:
                rider_has_face = any(fx1>=rx1 and fy1>=ry1 and fx2<=rx2 and fy2<=ry2 for fx1,fy1,fx2,fy2 in faces)
                rider_has_helmet = any(hx1>=rx1 and hy1>=ry1 and hx2<=rx2 and hy2<=ry2 for hx1,hy1,hx2,hy2 in helmets)

                if rider_has_face and not rider_has_helmet:
                    rider_crop = img[ry1:ry2, rx1:rx2]
                    if rider_crop.size == 0:
                        continue

                    plate_results = self.plate_model(rider_crop, imgsz=640, conf=0.2, stream=True)

                    for pr in plate_results:
                        for pbox in pr.boxes:
                            px1, py1, px2, py2 = map(int, pbox.xyxy[0])
                            plate_crop = rider_crop[py1:py2, px1:px2]
                            if plate_crop.size == 0:
                                continue

                            # Save crop
                            filename = os.path.join(self.snaps_dir, f"plate_{self.frame_count}.jpg")
                            cv2.imwrite(filename, plate_crop)

                            # OCR
                            plate_gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                            raw_text = pytesseract.image_to_string(plate_gray, config='--psm 7').strip()
                            text = clean_plate_text(raw_text)

                            if text:
                                # Save to DB
                                self._insert_plate(self.frame_count, text, filename)

                                # Draw OCR on main frame
                                cvzone.cornerRect(img, (rx1+px1, ry1+py1, (px2-px1), (py2-py1)))
                                cvzone.putTextRect(img, f'{text}', (rx1+px1, max(35, ry1+py1)),
                                                   scale=1, thickness=1)
                            else:
                                # Log rejected OCR text for debugging
                                with open("logs/rejected.txt", "a", encoding="utf-8") as f:
                                    f.write(f"Frame {self.frame_count}: {raw_text}\n")

            # Initialize video writer lazily and write
            self._init_writer_if_needed(img)
            if self.writer:
                self.writer.write(img)

            # Encode frame for MJPEG stream
            ret, buffer = cv2.imencode('.jpg', img)
            if not ret:
                continue
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    def release(self):
        with self.lock:
            if self.cap:
                self.cap.release()
            if self.writer:
                self.writer.release()
            if self.cursor:
                self.cursor.close()
            if self.db:
                self.db.close()
