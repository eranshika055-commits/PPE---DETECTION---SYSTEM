from flask import Flask, render_template, request, send_from_directory, jsonify
from ultralytics import YOLO
import os
import cv2
import subprocess
import imageio_ffmpeg
from werkzeug.utils import secure_filename


# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "best.pt")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "results")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


# ==========================================
# FLASK APPLICATION
# ==========================================

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER


# ==========================================
# LOAD YOLO MODEL
# ==========================================

print("Loading PPE YOLO model...")

model = YOLO(MODEL_PATH)

print("PPE YOLO model loaded successfully.")


# ==========================================
# PPE CLASSES
# ==========================================

PERSON_CLASS = "person"

PPE_CLASSES = [
    "hard hat",
    "mask",
    "no hard hat",
    "no mask",
    "no safety vest",
    "safety vest"
]


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# IMAGE DETECTION
# ==========================================

@app.route("/detect/image", methods=["POST"])
def detect_image():

    if "image" not in request.files:
        return jsonify({
            "success": False,
            "message": "No image file selected."
        }), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({
            "success": False,
            "message": "No image file selected."
        }), 400

    filename = secure_filename(file.filename)

    input_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(input_path)

    # ==========================================
    # RUN YOLO
    # ==========================================

    results = model(input_path, verbose=False)

    result = results[0]

    # ==========================================
    # SAVE ANNOTATED IMAGE
    # ==========================================

    result_filename = "result_" + filename

    result_path = os.path.join(
        app.config["RESULT_FOLDER"],
        result_filename
    )

    result.save(filename=result_path)

    # ==========================================
    # IMAGE SUMMARY
    # ==========================================

    detected_objects = []

    if result.boxes is not None:

        for box in result.boxes:

            class_id = int(box.cls[0])
            class_name = model.names[class_id]

            if class_name not in detected_objects:
                detected_objects.append(class_name)

    # ==========================================
    # BUILD PPE STATUS
    # ==========================================

    summary = {}

    summary["person"] = (
        "Detected"
        if "person" in detected_objects
        else "Not Detected"
    )

    summary["hard_hat"] = (
        "Detected"
        if "hard hat" in detected_objects
        else "Not Detected"
    )

    summary["mask"] = (
        "Detected"
        if "mask" in detected_objects
        else "Not Detected"
    )

    summary["safety_vest"] = (
        "Detected"
        if "safety vest" in detected_objects
        else "Not Detected"
    )

    summary["no_hard_hat"] = (
        "Detected"
        if "no hard hat" in detected_objects
        else "Not Detected"
    )

    summary["no_mask"] = (
        "Detected"
        if "no mask" in detected_objects
        else "Not Detected"
    )

    summary["no_safety_vest"] = (
        "Detected"
        if "no safety vest" in detected_objects
        else "Not Detected"
    )

    # ==========================================
    # RETURN IMAGE RESULT
    # ==========================================

    return jsonify({
        "success": True,
        "result_url": "/results/" + result_filename,
        "detected_objects": detected_objects,
        "summary": summary
    })


# ==========================================
# SERVE RESULT FILES
# ==========================================

@app.route("/results/<filename>")
def serve_result(filename):

    return send_from_directory(
        app.config["RESULT_FOLDER"],
        filename
    )


# ==========================================
# VIDEO DETECTION
# ==========================================

@app.route("/detect/video", methods=["POST"])
def detect_video():

    # ==========================================
    # CHECK VIDEO
    # ==========================================

    if "video" not in request.files:
        return jsonify({
            "success": False,
            "message": "No video file was uploaded."
        }), 400

    file = request.files["video"]

    if file.filename == "":
        return jsonify({
            "success": False,
            "message": "No video file was selected."
        }), 400

    # ==========================================
    # SAVE UPLOADED VIDEO
    # ==========================================

    original_filename = secure_filename(file.filename)

    input_path = os.path.join(
        UPLOAD_FOLDER,
        original_filename
    )

    file.save(input_path)

    # ==========================================
    # OPEN VIDEO
    # ==========================================

    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        return jsonify({
            "success": False,
            "message": "Could not open the uploaded video."
        }), 500

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 25

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # ==========================================
    # TEMPORARY OUTPUT VIDEO
    # ==========================================

    base_name = os.path.splitext(original_filename)[0]

    temp_filename = "result_" + base_name + "_temp.mp4"

    temp_path = os.path.join(
        RESULT_FOLDER,
        temp_filename
    )

    output_filename = "result_" + base_name + ".mp4"

    output_path = os.path.join(
        RESULT_FOLDER,
        output_filename
    )

    # ==========================================
    # VIDEO WRITER
    # ==========================================

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        temp_path,
        fourcc,
        fps,
        (width, height)
    )

    if not writer.isOpened():
        cap.release()

        return jsonify({
            "success": False,
            "message": "Could not create the output video."
        }), 500

    # ==========================================
    # PERSON DATA
    # ==========================================

    person_data = {}

    # Used if tracker IDs are available
    track_to_person = {}

    next_person_id = 1

    # Used as fallback if a frame does not provide
    # a tracker ID
    previous_persons = []

    # ==========================================
    # CLASS NAMES
    # ==========================================

    PERSON_CLASS = "person"

    PPE_CLASSES = {
        "hard hat",
        "mask",
        "safety vest",
        "no hard hat",
        "no mask",
        "no safety vest"
    }

    # ==========================================
    # HELPER FUNCTIONS
    # ==========================================

    def box_center(box):
        x1, y1, x2, y2 = box

        return (
            (x1 + x2) / 2,
            (y1 + y2) / 2
        )

    def point_inside_box(point, box):

        px, py = point

        x1, y1, x2, y2 = box

        return (
            x1 <= px <= x2
            and
            y1 <= py <= y2
        )

    def calculate_iou(box1, box2):

        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])

        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection_width = max(
            0,
            x2 - x1
        )

        intersection_height = max(
            0,
            y2 - y1
        )

        intersection = (
            intersection_width
            *
            intersection_height
        )

        area1 = max(
            0,
            box1[2] - box1[0]
        ) * max(
            0,
            box1[3] - box1[1]
        )

        area2 = max(
            0,
            box2[2] - box2[0]
        ) * max(
            0,
            box2[3] - box2[1]
        )

        union = area1 + area2 - intersection

        if union <= 0:
            return 0

        return intersection / union

    # ==========================================
    # PROCESS VIDEO FRAME BY FRAME
    # ==========================================

    while True:

        success, frame = cap.read()

        if not success:
            break

        # ======================================
        # YOLO TRACKING
        # ======================================

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        if not results:
            writer.write(frame)
            continue

        result = results[0]

        # ======================================
        # GET DETECTIONS
        # ======================================

        detections = []

        if result.boxes is not None:

            boxes = result.boxes

            for i in range(len(boxes)):

                cls_id = int(
                    boxes.cls[i].item()
                )

                confidence = float(
                    boxes.conf[i].item()
                )

                xyxy = boxes.xyxy[i].tolist()

                class_name = str(
                    model.names[cls_id]
                ).strip().lower()

                track_id = None

                if boxes.id is not None:

                    track_id = int(
                        boxes.id[i].item()
                    )

                detections.append({
                    "class_name": class_name,
                    "confidence": confidence,
                    "box": xyxy,
                    "track_id": track_id
                })

        # ======================================
        # FIND PERSONS
        # ======================================

        persons = []

        for detection in detections:

            if (
                detection["class_name"]
                .strip()
                .lower()
                == PERSON_CLASS
            ):

                persons.append(detection)

    # ======================================
        # ASSIGN PERSON IDs
        # ======================================

        current_persons = []

        used_previous_ids = set()

        for person in persons:

            person_box = person["box"]

            person_center = box_center(
                person_box
            )

            person_id = None

            best_iou = 0

            best_previous = None

            # ----------------------------------
            # MATCH WITH PERSON FROM PREVIOUS FRAME
            # ----------------------------------

            for old_person in previous_persons:

                old_person_id = old_person["person_id"]

                if old_person_id in used_previous_ids:
                    continue

                old_box = old_person["box"]

                iou = calculate_iou(
                    person_box,
                    old_box
                )

                if iou > best_iou:

                    best_iou = iou

                    best_previous = old_person

            # ----------------------------------
            # IF IOU MATCH IS GOOD, KEEP SAME ID
            # ----------------------------------

            if (
                best_previous is not None
                and best_iou >= 0.15
            ):

                person_id = best_previous[
                    "person_id"
                ]

                used_previous_ids.add(
                    person_id
                )

            # ----------------------------------
            # FALLBACK: MATCH BY CENTER DISTANCE
            # ----------------------------------

            else:

                best_distance = float("inf")

                best_previous = None

                for old_person in previous_persons:

                    old_person_id = old_person[
                        "person_id"
                    ]

                    if old_person_id in used_previous_ids:
                        continue

                    old_center = old_person[
                        "center"
                    ]

                    distance = (
                        (
                            person_center[0]
                            -
                            old_center[0]
                        ) ** 2
                        +
                        (
                            person_center[1]
                            -
                            old_center[1]
                        ) ** 2
                    ) ** 0.5

                    max_distance = max(
                        width,
                        height
                    ) * 0.25

                    if (
                        distance < best_distance
                        and
                        distance <= max_distance
                    ):

                        best_distance = distance

                        best_previous = old_person

                if best_previous is not None:

                    person_id = best_previous[
                        "person_id"
                    ]

                    used_previous_ids.add(
                        person_id
                    )

            # ----------------------------------
            # CREATE NEW PERSON ID
            # ----------------------------------

            if person_id is None:

                person_id = next_person_id

                next_person_id += 1

            # ----------------------------------
            # CREATE PERSON DATA
            # ----------------------------------

            if person_id not in person_data:

                person_data[person_id] = {

                    "person_id": person_id,

                    "hard_hat": False,

                    "mask": False,

                    "safety_vest": False,

                    "no_hard_hat": False,

                    "no_mask": False,

                    "no_safety_vest": False
                }

            # ----------------------------------
            # SAVE CURRENT PERSON
            # ----------------------------------

            current_persons.append({

                "person_id": person_id,

                "box": person_box,

                "center": person_center
            })

        # ======================================
        # SAVE CURRENT PERSONS FOR NEXT FRAME
        # ======================================

        previous_persons = current_persons
        # ======================================
        # ASSOCIATE PPE WITH PERSON
        # ======================================

        for detection in detections:

            class_name = detection[
                "class_name"
            ]

            if class_name not in PPE_CLASSES:
                continue

            ppe_box = detection["box"]

            ppe_center = box_center(
                ppe_box
            )

            best_person_id = None

            best_score = 0

            # ----------------------------------
            # FIND THE PERSON THAT OWNS PPE
            # ----------------------------------

            for person in current_persons:

                person_box = person["box"]

                inside = point_inside_box(
                    ppe_center,
                    person_box
                )

                iou = calculate_iou(
                    ppe_box,
                    person_box
                )

                if inside:

                    score = 1.0 + iou

                else:

                    score = iou

                if score > best_score:

                    best_score = score

                    best_person_id = person[
                        "person_id"
                    ]

            # ----------------------------------
            # SAVE PPE FOR PERSON
            # ----------------------------------

            if best_person_id is not None:

                if best_score > 0:

                    if class_name == "hard hat":

                        person_data[
                            best_person_id
                        ]["hard_hat"] = True

                    elif class_name == "mask":

                        person_data[
                            best_person_id
                        ]["mask"] = True

                    elif class_name == "safety vest":

                        person_data[
                            best_person_id
                        ]["safety_vest"] = True

                    elif class_name == "no hard hat":

                        person_data[
                            best_person_id
                        ]["no_hard_hat"] = True

                    elif class_name == "no mask":

                        person_data[
                            best_person_id
                        ]["no_mask"] = True

                    elif class_name == "no safety vest":

                        person_data[
                            best_person_id
                        ]["no_safety_vest"] = True

        # ======================================
        # DRAW YOLO DETECTIONS
        # ======================================

        annotated_frame = result.plot()

        writer.write(annotated_frame)

    # ==========================================
    # RELEASE VIDEO
    # ==========================================

    cap.release()

    writer.release()

    # ==========================================
    # CONVERT VIDEO TO H264 MP4
    # ==========================================

    try:

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg_exe,
            "-y",
            "-i",
            temp_path,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            output_path
        ]

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if os.path.exists(temp_path):

            os.remove(temp_path)

    except Exception as e:

        print("FFmpeg conversion failed:", e)

        # If conversion fails, keep the OpenCV
        # generated video instead
        if os.path.exists(temp_path):

            if os.path.exists(output_path):

                os.remove(output_path)

            os.rename(
                temp_path,
                output_path
            )

    # ==========================================
    # BUILD PERSON SUMMARIES
    # ==========================================

    person_summaries = []

    for person_id in sorted(person_data.keys()):

        data = person_data[person_id]

        person_summary = {

            "person_id": person_id,

            "hard_hat": (
                "Detected"
                if data["hard_hat"]
                else "Not Detected"
            ),

            "mask": (
                "Detected"
                if data["mask"]
                else "Not Detected"
            ),

            "safety_vest": (
                "Detected"
                if data["safety_vest"]
                else "Not Detected"
            ),

            "no_hard_hat": (
                "Detected"
                if data["no_hard_hat"]
                else "Not Detected"
            ),

            "no_mask": (
                "Detected"
                if data["no_mask"]
                else "Not Detected"
            ),

            "no_safety_vest": (
                "Detected"
                if data["no_safety_vest"]
                else "Not Detected"
            )
        }

        person_summaries.append(
            person_summary
        )

    # ==========================================
    # PRINT SUMMARY IN VS CODE
    # ==========================================

    print("\n==========================================")

    print(
        "VIDEO PERSON-WISE PPE SUMMARY"
    )

    print(
        "=========================================="
    )

    print(
        "Total persons:",
        len(person_summaries)
    )

    for person in person_summaries:

        print(
            "Person",
            person["person_id"],
            "| Hard Hat:",
            person["hard_hat"],
            "| Mask:",
            person["mask"],
            "| Safety Vest:",
            person["safety_vest"],
            "| No Hard Hat:",
            person["no_hard_hat"],
            "| No Mask:",
            person["no_mask"],
            "| No Safety Vest:",
            person["no_safety_vest"]
        )

    print(
        "==========================================\n"
    )

    # ==========================================
    # RETURN VIDEO RESULT
    # ==========================================

    return jsonify({

        "success": True,

        "message":
            "PPE detection completed successfully.",

        "result_url":
            "/results/" + output_filename,

        "person_count":
            len(person_summaries),

        "person_summaries":
            person_summaries
    })

# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    print("Starting PPE Safety Detection System...")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )