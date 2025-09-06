# app.py
from flask import Flask, Response, jsonify, send_file
from flask import request, send_from_directory
import mysql.connector
import csv
import os
from HelmetDetector import HelmetDetector



app = Flask(__name__, static_url_path='/static', static_folder='static')

# --- CONFIG ---
DB_CFG = dict(
    host="localhost",
    user="root",
    password="0000",
    database="BikeMonitoring"
)

VIDEO_PATH = "Media/test2.mp4"
TESSERACT_CMD = None  # e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ---------------

detector = HelmetDetector(
    video_path=VIDEO_PATH,
    helmet_weights="Weights/BikeFaceHelmet/best.pt",
    plate_weights="Weights/NoPlate1/best.pt",
    snaps_dir="Snaps",
    save_video=True,
    out_video_path="output/processed.mp4",
    db_cfg=DB_CFG,
    tesseract_cmd=TESSERACT_CMD
)

@app.route("/")
def index():
    # Serve the HTML page
    return send_from_directory("templates", "index.html")

@app.route("/video_feed")
def video_feed():
    return Response(detector.frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/plates")
def api_plates():
    """
    Returns latest plate rows as JSON for the table.
    Query params:
      - limit (int, default 50)
      - q (optional text search in plate_text)
    """
    limit = int(request.args.get("limit", 50))
    q = request.args.get("q", "").strip()

    db = mysql.connector.connect(**DB_CFG)
    cur = db.cursor(dictionary=True)

    if q:
        cur.execute(
            """
            SELECT id, frame_number, plate_text, plate_image_path, detected_at
            FROM Plates
            WHERE plate_text LIKE %s
            ORDER BY detected_at DESC
            LIMIT %s
            """,
            (f"%{q}%", limit)
        )
    else:
        cur.execute(
            """
            SELECT id, frame_number, plate_text, plate_image_path, detected_at
            FROM Plates
            ORDER BY detected_at DESC
            LIMIT %s
            """,
            (limit,)
        )

    rows = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(rows)

@app.route("/download")
def download_csv():
    """Download the current latest table as CSV."""
    limit = int(request.args.get("limit", 500))
    q = request.args.get("q", "").strip()

    db = mysql.connector.connect(**DB_CFG)
    cur = db.cursor()

    if q:
        cur.execute(
            """
            SELECT id, frame_number, plate_text, plate_image_path, detected_at
            FROM Plates
            WHERE plate_text LIKE %s
            ORDER BY detected_at DESC
            LIMIT %s
            """,
            (f"%{q}%", limit)
        )
    else:
        cur.execute(
            """
            SELECT id, frame_number, plate_text, plate_image_path, detected_at
            FROM Plates
            ORDER BY detected_at DESC
            LIMIT %s
            """,
            (limit,)
        )

    out_path = "output/plates_export.csv"
    os.makedirs("output", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "frame_number", "plate_text", "plate_image_path", "detected_at"])
        for row in cur.fetchall():
            w.writerow(row)

    cur.close()
    db.close()

    return send_file(out_path, as_attachment=True, download_name="plates_export.csv")

@app.route("/snaps/<path:filename>")
def serve_snaps(filename):
    return send_from_directory("Snaps", filename)


#############charts#################
@app.route("/api/stats")
def api_stats():
    """
    Returns aggregated statistics:
      - bar: counts per day
      - pie: top 5 plates with most violations
    """
    db = mysql.connector.connect(**DB_CFG)
    cur = db.cursor(dictionary=True)

    # --- Bar chart: group by date ---
    cur.execute("""
        SELECT DATE(detected_at) as d, COUNT(*) as c
        FROM Plates
        GROUP BY DATE(detected_at)
        ORDER BY d ASC
    """)
    bar_data = cur.fetchall()

    # --- Pie chart: group by plate_text (top 5 violators) ---
    cur.execute("""
        SELECT plate_text as label, COUNT(*) as c
        FROM Plates
        GROUP BY plate_text
        ORDER BY c DESC
        LIMIT 5
    """)
    pie_data = cur.fetchall()

    cur.close()
    db.close()

    return jsonify({"bar": bar_data, "pie": pie_data})

########################################################

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
    finally:
        detector.release()
