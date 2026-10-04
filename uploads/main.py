from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, flash
from tensorflow.keras.models import Sequential  # type:ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, InputLayer  # type:ignore
from tensorflow.keras.regularizers import l2  # type:ignore
from tensorflow.keras.optimizers import Adam  # type:ignore
from transformers import AutoTokenizer, TFAutoModelForSeq2SeqLM
import cv2
import numpy as np
import mediapipe as mp
import pyttsx3
import time
import random
import re
import threading
import queue
import signal
import sys
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize MediaPipe solutions
mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class SignLanguageModel:
    def __init__(self, model_type, model_weights_path, actions):
        self.model_type = model_type
        self.actions = actions
        self.colors = [tuple(random.randint(0, 255) for _ in range(3)) for _ in range(len(actions))]
        
        # Build the appropriate model based on type
        if model_type == "first_pov":
            self.model = self._build_first_pov_model(len(actions))
        else:
            self.model = self._build_third_pov_model(len(actions))
            
        self.model.load_weights(model_weights_path)
        
    def _build_first_pov_model(self, num_actions):
        """Build the model architecture for first-person view"""
        model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(30, 126)),
            LSTM(64, return_sequences=False),
            Dense(64, activation='relu'),
            Dense(num_actions, activation='softmax')
        ])
        model.compile(optimizer=Adam(learning_rate=0.001), 
                     loss='sparse_categorical_crossentropy', 
                     metrics=['accuracy'])
        return model
        
    def _build_third_pov_model(self, num_actions):
        """Build the model architecture for third-person view"""
        model = Sequential()
        model.add(InputLayer(input_shape=(30, 258)))
        model.add(LSTM(128, return_sequences=True, kernel_regularizer=l2(0.01)))
        model.add(BatchNormalization())
        model.add(Dropout(0.5))
        model.add(LSTM(64, return_sequences=False, kernel_regularizer=l2(0.01)))
        model.add(BatchNormalization())
        model.add(Dropout(0.5))
        model.add(Dense(64, activation='relu', kernel_regularizer=l2(0.01)))
        model.add(Dropout(0.5))
        model.add(Dense(num_actions, activation='softmax'))
        model.compile(
            optimizer=Adam(learning_rate=0.0001),
            loss='categorical_crossentropy',
            metrics=['categorical_accuracy']
        )
        return model
        
    def predict(self, sequence):
        return self.model.predict(np.expand_dims(sequence, axis=0))[0]

class NLUModel:
    def __init__(self, model_path, tokenizer_path):
        self.model = TFAutoModelForSeq2SeqLM.from_pretrained(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        
    def predict_sentence(self, sign_sequence):
        # Remove duplicates while preserving order
        unique_sequence = []
        for word in sign_sequence:
            if not unique_sequence or word != unique_sequence[-1]:
                unique_sequence.append(word)
        sequence_str = ', '.join([f'"{word}"' for word in unique_sequence if word != 'fullstop'])
        inputs = self.tokenizer(sequence_str, return_tensors='tf', padding=True, truncation=True)
        output = self.model.generate(inputs['input_ids'], max_length=50)
        return self.tokenizer.decode(output[0], skip_special_tokens=True)

# Initialize models
first_pov_model = SignLanguageModel(
    "first_pov",
    r"C:\Users\naiyy\OneDrive\Desktop\sign\model_epoch_24.h5",
    np.array(['hello', 'good', 'morning', 'thank you', 'name', 'you', 'I', 'work', 'engineer', 'from', 'okay', 
              'fine', 'mumbai', 'how', 'what', 'who', 'fullstop', 'no'])
)

third_pov_model = SignLanguageModel(
    "third_pov",
    r"C:\Users\naiyy\OneDrive\Desktop\sign\model_epoch_1298.h5",  # Update this path
    np.array(['hello', 'good', 'morning', 'mumbai', 'from', 'you', 'name', 'I', 'no', 'stop', 'fullstop'])
)

nlu_model = NLUModel(
    r"C:\Users\naiyy\OneDrive\Desktop\sign\fine_tuned_t5(3)\fine_tuned_t5(3)",
    r"C:\Users\naiyy\OneDrive\Desktop\sign\fine_tuned_t5(3)\fine_tuned_t5(3)"
)

# Speech queue and worker thread
speech_queue = queue.Queue()
stop_speech_event = threading.Event()

def speech_worker():
    while not stop_speech_event.is_set():
        try:
            text = speech_queue.get(timeout=1.0)
            if text is None:
                break
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            speech_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Speech error: {e}")

speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

# Camera management
camera = None
camera_active = False
current_model = first_pov_model  # Default model
current_hands = mp_hands.Hands(
    static_image_mode=False, 
    max_num_hands=2, 
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5
)
current_pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera

def release_camera():
    global camera
    if camera is not None and camera.isOpened():
        camera.release()
    camera = None

def extract_first_pov_keypoints(results):
    """Extract keypoints for first-person view (hands only)"""
    lh = np.zeros(21 * 3)
    rh = np.zeros(21 * 3)
    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
            hand_label = results.multi_handedness[hand_index].classification[0].label
            hand_array = np.array([[res.x, res.y, res.z] for res in hand_landmarks.landmark]).flatten()
            if hand_label.lower() == "left":
                lh = hand_array
            elif hand_label.lower() == "right":
                rh = hand_array
    return np.concatenate([lh, rh])

def extract_third_pov_keypoints(pose_results, hand_results):
    """Extract keypoints for third-person view (pose + hands)"""
    # Initialize arrays with zeros
    pose = np.zeros(33 * 4)
    lh = np.zeros(21 * 3)
    rh = np.zeros(21 * 3)
    
    # Extract pose keypoints if available
    if pose_results.pose_landmarks:
        pose = np.array([[res.x, res.y, res.z, res.visibility] 
                        for res in pose_results.pose_landmarks.landmark]).flatten()
    
    # Extract hand keypoints if available
    if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
        for hand_index, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
            hand_label = hand_results.multi_handedness[hand_index].classification[0].label
            hand_array = np.array([[res.x, res.y, res.z] for res in hand_landmarks.landmark]).flatten()
            if hand_label.lower() == "left":
                lh = hand_array
            elif hand_label.lower() == "right":
                rh = hand_array
    
    return np.concatenate([pose, lh, rh])

def text_to_speech(text):
    speech_queue.put(text)

def mediapipe_detection(image, hands_model, pose_model=None):
    """Process image with MediaPipe, handling both models"""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    
    # Process hands
    hand_results = hands_model.process(image)
    
    # Process pose if model is provided
    pose_results = None
    if pose_model is not None:
        pose_results = pose_model.process(image)
    
    image.flags.writeable = True
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR), hand_results, pose_results

def draw_landmarks(image, hand_results, pose_results=None):
    """Draw all relevant landmarks based on current model"""
    # Draw hand landmarks
    if hand_results.multi_hand_landmarks:
        for hand_landmarks in hand_results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                image, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(121, 22, 76), thickness=2, circle_radius=4),
                mp_drawing.DrawingSpec(color=(121, 44, 250), thickness=2, circle_radius=2))
    
    # Draw pose landmarks if available
    if pose_results and pose_results.pose_landmarks:
        mp_drawing.draw_landmarks(
            image, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))

def generate_frames():
    global camera_active, current_model, current_hands, current_pose
    
    cap = get_camera()
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    sequence, sentence, predictions = [], [], []
    threshold, cooldown_period = 0.7, 3
    last_prediction_time = 0
    pause_until = 0

    while camera_active and cap.isOpened():
        current_time = time.time()

        if current_time < pause_until:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.putText(frame, "Processing... (5s break)", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            continue

        ret, frame = cap.read()
        if not ret:
            print("Camera not accessible.")
            break

        # Process frame with appropriate models
        if current_model.model_type == "first_pov":
            image, hand_results, _ = mediapipe_detection(frame, current_hands)
            keypoints = extract_first_pov_keypoints(hand_results)
            draw_landmarks(image, hand_results)
        else:
            image, hand_results, pose_results = mediapipe_detection(frame, current_hands, current_pose)
            keypoints = extract_third_pov_keypoints(pose_results, hand_results)
            draw_landmarks(image, hand_results, pose_results)
        
        sequence.append(keypoints)
        sequence = sequence[-30:]

        if len(sequence) == 30:
            res = current_model.predict(sequence)
            predicted_action_idx = np.argmax(res)
            predictions.append(predicted_action_idx)

            if current_time - last_prediction_time > cooldown_period:
                if len(predictions) >= 10 and np.unique(predictions[-10:])[0] == predicted_action_idx and res[predicted_action_idx] > threshold:
                    current_action = current_model.actions[predicted_action_idx]
                    if not sentence or current_action != sentence[-1]:
                        sentence.append(current_action)
                        last_prediction_time = current_time

            if 'fullstop' in sentence:
                structured_sentence = nlu_model.predict_sentence(sentence)
                text_to_speech(structured_sentence)
                pause_until = current_time + 5
                sequence, sentence, predictions = [], [], []
                last_prediction_time = 0

        TOP_BAR_COLOR = (164, 171, 251)
        TEXT_COLOR = (0, 0, 0)
        cv2.rectangle(image, (0, 0), (640, 40), TOP_BAR_COLOR, -1)
        cv2.putText(image, ' '.join(sentence[-5:]), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, TEXT_COLOR, 2)

        _, jpeg = cv2.imencode('.jpg', image)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')


# ... [keep all your existing routes unchanged] ...

@app.route('/')
def landing():
    return render_template("landing.html")

@app.route('/home')
def index():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        return redirect(url_for("index"))
    return render_template("login.html")

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not is_valid_email(email):
            flash("Invalid email address. Please try again.", "email_error")
            return redirect(url_for("signup"))
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "password_error")
        elif not any(char.isupper() for char in password):
            flash("Password must contain at least one uppercase letter.", "password_error")
        elif not any(char.isdigit() for char in password):
            flash("Password must contain at least one number.", "password_error")
        elif not any(char in "@$!%*?&.,;" for char in password):
            flash("Password must contain at least one special character (e.g., @, $, !, etc.).", "password_error")
        else:
            flash("Signup successful! You can now log in.", "success")
            return redirect(url_for("index"))
        return redirect(url_for("signup"))
    return render_template("signup.html")

@app.route('/fpvideo')
def fpvideo():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera', methods=['POST'])
def start_camera():
    global camera_active
    camera_active = True
    return jsonify({'status': 'success'})

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    global camera_active
    camera_active = False
    release_camera()
    return jsonify({'status': 'success'})

@app.route('/set_language', methods=['POST'])
def set_language():
    data = request.json
    language = data.get('language', 'english')
    return jsonify({'status': 'success', 'language': language})

@app.route('/get_translation', methods=['GET'])
def get_translation():
    return jsonify({
        'translation': "Sample translation",
        'language': 'english'
    })

@app.route('/release_camera', methods=['POST'])
def handle_release_camera():
    release_camera()
    return jsonify({'status': 'success'})

@app.route('/switch_model', methods=['POST'])
def switch_model():
    global current_model, current_hands, current_pose
    model_type = request.json.get('model_type', 'first_pov')
    
    if model_type == 'third_pov':
        current_model = third_pov_model
        # Initialize pose estimation for third-person view
        current_pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    else:
        current_model = first_pov_model
        # Release pose estimation resources if switching to first-person view
        if current_pose:
            current_pose.close()
            current_pose = None
    
    return jsonify({
        'status': 'success', 
        'current_model': current_model.model_type,
        'actions': current_model.actions.tolist()
    })

# Signal handler for clean shutdown
def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    global camera_active
    camera_active = False
    stop_speech_event.set()
    speech_queue.put(None)
    release_camera()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    try:
        app.run(debug=True, threaded=True)
    finally:
        print("Cleaning up...")
        stop_speech_event.set()
        speech_queue.put(None)
        speech_thread.join()
        release_camera()
        if current_pose:
            current_pose.close()
        cv2.destroyAllWindows()