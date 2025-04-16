#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import copy
import argparse
import itertools
import os
import subprocess
import sys
from collections import Counter
from collections import deque
from datetime import datetime
from functools import partial


import cv2 as cv
import numpy as np
import mediapipe as mp
import time
import multiprocessing as mtp

from moviepy import VideoFileClip

from hand_gesture_recognizer.utils.cvfpscalc import CvFpsCalc
from hand_gesture_recognizer.model.keypoint_classifier.keypoint_classifier import KeyPointClassifier
from hand_gesture_recognizer.model.point_history_classifier.point_history_classifier import PointHistoryClassifier

import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog

pose_duration = 0.8
time_between_batches = 0.4
start_sign = "OK"
end_sign = "Peace"

################################# GUI #################################
# Set appearance mode and default color theme for CustomTkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Main application window
root = ctk.CTk()
root.title("Video to Multiple Short Videos")
root.geometry("800x600")
root.resizable(True, True)


class VideoSplitterApp:
    """Application for splitting videos into multiple shorter clips.

    This class provides a CustomTkinter-based GUI for uploading videos
    and splitting them into shorter segments.
    """

    def __init__(self, master):
        """Initialize the application.

        Args:
            master: The root CTk window of the application.
        """
        self.master = master
        self.selected_file = tk.StringVar()
        # Get current date and time
        self.date_time = tk.StringVar()

        # Set up frames for different screens
        self._setup_frames()

        # Start with the input frame visible
        self.show_frame(self.input_frame)

    def _setup_frames(self):
        """Set up the main frames for different application states."""
        # Create three frames for different states with the same grid position
        self.input_frame = ctk.CTkFrame(self.master, fg_color="#E8ECEF", corner_radius=0)
        self.loading_frame = ctk.CTkFrame(self.master, fg_color="#E8ECEF", corner_radius=0)
        self.results_frame = ctk.CTkFrame(self.master, fg_color="#E8ECEF", corner_radius=0)

        # Stack frames on top of each other
        for frame in (self.input_frame, self.loading_frame, self.results_frame):
            frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid to allow expansion
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        # Set up each frame's content
        self._setup_input_frame()
        self._setup_loading_frame()
        self._setup_results_frame()

    def _setup_input_frame(self):
        """Set up the input frame with upload functionality."""
        # Configure frame layout
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_rowconfigure(0, weight=0)  # Header
        self.input_frame.grid_rowconfigure(1, weight=1)  # Drag area
        self.input_frame.grid_rowconfigure(2, weight=0)  # File label
        self.input_frame.grid_rowconfigure(3, weight=0)  # Execute button
        self.input_frame.grid_rowconfigure(4, weight=0)  # Footer

        # Header frame (centered)
        header_frame = ctk.CTkFrame(self.input_frame, fg_color="white", corner_radius=8)
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")

        # Configure header for centering
        header_frame.grid_columnconfigure(0, weight=1)

        # Upload button (centered in header frame)
        upload_button = ctk.CTkButton(
            header_frame,
            text="Upload Video",
            command=self.select_video,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        upload_button.grid(row=0, column=0, padx=20, pady=10)

        # Drag-and-drop area
        drag_area = ctk.CTkFrame(self.input_frame, fg_color="white", corner_radius=8)
        drag_area.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        # Configure drag area for centering
        drag_area.grid_rowconfigure(0, weight=1)
        drag_area.grid_rowconfigure(1, weight=0)
        drag_area.grid_rowconfigure(2, weight=1)
        drag_area.grid_columnconfigure(0, weight=1)

        # Upload icon (centered)
        upload_icon = ctk.CTkLabel(
            drag_area,
            text="⬆",
            font=ctk.CTkFont(size=40),
            text_color="#A9A9A9"
        )
        upload_icon.grid(row=0, column=0, padx=20, pady=20)

        # Text labels (centered)
        drag_label = ctk.CTkLabel(
            drag_area,
            text="Select video to upload",
            font=ctk.CTkFont(size=16)
        )
        drag_label.grid(row=1, column=0, padx=20, pady=(0, 5))

        drag_sublabel = ctk.CTkLabel(
            drag_area,
            text="Or drag and drop video files",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        drag_sublabel.grid(row=2, column=0, padx=20, pady=(0, 20))

        # Selected file label
        file_label = ctk.CTkLabel(
            self.input_frame,
            textvariable=self.selected_file,
            wraplength=700
        )
        file_label.grid(row=2, column=0, padx=20, pady=5)

        # Execute button (centered)
        execute_button = ctk.CTkButton(
            self.input_frame,
            text="Execute",
            command=self.execute_split,
            width=150,
            font=ctk.CTkFont(weight="bold")
        )
        execute_button.grid(row=3, column=0, padx=20, pady=10)

        # Footer/info section (centered)
        footer_frame = ctk.CTkFrame(self.input_frame, fg_color="#E8ECEF", corner_radius=0)
        footer_frame.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")

        # Configure footer for centering
        footer_frame.grid_columnconfigure(0, weight=1)

        # Version info
        info_label = ctk.CTkLabel(
            footer_frame,
            text="Video to Multiple Short Videos App v1.0",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.grid(row=0, column=0, padx=20, pady=(5, 0))

        # Description
        desc_label = ctk.CTkLabel(
            footer_frame,
            text="Easily split your videos into shorter clips!",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc_label.grid(row=1, column=0, padx=20, pady=(0, 5))

    def _setup_loading_frame(self):
        """Set up the loading screen for processing indication."""
        # Configure frame layout
        self.loading_frame.grid_columnconfigure(0, weight=1)
        self.loading_frame.grid_rowconfigure(0, weight=1)

        # Loading elements
        loading_label = ctk.CTkLabel(
            self.loading_frame,
            text="Processing your video...",
            font=ctk.CTkFont(size=20),
            text_color="#606770"
        )
        loading_label.grid(row=0, column=0, padx=20, pady=20)

        # Loading progress bar (centered)
        progress = ctk.CTkProgressBar(self.loading_frame, width=300)
        progress.grid(row=1, column=0, padx=20, pady=20)
        progress.configure(mode="indeterminate")
        progress.start()

    def _setup_results_frame(self):
        """Set up the results frame to display processed video clips."""
        # Configure frame layout
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=0)  # Header
        self.results_frame.grid_rowconfigure(1, weight=1)  # Video grid
        self.results_frame.grid_rowconfigure(2, weight=0)  # Back button

        # Header for results (centered)
        results_header = ctk.CTkFrame(self.results_frame, fg_color="white", corner_radius=8)
        results_header.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")

        # Configure header for centering
        results_header.grid_columnconfigure(0, weight=1)

        # Results title
        results_label = ctk.CTkLabel(
            results_header,
            text="Your Short Videos",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#606770"
        )
        results_label.grid(row=0, column=0, padx=20, pady=10)

        # Scrollable frame for videos (centered)
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.results_frame,
            fg_color="#E8ECEF",
            corner_radius=8
        )
        self.scrollable_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        # Back button (centered)
        back_button = ctk.CTkButton(
            self.results_frame,
            text="Back",
            command=lambda: self.show_frame(self.input_frame),
            width=150,
            font=ctk.CTkFont(weight="bold")
        )
        back_button.grid(row=2, column=0, padx=20, pady=20)

    def show_frame(self, frame):
        """Bring the specified frame to the front.

        Args:
            frame: The frame to display.
        """
        frame.tkraise()

    def select_video(self):
        """Open file dialog to select a video file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mkv")]
        )
        if file_path:
            self.selected_file.set(file_path)

    def execute_split(self):
        """Process the video and show results."""
        if not self.selected_file.get():
            messagebox.showwarning("No File", "Please select a video first!")
            return

        self.show_frame(self.loading_frame)
        run_main_in_thread()


    def show_results(self):
        """Display the results screen with processed videos."""
        self.populate_videos()
        self.show_frame(self.results_frame)

    def populate_videos(self):
        """Create video thumbnail entries from real videos in the results screen."""
        # Clear existing widgets in scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Get the folder path with real videos
        folder_path = f'videos/{self.date_time.get()}'

        # Check if folder exists
        if not os.path.exists(folder_path):
            # Show no videos message
            no_videos_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="No videos found in the specified folder",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_videos_label.pack(pady=50)
            return

        # Get list of video files
        video_files = [f for f in os.listdir(folder_path)
                       if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))]

        if not video_files:
            # Show no videos message
            no_videos_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="No video files found in the folder",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_videos_label.pack(pady=50)
            return

        # Create a 3-column grid for videos
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)
        self.scrollable_frame.grid_columnconfigure(2, weight=1)

        # Create video entries
        for i, video_file in enumerate(video_files):
            video_path = os.path.join(folder_path, video_file)

            # Get video metadata if possible (optional)
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # Convert to MB

            # Create frame for this video
            video_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="white", corner_radius=8)
            video_frame.grid(row=i // 3, column=i % 3, padx=10, pady=10, sticky="nsew")

            # Configure video frame for centering content
            video_frame.grid_columnconfigure(0, weight=1)

            # Placeholder for video thumbnail (still using placeholder since generating
            # actual thumbnails requires additional processing)
            thumbnail = ctk.CTkLabel(
                video_frame,
                text="[Video Thumbnail]",
                fg_color="#E8ECEF",
                text_color="#606770",
                width=180,
                height=120,
                corner_radius=4
            )
            thumbnail.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

            # Video title (actual filename)
            title = ctk.CTkLabel(
                video_frame,
                text=video_file,
                font=ctk.CTkFont(size=12),
                text_color="#1A73E8",
                wraplength=180  # Wrap long filenames
            )
            title.grid(row=1, column=0, padx=10, pady=(0, 5))

            # File size info
            file_info = ctk.CTkLabel(
                video_frame,
                text=f"{file_size:.1f} MB",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            file_info.grid(row=2, column=0, padx=10, pady=(0, 5))

            # Button frame (centered)
            button_frame = ctk.CTkFrame(video_frame, fg_color="white", corner_radius=0)
            button_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

            # Center the buttons within the frame
            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)
            button_frame.grid_columnconfigure(2, weight=1)

            # Play button - replace embed button
            play_btn = ctk.CTkButton(
                button_frame,
                text="Play",
                font=ctk.CTkFont(size=10),
                width=50,
                height=25,
                command=lambda v=video_path: self.play_video(v)
            )
            play_btn.grid(row=0, column=0, padx=2, pady=5)

            # Open folder button - replace edit button
            folder_btn = ctk.CTkButton(
                button_frame,
                text="Folder",
                font=ctk.CTkFont(size=10),
                width=50,
                height=25,
                command=lambda f=folder_path: self.open_folder(self.selected_file.get())
            )
            folder_btn.grid(row=0, column=1, padx=2, pady=5)

            # More options button
            more_btn = ctk.CTkButton(
                button_frame,
                text="•••",
                font=ctk.CTkFont(size=10),
                width=50,
                height=25,
                command=lambda v=video_path: self.show_options(v)
            )
            more_btn.grid(row=0, column=2, padx=2, pady=5)

    def play_video(self, video_path):
        """Open the video in the default video player"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(video_path)
            elif os.name == 'posix':  # macOS, Linux
                import subprocess
                subprocess.call(('open', video_path) if sys.platform == 'darwin' else ('xdg-open', video_path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open video: {e}")

    def open_folder(self, folder_path):
        """Open the folder containing the videos"""
        folder_path = folder_path.rsplit('/', 1)[0]
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS, Linux
                import subprocess
                subprocess.call(('open', folder_path) if sys.platform == 'darwin' else ('xdg-open', folder_path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def show_options(self, video_path):
        """Show additional options for the video"""
        options = ["Rename", "Delete", "Copy path"]

        # Create a simple popup menu
        popup = tk.Menu(self.master, tearoff=0)
        popup.add_command(label="Rename", command=lambda: self.rename_video(video_path))
        popup.add_command(label="Delete", command=lambda: self.delete_video(video_path))
        popup.add_command(label="Copy path", command=lambda: self.copy_path(video_path))

        # Display the popup menu
        try:
            popup.tk_popup(self.master.winfo_pointerx(), self.master.winfo_pointery())
        finally:
            popup.grab_release()

    def rename_video(self, video_path):
        """Rename the video file"""
        old_name = os.path.basename(video_path)
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=old_name)

        if new_name and new_name != old_name:
            try:
                new_path = os.path.join(os.path.dirname(video_path), new_name)
                os.rename(video_path, new_path)
                self.populate_videos()  # Refresh the view
            except Exception as e:
                messagebox.showerror("Error", f"Could not rename file: {e}")

    def delete_video(self, video_path):
        """Delete the video file"""
        if messagebox.askyesno("Confirm Delete",
                               f"Are you sure you want to delete {os.path.basename(video_path)}?"):
            try:
                os.remove(video_path)
                self.populate_videos()  # Refresh the view
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")

    def copy_path(self, video_path):
        """Copy the video path to clipboard"""
        self.master.clipboard_clear()
        self.master.clipboard_append(video_path)
        messagebox.showinfo("Info", "Path copied to clipboard")

# Function to switch between frames (screens)
def run_main_in_thread():
    thread = threading.Thread(target=main)
    thread.daemon = True  # Ensures thread exits when main program ends
    thread.start()
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

    # Create App instance and run it

    video_path = app.selected_file.get()
    print(f"Processing video: {video_path}")

    # Get available CPU cores (or use a reasonable default)
    num_cores = mtp.cpu_count()
    print(f"num_cores: {num_cores}")
    # Use slightly fewer cores than available to avoid overloading the system
    num_segments = max(2, num_cores - 1)

    # Process video in parallel
    timestamps_start, timestamps_end = process_video_parallel(video_path, num_segments)

    # Process the results as before
    print("starts after normalize: ")
    print(timestamps_start)
    print("end: ")
    print(timestamps_end)

    app.date_time.set(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

    if not timestamps_start:
        print("No start points found")
        app.show_results()
        return

    # Convert to string with a specific format
    datetime_string = app.date_time.get()

    # Create clips from the timestamps
    segment_name = 1
    for idx, point_to_start in enumerate(timestamps_start):
        if len(timestamps_start) >= 2 and len(timestamps_start) > idx + 1:
            subclip(datetime_string, video_path, point_to_start, timestamps_start[idx + 1], f"{segment_name}.mp4")
            segment_name = segment_name + 1

    print(f"start point of last clip: {timestamps_start[-1]}")
    start_time_last = timestamps_start[-1]

    if len(timestamps_end) > 0:
        print(f"end point of last clip: {timestamps_end[0]}")
        end_time_last = timestamps_end[0]
        subclip(datetime_string, video_path, start_time_last, end_time_last, f"{segment_name}.mp4")
    else:
        subclip(datetime_string, video_path, start_time_last, VideoFileClip(video_path).duration, f"{segment_name}.mp4")

    app.show_results()
    # APP ENDS #################################################

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")


def process_video_segment(video_path, start_time, end_time):
    """
    Process a specific segment of the video.

    Args:
        video_path (str): Path to the video file
        start_time (float): Time in seconds to start processing
        end_time (float): Time in seconds to end processing

    Returns:
        tuple: Lists of timestamps for starts and ends
    """
    cap = cv.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video for segment {start_time}-{end_time}.")
        return [], []

    # Get video details
    frame_rate = cap.get(cv.CAP_PROP_FPS)

    # Set starting position
    start_frame = int(start_time * frame_rate)
    end_frame = int(end_time * frame_rate)

    cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)
    frame_count = start_frame

    # Initialize other variables as in your original function
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                           min_detection_confidence=0.5, min_tracking_confidence=0.5)

    keypoint_classifier = KeyPointClassifier()

    with open('hand_gesture_recognizer/model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = [row[0] for row in csv.reader(f)]

    timestamps_start = []
    timestamps_end = []

    initialize_dynamic_parameters(frame_rate)
    frame_skip = calculate_frames_to_skip(frame_rate)
    print(f"Frame skip: {frame_skip}")
    end_detected = False

    # Process frames until we reach the end frame
    while frame_count < end_frame and not end_detected:
        ret, image = cap.read()
        if not ret:
            break

        # Skip frames for speed
        if frame_count % frame_skip == 0:

            timestamp = frame_count / frame_rate
            print(f"{timestamp}")

            image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
            results = hands.process(image)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    landmark_list = calc_landmark_list(image, hand_landmarks)
                    pre_processed_landmark_list = pre_process_landmark(landmark_list)

                    hand_sign_id = keypoint_classifier(pre_processed_landmark_list)

                    # Start points
                    if keypoint_classifier_labels[hand_sign_id] == start_sign:
                        timestamps_start.append(timestamp)
                    # End points
                    if keypoint_classifier_labels[hand_sign_id] == end_sign:
                        if len(timestamps_end) == 0:  # If list is empty
                            timestamps_end.append(timestamp)
                        else:
                            if abs(timestamps_end[-1] - timestamp) <= time_between_batches:  # If still the same batch
                                timestamps_end.append(timestamp)
                                if (len(timestamps_end) >= 2 and
                                        abs(timestamps_end[-1] - timestamps_end[0]) >= pose_duration):
                                    end_detected = True
                            else:   # If a different batch
                                timestamps_end.clear()
                                timestamps_end.append(timestamp)
        frame_count += 1
    cap.release()
    return timestamps_start, timestamps_end


def initialize_dynamic_parameters(fps):
    """
    Initialize global parameters based on frame rate.

    Args:
        fps (float): Frames per second of the video
    """
    global pose_duration, time_between_batches

    # Reference values optimized for 30fps video
    reference_fps = 30.0
    reference_pose_duration = pose_duration
    reference_time_between_batches = time_between_batches

    # Scale parameters linearly with frame rate ratio
    fps_ratio = fps / reference_fps

    # Apply scaling - slower videos need more time, faster videos need less
    pose_duration = reference_pose_duration * fps_ratio
    time_between_batches = reference_time_between_batches * fps_ratio

    print(f"- Pose duration: {pose_duration:.2f}s")
    print(f"- Time between batches: {time_between_batches:.2f}s")


def calculate_frames_to_skip(fps):
    """
    Calculate how many frames to skip while maintaining reliable detection.

    Args:
        fps (float): Frames per second of the video

    Returns:
        int: Number of frames to skip between processed frames
    """
    # Reference values for 30fps
    reference_fps = 30.0
    reference_min_detection_window = pose_duration
    reference_min_samples = 3

    # Scale detection window based on fps ratio
    fps_ratio = reference_fps / fps
    min_detection_window_seconds = reference_min_detection_window * fps_ratio

    # Calculate how many frames we need to check within our minimum detection window
    frames_in_window = fps * min_detection_window_seconds

    # Calculate maximum frames to skip while still getting enough samples
    max_skip = int(frames_in_window / reference_min_samples)

    print(f"- Min detection window: {min_detection_window_seconds:.2f}s")

    # Ensure we don't return 0 (which would mean process every frame)
    return max(1, max_skip - 1)


def process_video_parallel(video_path, num_segments=4):
    """
    Process a video by dividing it into segments and processing them in parallel.

    Args:
        video_path (str): Path to the video file
        num_segments (int): Number of segments to divide the video into

    Returns:
        tuple: Combined lists of start and end timestamps
    """
    # Calculate segment boundaries
    segments = calculate_segment_boundaries(video_path, num_segments)
    print(f"Dividing video into {num_segments} segments:")
    for i, (start, end) in enumerate(segments):
        print(f"  Segment {i + 1}: {start:.2f}s - {end:.2f}s")

    # Create a pool of worker processes
    pool = mtp.Pool(processes=min(mtp.cpu_count(), num_segments))

    # Create a partial function with the video_path already set
    process_segment = partial(process_segment_wrapper, video_path=video_path)

    # Process all segments in parallel
    results = pool.starmap(process_segment, segments)

    # Close the pool
    pool.close()
    pool.join()

    # Combine results from all segments
    all_starts = []
    all_ends = []

    for starts, ends in results:
        all_starts.extend(starts)
        all_ends.extend(ends)

    # Sort the combined timestamps
    all_starts.sort()
    all_ends.sort()

    # Normalize timestamps if needed
    all_starts = normalize_timestamps(all_starts)
    print(f"process_video_parallel: End before normalize: {all_ends}")
    all_ends = normalize_timestamps(all_ends)
    print(f"process_video_parallel: End after normalize: {all_ends}")
    if len(all_ends) > 0 and len(all_starts) > 0:
        if all_ends[-1] > all_starts[0]:
            real_end = all_ends[-1]
            all_ends.clear()
            all_ends.append(real_end)
        else:
            all_ends.clear()
    else:
        all_ends.clear()
    print(f"process_video_parallel: End after cleaning: {all_ends}")

    return all_starts, all_ends


def process_segment_wrapper(start_time, end_time, video_path):
    """
    Wrapper function to be used with pool.starmap().
    """
    print(f"Processing segment {start_time:.2f}s - {end_time:.2f}s")
    return process_video_segment(video_path, start_time, end_time)


def calculate_segment_boundaries(video_path, num_segments):
    """
    Calculate the starting and ending points for each segment of the video.

    Args:
        video_path (str): Path to the video file
        num_segments (int): Number of segments to divide the video into

    Returns:
        list of tuples: Each tuple contains (start_time, end_time) in seconds
    """
    # Open the video to get its duration
    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return []

    # Get total frames and frame rate
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    frame_rate = cap.get(cv.CAP_PROP_FPS)
    total_duration = total_frames / frame_rate

    cap.release()

    # Calculate segment duration
    segment_duration = total_duration / num_segments

    # Calculate segment boundaries
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        end_time = (i + 1) * segment_duration
        # For the last segment, ensure we go to the exact end
        if i == num_segments - 1:
            end_time = total_duration

        segments.append((start_time, end_time))

    return segments


def subclip(date_time, video_path, start_time, end_time, output_file):
    folder_path = f"videos/{date_time}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", video_path,
        "-t", str(end_time - start_time),
        "-c:v", "copy",  # Stream copy video - no re-encoding
        "-c:a", "copy",  # Stream copy audio - no re-encoding
        "-avoid_negative_ts", "make_zero",  # Helps with frame accuracy
        f"{folder_path}/{output_file}"
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
                        temp_timestamps[-1] - temp_timestamps[0] >= pose_duration):
                    normalized_timestamps.append(temp_timestamps[-1])
                temp_timestamps.clear()
        # When reach the end
        elif idx + 1 == len(timestamps) >= 2:
            # Only process if it is a same-batch stamp since a different-batch stamp being the final stamp is discarded
            # If same batch -> Still add that final stamp to temp
            if (len(temp_timestamps) > 0 and
                    abs(timestamp - temp_timestamps[-1]) <= time_between_batches):
                temp_timestamps.append(timestamp)
            # Validate current batch and clean temp
            if (len(temp_timestamps) > 0 and
                    temp_timestamps[-1] - temp_timestamps[0] >= pose_duration):
                normalized_timestamps.append(temp_timestamps[-1])
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


if __name__ == "__main__":
    app = VideoSplitterApp(root)
    root.mainloop()
