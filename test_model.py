from ultralytics import YOLO

# Load your trained PPE model
model = YOLO("best.pt")

# Test image
image_path = "test_image.jpg"

# Run detection with a low confidence threshold
results = model(image_path, conf=0.20)

print("\n--- DETECTIONS ---")

for result in results:
    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = model.names[class_id]

        print(f"{class_name}: {confidence:.2f}")