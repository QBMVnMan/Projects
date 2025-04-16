#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import copy
import argparse
import itertools
import multiprocessing
import subprocess
import sys
from collections import Counter
from collections import deque

from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

import cv2
import cv2 as cv
import numpy as np
import mediapipe as mp
import time
import multiprocessing as mtp

from hand_gesture_recognizer.utils.cvfpscalc import CvFpsCalc
from hand_gesture_recognizer.model.keypoint_classifier.keypoint_classifier import KeyPointClassifier
from hand_gesture_recognizer.model.point_history_classifier.point_history_classifier import PointHistoryClassifier

import threading
import tkinter as tk
from tkinter import filedialog, messagebox

pose_duration = 0.2
time_between_batches = 2

################################# GUI #################################
# Function to switch between frames (screens)
def show_frame(frame):
    frame.tkraise()


def select_video():
    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv *.MOV")])
    if file_path:
        # selected_file.set(f"Selected: {file_path.split('/')[-1]}")
        selected_file.set(file_path)
    print(selected_file.get())


def execute_split():
    if not selected_file.get():
        messagebox.showwarning("No File", "Please select a video first!")
        return
    show_frame(loading_frame)
    # this freezes the frame
    run_main_in_thread()


def run_main_in_thread():
    thread = threading.Thread(target=main)
    thread.daemon = True  # Ensures thread exits when main program ends
    thread.start()

def show_results():
    # Mockup: Populate with example video names (replace with real output)
    video_list.delete(0, tk.END)
    for i in range(1, 6):
        video_list.insert(tk.END, f"short_video_{i}.mp4")
    show_frame(results_frame)

# Main application window
root = tk.Tk()
root.title("Video to Multiple Short Videos")
root.geometry("400x300")
root.resizable(False, False)

# Create three frames for different states
input_frame = tk.Frame(root)
loading_frame = tk.Frame(root)
results_frame = tk.Frame(root)
selected_file = tk.StringVar()

# Scrollable listbox to display cut video names (mockup)
scrollbar = tk.Scrollbar(results_frame)
video_list = tk.Listbox(results_frame, height=10, width=50, yscrollcommand=scrollbar.set)
scrollbar.config(command=video_list.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
video_list.pack(pady=10)

# Stack frames on top of each other
for frame in (input_frame, loading_frame, results_frame):
    frame.grid(row=0, column=0, sticky="nsew")

# --- Input Frame (Initial Screen) ---
input_label = tk.Label(input_frame, text="Select a video to split", font=("Arial", 14))
input_label.pack(pady=20)

file_label = tk.Label(input_frame, textvariable=selected_file, wraplength=350)
file_label.pack(pady=10)
select_button = tk.Button(input_frame, text="Select Video", command=select_video, width=15)
select_button.pack(pady=10)

execute_button = tk.Button(input_frame, text="Execute", command=execute_split, width=15)
execute_button.pack(pady=20)

# --- Loading Frame ---
loading_label = tk.Label(loading_frame, text="Processing your video...", font=("Arial", 16))
loading_label.pack(expand=True)

# --- Results Frame ---
results_label = tk.Label(results_frame, text="Your Short Videos", font=("Arial", 14))
results_label.pack(pady=10)

back_button = tk.Button(results_frame, text="Back", command=lambda: show_frame(input_frame), width=15)
back_button.pack(pady=10)
################################# GUI #################################

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", help='cap width', type=int, default=960)
    parser.add_argument("--height", help='cap height', type=int, default=540)

    parser.add_argument('--use_static_image_mode', action='store_true')
    parser.add_argument("--min_detection_confidence",
                        help='min_detection_confidence',
                        type=float,
                        default=0.7)
    parser.add_argument("--min_tracking_confidence",
                        help='min_tracking_confidence',
                        type=int,
                        default=0.5)

    args = parser.parse_args()

    return args


def main():
    start_time = time.perf_counter()

    # APP STARTS #################################################
    video_path = selected_file.get()
    print(f"Processing video: {video_path}")
    # process_video(video_path)
    process_video_single_thread(video_path)
    show_results()
    # APP ENDS #################################################
    end_time = time.perf_counter()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.2f} seconds")


# 1h3m for a 1080p 3h video (2.4GHz CPU)
# 57.2m for a 1080p 3h video (3.1GHz CPU)
# 12.8m for a 720p 1h video (2.4GHz CPU)
def process_video_single_thread(video_path):
    cap = cv.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5,
                           min_tracking_confidence=0.5)

    keypoint_classifier = KeyPointClassifier()

    with open('hand_gesture_recognizer/model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = [row[0] for row in csv.reader(f)]

    timestamps_start = []
    timestamps_end = []
    frame_rate = cap.get(cv.CAP_PROP_FPS)

    frame_skip = 5
    frame_count = 0
    end_detected = False

    # monitor(cap, hands)

    while True and not end_detected:
        ret, image = cap.read()
        if not ret:
            break

        # Skip frames for speed
        if frame_count % frame_skip == 0:
            image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
            results = hands.process(image)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    landmark_list = calc_landmark_list(image, hand_landmarks)
                    pre_processed_landmark_list = pre_process_landmark(landmark_list)

                    hand_sign_id = keypoint_classifier(pre_processed_landmark_list)

                    # Start points
                    if keypoint_classifier_labels[hand_sign_id] == "Peace":
                        timestamp = frame_count / frame_rate
                        timestamps_start.append(timestamp)
                    # End points
                    if keypoint_classifier_labels[hand_sign_id] == "OOO" and len(timestamps_start) != 0:
                        timestamp = frame_count / frame_rate
                        if len(timestamps_end) == 0:  # If list is empty
                            timestamps_end.append(timestamp)
                        else:
                            if abs(timestamps_end[0] - timestamp) < time_between_batches:  # If still the same batch
                                timestamps_end.append(timestamp)
                                if (len(timestamps_end) >= 2 and
                                        (timestamps_end[-1] - timestamps_end[0]) >= pose_duration):
                                    end_detected = True
                            else:   # If a different batch
                                timestamps_end.clear()
                                timestamps_end.append(timestamp)
        frame_count += 1

    cap.release()

    print(timestamps_start)

    timestamps_start = normalize_timestamps(timestamps_start)
    # timestamps_end = normalize_timestamps(timestamps_end)
    print(timestamps_start)
    print("end: ")
    print(timestamps_end)
    if not timestamps_start:
        print("No start points found")
        return
    segment_name = 1
    for idx, point_to_start in enumerate(timestamps_start):
        if len(timestamps_start) >= 2 and len(timestamps_start) > idx + 1:
            subclip(video_path, point_to_start, timestamps_start[idx + 1], f"{segment_name}.mp4")
            segment_name = segment_name + 1
    start_time = timestamps_start[-1]
    if len(timestamps_end) > 0:
        print(f"end point of last clip: {timestamps_end[0]}")
        end_time = timestamps_end[0]
        subclip(video_path, start_time, end_time, f"{segment_name}.mp4")
    else:
        subclip(video_path, start_time, VideoFileClip(video_path).duration, f"{segment_name}.mp4")

######### HERE ###########
def worker_init():
    """ Each process initializes its own MediaPipe and classifier. """
    global hands, keypoint_classifier, keypoint_classifier_labels
    hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5,
                                     min_tracking_confidence=0.5)
    keypoint_classifier = KeyPointClassifier()

    with open('hand_gesture_recognizer/model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = [row[0] for row in csv.reader(f)]


def process_frame_worker(args):
    """ Process a single frame and detect hand gestures. """
    frame_count, frame, frame_rate = args
    image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    results = hands.process(image)

    detected_timestamps = []
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            landmark_list = calc_landmark_list(image, hand_landmarks)
            pre_processed_landmark_list = pre_process_landmark(landmark_list)
            hand_sign_id = keypoint_classifier(pre_processed_landmark_list)

            timestamp = frame_count / frame_rate
            if keypoint_classifier_labels[hand_sign_id] == "Peace":
                print(f"Found one at {timestamp}")
                detected_timestamps.append(("start", timestamp))
            if keypoint_classifier_labels[hand_sign_id] == "":
                detected_timestamps.append(("end", timestamp))

    return detected_timestamps  # Return detected timestamps for merging


# 54m for a 1080p 3h video (2.5GHz CPU)
# 52m for a 1080p 3h video (3.1GHz CPU)
# 8.1m for a 720p 1h video (2.5GHz CPU)
def process_video(video_path):
    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    frame_rate = cap.get(cv.CAP_PROP_FPS)
    frame_skip = 5
    frame_count = 0
    end_detected = False
    timestamps_start = []
    timestamps_end = []

    pool = mtp.Pool(mtp.cpu_count(), initializer=worker_init)  # Limit workers to save RAM

    batch_size = 50
    tasks = []
    results = []  # ✅ Store all results

    while True and not end_detected:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_skip == 0:
            tasks.append((frame_count, frame, frame_rate))

        if len(tasks) >= batch_size:  # Process in batches
            batch_results = pool.map(process_frame_worker, tasks)
            results += batch_results  # ✅ Append batch results instead of overwriting
            tasks.clear()  # Free memory

        frame_count += 1

    cap.release()

    # ✅ Process any remaining frames
    if tasks:
        results += pool.map(process_frame_worker, tasks)

    pool.close()
    pool.join()

    # ✅ Merge results
    for detected_timestamps in results:
        for event, timestamp in detected_timestamps:
            if event == "start":
                timestamps_start.append(timestamp)
            elif event == "end":
                timestamps_end.append(timestamp)

    timestamps_start = normalize_timestamps(timestamps_start)
    timestamps_end = normalize_timestamps(timestamps_end)

    print("Starts:", timestamps_start)
    print("Ends:", timestamps_end)

    if not timestamps_start:
        print("No start points found")
        return
    segment_name = 1
    for idx, point_to_start in enumerate(timestamps_start):
        if len(timestamps_start) >= 2 and len(timestamps_start) > idx + 1:
            subclip(video_path, point_to_start, timestamps_start[idx + 1], f"{segment_name}.mp4")
            segment_name = segment_name + 1
    print(f"start point of last clip: {timestamps_start[len(timestamps_start) - 1]}")
    start_time = timestamps_start[len(timestamps_start) - 1]
    if len(timestamps_end) > 0:
        print(f"end point of last clip: {timestamps_end[0]}")
        end_time = timestamps_end[0]
        subclip(video_path, start_time, end_time, f"{segment_name}.mp4")
    else:
        subclip(video_path, start_time, VideoFileClip(video_path).duration, f"{segment_name}.mp4")
######### HERE ###########

def subclip(video_path, start_time, end_time, output_file):
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", video_path,
        "-to", str(end_time - start_time),
        "-force_key_frames", "expr:gte(t,0)",  # Force keyframe at start
        "-preset", "ultrafast",
        f"{output_file}"
    ])


def normalize_timestamps(timestamps):
    temp_timestamps = []
    normalized_timestamps = []
    for idx, timestamp in enumerate(timestamps):    # 2.1 2.2 2.3   5.6 5.7   8.1 8.2 8.3 8.4 8.5
        # When haven't reached the end
        if len(timestamps) > idx + 1 and len(timestamps) >= 2:
            timestamps.sort()
            # Keep flushing to temp
            temp_timestamps.append(timestamp)
            # When reach a different batch
            if abs(timestamp - timestamps[idx + 1]) > time_between_batches:
                # Validate current temp batch and clean temp
                if (len(temp_timestamps) > 0 and
                        temp_timestamps[len(temp_timestamps) - 1] - temp_timestamps[0] >= pose_duration):
                    normalized_timestamps.append(temp_timestamps[len(temp_timestamps) - 1])
                temp_timestamps.clear()
        # When reach the end
        elif idx + 1 == len(timestamps) >= 2:
            # Only process if it is a same-batch stamp since a different-batch stamp being the final stamp is discarded
            # If same batch -> Still add that final stamp to temp
            if (len(temp_timestamps) > 0 and
                    abs(timestamp - temp_timestamps[len(temp_timestamps) - 1]) <= time_between_batches):
                temp_timestamps.append(timestamp)
            # Validate current batch and clean temp
            if (len(temp_timestamps) > 0 and
                    temp_timestamps[len(temp_timestamps) - 1] - temp_timestamps[0] >= pose_duration):
                normalized_timestamps.append(temp_timestamps[len(temp_timestamps) - 1])
            temp_timestamps.clear()
    return normalized_timestamps


def run_with_camera():
    # Argument parsing #################################################################
    args = get_args()

    cap_device = args.device
    cap_width = args.width
    cap_height = args.height

    use_static_image_mode = args.use_static_image_mode
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence

    use_brect = True

    # Camera preparation ###############################################################
    cap = cv.VideoCapture(cap_device)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    # Model load #############################################################
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=1,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    keypoint_classifier = KeyPointClassifier()

    point_history_classifier = PointHistoryClassifier()

    # Read labels ###########################################################
    with open('hand_gesture_recognizer/model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [
            row[0] for row in keypoint_classifier_labels
        ]
    with open(
            'hand_gesture_recognizer/model/point_history_classifier/point_history_classifier_label.csv',
            encoding='utf-8-sig') as f:
        point_history_classifier_labels = csv.reader(f)
        point_history_classifier_labels = [
            row[0] for row in point_history_classifier_labels
        ]

    # FPS Measurement ########################################################
    cvFpsCalc = CvFpsCalc(buffer_len=10)

    # Coordinate history #################################################################
    history_length = 16
    point_history = deque(maxlen=history_length)

    # Finger gesture history ################################################
    finger_gesture_history = deque(maxlen=history_length)

    #  ########################################################################
    mode = 0

    while True:
        fps = cvFpsCalc.get()

        # Process Key (ESC: end) #################################################
        key = cv.waitKey(10)
        if key == 27:  # ESC
            break
        number, mode = select_mode(key, mode)

        # Camera capture #####################################################
        ret, image = cap.read()
        if not ret:
            break
        image = cv.flip(image, 1)  # Mirror display
        debug_image = copy.deepcopy(image)

        # Detection implementation #############################################################
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True

        #  ####################################################################
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks,
                                                  results.multi_handedness):
                # Bounding box calculation
                brect = calc_bounding_rect(debug_image, hand_landmarks)
                # Landmark calculation
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                # Conversion to relative coordinates / normalized coordinates
                pre_processed_landmark_list = pre_process_landmark(
                    landmark_list)
                pre_processed_point_history_list = pre_process_point_history(
                    debug_image, point_history)
                # Write to the dataset file
                logging_csv(number, mode, pre_processed_landmark_list,
                            pre_processed_point_history_list)

                # Hand sign classification
                hand_sign_id = keypoint_classifier(pre_processed_landmark_list)
                if hand_sign_id == "Not applicable":  # Point gesture
                    point_history.append(landmark_list[8])
                else:
                    point_history.append([0, 0])

                # Finger gesture classification
                finger_gesture_id = 0
                point_history_len = len(pre_processed_point_history_list)
                if point_history_len == (history_length * 2):
                    finger_gesture_id = point_history_classifier(
                        pre_processed_point_history_list)

                # Calculates the gesture IDs in the latest detection
                finger_gesture_history.append(finger_gesture_id)
                most_common_fg_id = Counter(
                    finger_gesture_history).most_common()

                # Logic for Determining Checkpoints
                # if keypoint_classifier_labels[hand_sign_id] == "Peace":
                #     print("Peace")

                # Drawing part
                debug_image = draw_bounding_rect(use_brect, debug_image, brect)
                debug_image = draw_landmarks(debug_image, landmark_list)
                debug_image = draw_info_text(
                    debug_image,
                    brect,
                    handedness,
                    keypoint_classifier_labels[hand_sign_id],
                    point_history_classifier_labels[most_common_fg_id[0][0]],
                )
        else:
            point_history.append([0, 0])

        debug_image = draw_point_history(debug_image, point_history)
        debug_image = draw_info(debug_image, fps, mode, number)

        # Screen reflection #############################################################
        cv.imshow('Hand Gesture Recognition', debug_image)

    cap.release()
    cv.destroyAllWindows()


def select_mode(key, mode):
    number = -1
    if 48 <= key <= 57:  # 0 ~ 9
        number = key - 48
    if key == 110:  # n
        mode = 0
    if key == 107:  # k
        mode = 1
    if key == 104:  # h
        mode = 2
    return number, mode


def calc_bounding_rect(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_array = np.empty((0, 2), int)

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point = [np.array((landmark_x, landmark_y))]

        landmark_array = np.append(landmark_array, landmark_point, axis=0)

    x, y, w, h = cv.boundingRect(landmark_array)

    return [x, y, x + w, y + h]


def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    # Keypoint
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        # landmark_z = landmark.z

        landmark_point.append([landmark_x, landmark_y])

    return landmark_point


def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)

    # Convert to relative coordinates
    base_x, base_y = 0, 0
    for index, landmark_point in enumerate(temp_landmark_list):
        if index == 0:
            base_x, base_y = landmark_point[0], landmark_point[1]

        temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
        temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y

    # Convert to a one-dimensional list
    temp_landmark_list = list(
        itertools.chain.from_iterable(temp_landmark_list))

    # Normalization
    max_value = max(list(map(abs, temp_landmark_list)))

    def normalize_(n):
        return n / max_value

    temp_landmark_list = list(map(normalize_, temp_landmark_list))

    return temp_landmark_list


def pre_process_point_history(image, point_history):
    image_width, image_height = image.shape[1], image.shape[0]

    temp_point_history = copy.deepcopy(point_history)

    # Convert to relative coordinates
    base_x, base_y = 0, 0
    for index, point in enumerate(temp_point_history):
        if index == 0:
            base_x, base_y = point[0], point[1]

        temp_point_history[index][0] = (temp_point_history[index][0] -
                                        base_x) / image_width
        temp_point_history[index][1] = (temp_point_history[index][1] -
                                        base_y) / image_height

    # Convert to a one-dimensional list
    temp_point_history = list(
        itertools.chain.from_iterable(temp_point_history))

    return temp_point_history


def logging_csv(number, mode, landmark_list, point_history_list):
    if mode == 0:
        pass
    if mode == 1 and (0 <= number <= 9):
        csv_path = 'hand_gesture_recognizer/model/keypoint_classifier/keypoint.csv'
        with open(csv_path, 'a', newline="") as f:
            writer = csv.writer(f)
            writer.writerow([number, *landmark_list])
    if mode == 2 and (0 <= number <= 9):
        csv_path = 'hand_gesture_recognizer/model/point_history_classifier/point_history.csv'
        with open(csv_path, 'a', newline="") as f:
            writer = csv.writer(f)
            writer.writerow([number, *point_history_list])
    return


def draw_landmarks(image, landmark_point):
    if len(landmark_point) > 0:
        # Thumb
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]),
                (255, 255, 255), 2)

        # Index finger
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]),
                (255, 255, 255), 2)

        # Middle finger
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]),
                (255, 255, 255), 2)

        # Ring finger
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]),
                (255, 255, 255), 2)

        # Little finger
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]),
                (255, 255, 255), 2)

        # Palm
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]),
                (255, 255, 255), 2)

    # Key Points
    for index, landmark in enumerate(landmark_point):
        if index == 0:  # 手首1
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 1:  # 手首2
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 2:  # 親指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 3:  # 親指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 4:  # 親指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 5:  # 人差指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 6:  # 人差指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 7:  # 人差指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 8:  # 人差指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 9:  # 中指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 10:  # 中指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 11:  # 中指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 12:  # 中指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 13:  # 薬指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 14:  # 薬指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 15:  # 薬指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 16:  # 薬指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 17:  # 小指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 18:  # 小指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 19:  # 小指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 20:  # 小指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)

    return image


def draw_bounding_rect(use_brect, image, brect):
    if use_brect:
        # Outer rectangle
        cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[3]),
                     (0, 0, 0), 1)

    return image


def draw_info_text(image, brect, handedness, hand_sign_text,
                   finger_gesture_text):
    cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[1] - 22),
                 (0, 0, 0), -1)

    info_text = handedness.classification[0].label[0:]
    if hand_sign_text != "":
        info_text = info_text + ':' + hand_sign_text
    cv.putText(image, info_text, (brect[0] + 5, brect[1] - 4),
               cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)

    # if finger_gesture_text != "":
    #     cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
    #                cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
    #     cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
    #                cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
    #                cv.LINE_AA)

    return image


def draw_point_history(image, point_history):
    for index, point in enumerate(point_history):
        if point[0] != 0 and point[1] != 0:
            cv.circle(image, (point[0], point[1]), 1 + int(index / 2),
                      (152, 251, 152), 2)

    return image


def draw_info(image, fps, mode, number):
    cv.putText(image, "FPS:" + str(fps), (10, 30), cv.FONT_HERSHEY_SIMPLEX,
               1.0, (0, 0, 0), 4, cv.LINE_AA)
    cv.putText(image, "FPS:" + str(fps), (10, 30), cv.FONT_HERSHEY_SIMPLEX,
               1.0, (255, 255, 255), 2, cv.LINE_AA)

    mode_string = ['Logging Key Point', 'Logging Point History']
    if 1 <= mode <= 2:
        cv.putText(image, "MODE:" + mode_string[mode - 1], (10, 90),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                   cv.LINE_AA)
        if 0 <= number <= 9:
            cv.putText(image, "NUM:" + str(number), (10, 110),
                       cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                       cv.LINE_AA)
    return image


def monitor(cap, hands):
    ############### Gud Code ################
    use_brect = True
    point_history_classifier = PointHistoryClassifier()
    keypoint_classifier = KeyPointClassifier()
    # Read labels ###########################################################
    with open('hand_gesture_recognizer/model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [
            row[0] for row in keypoint_classifier_labels
        ]
    with open(
            'hand_gesture_recognizer/model/point_history_classifier/point_history_classifier_label.csv',
            encoding='utf-8-sig') as f:
        point_history_classifier_labels = csv.reader(f)
        point_history_classifier_labels = [
            row[0] for row in point_history_classifier_labels
        ]

    # FPS Measurement ########################################################
    cvFpsCalc = CvFpsCalc(buffer_len=10)

    # Coordinate history #################################################################
    history_length = 16
    point_history = deque(maxlen=history_length)

    # Finger gesture history ################################################
    finger_gesture_history = deque(maxlen=history_length)

    #  ########################################################################
    mode = 0

    while True:
        fps = cvFpsCalc.get()

        # Process Key (ESC: end) #################################################
        key = cv.waitKey(10)
        if key == 27:  # ESC
            break
        number, mode = select_mode(key, mode)

        # Camera capture #####################################################
        ret, image = cap.read()
        if not ret:
            break
        image = cv.flip(image, 1)  # Mirror display
        debug_image = copy.deepcopy(image)

        # Detection implementation #############################################################
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True

        #  ####################################################################
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks,
                                                  results.multi_handedness):
                # Bounding box calculation
                brect = calc_bounding_rect(debug_image, hand_landmarks)
                # Landmark calculation
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                # Conversion to relative coordinates / normalized coordinates
                pre_processed_landmark_list = pre_process_landmark(
                    landmark_list)
                pre_processed_point_history_list = pre_process_point_history(
                    debug_image, point_history)
                # Write to the dataset file
                logging_csv(number, mode, pre_processed_landmark_list,
                            pre_processed_point_history_list)

                # Hand sign classification
                hand_sign_id = keypoint_classifier(pre_processed_landmark_list)
                if hand_sign_id == "Not applicable":  # Point gesture
                    point_history.append(landmark_list[8])
                else:
                    point_history.append([0, 0])

                # Finger gesture classification
                finger_gesture_id = 0
                point_history_len = len(pre_processed_point_history_list)
                if point_history_len == (history_length * 2):
                    finger_gesture_id = point_history_classifier(
                        pre_processed_point_history_list)

                # Calculates the gesture IDs in the latest detection
                finger_gesture_history.append(finger_gesture_id)
                most_common_fg_id = Counter(
                    finger_gesture_history).most_common()

                # Logic for Determining Checkpoints
                if keypoint_classifier_labels[hand_sign_id] == "Peace":
                    print("Peace")

                # Drawing part
                debug_image = draw_bounding_rect(use_brect, debug_image, brect)
                debug_image = draw_landmarks(debug_image, landmark_list)
                debug_image = draw_info_text(
                    debug_image,
                    brect,
                    handedness,
                    keypoint_classifier_labels[hand_sign_id],
                    point_history_classifier_labels[most_common_fg_id[0][0]],
                )
        else:
            point_history.append([0, 0])

        debug_image = draw_point_history(debug_image, point_history)
        debug_image = draw_info(debug_image, fps, mode, number)

        # Screen reflection #############################################################
        cv.imshow('Hand Gesture Recognition', debug_image)

    cap.release()
    cv.destroyAllWindows()
    ############### Gud Code ################


if __name__ == "__main__":
    # Start with the input frame visible
    show_frame(input_frame)

    # Run the application
    root.mainloop()
