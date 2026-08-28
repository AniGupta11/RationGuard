import cv2
import os
import numpy as np

FACE_DATA_DIR = "faces"
MODEL_PATH = os.path.join(FACE_DATA_DIR, "face_model.yml")

if not os.path.exists(FACE_DATA_DIR):
    os.makedirs(FACE_DATA_DIR)

recognizer = cv2.face.LBPHFaceRecognizer_create()


class FaceDuplicateError(Exception):
    """Raised when the presented face already exists in the system."""


def delete_user_faces(user_id: int):
    """Remove all stored face images for a user."""
    if not os.path.exists(FACE_DATA_DIR):
        return
    prefix = f"User.{user_id}."
    for image_name in os.listdir(FACE_DATA_DIR):
        if image_name.startswith(prefix):
            try:
                os.remove(os.path.join(FACE_DATA_DIR, image_name))
            except OSError:
                continue


def _can_check_duplicates():
    if not os.path.exists(MODEL_PATH):
        return False
    try:
        recognizer.read(MODEL_PATH)
        return True
    except cv2.error:
        return False


def _is_duplicate_face(face_img, current_user_id, threshold):
    try:
        predicted_id, confidence = recognizer.predict(face_img)
    except cv2.error:
        return False, None, None

    if predicted_id != current_user_id and confidence is not None and confidence < threshold:
        return True, predicted_id, confidence
    return False, predicted_id, confidence


def collect_face_samples(user_id: int, prevent_duplicates: bool = True, duplicate_threshold: float = 55.0):
    cam = cv2.VideoCapture(0)
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    sample_count = 0
    window_title = "Collecting Face Samples - Press Q to quit"
    duplicate_check_ready = prevent_duplicates and _can_check_duplicates()

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            if duplicate_check_ready:
                is_duplicate, existing_id, confidence = _is_duplicate_face(
                    gray[y:y + h, x:x + w],
                    user_id,
                    duplicate_threshold
                )
                if is_duplicate:
                    cam.release()
                    cv2.destroyAllWindows()
                    raise FaceDuplicateError(
                        f"Duplicate face detected. Already registered under User ID {existing_id} "
                        f"(confidence {confidence:.2f})."
                    )

            sample_count += 1
            face_img = gray[y:y + h, x:x + w]
            cv2.imwrite(
                os.path.join(FACE_DATA_DIR, f"User.{user_id}.{sample_count}.jpg"),
                face_img,
            )
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        cv2.imshow(window_title, frame)

        if cv2.waitKey(100) & 0xFF == ord("q"):
            break

        if sample_count >= 30:
            break

    cam.release()
    cv2.destroyAllWindows()


def train_face_model():
    image_files = [
        f for f in os.listdir(FACE_DATA_DIR)
        if f.lower().endswith(".jpg") or f.lower().endswith(".png")
    ]

    if not image_files:
        return False

    faces = []
    ids = []

    for image_name in image_files:
        path = os.path.join(FACE_DATA_DIR, image_name)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        try:
            user_id = int(image_name.split(".")[1])
        except (IndexError, ValueError):
            continue

        faces.append(img)
        ids.append(user_id)

    if not faces:
        return False

    recognizer.train(faces, np.array(ids))
    recognizer.write(MODEL_PATH)
    return True


def recognize_face():
    if not os.path.exists(MODEL_PATH):
        return None

    recognizer.read(MODEL_PATH)
    cam = cv2.VideoCapture(0)
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            user_id, confidence = recognizer.predict(gray[y:y + h, x:x + w])
            cam.release()
            cv2.destroyAllWindows()

            if confidence < 60:
                return user_id
            else:
                return None

        cv2.imshow("Face Login - Press Q to quit", frame)
        if cv2.waitKey(100) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()
    return None
