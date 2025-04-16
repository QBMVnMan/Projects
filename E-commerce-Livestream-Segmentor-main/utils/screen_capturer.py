import cv2
import numpy as np
import pyautogui
import threading
import tkinter as tk
from tkinter import ttk
import moviepy.video.io.VideoFileClip as mp
import soundcard as sc
import soundfile as sf

# Screen recording settings
screen_width, screen_height = pyautogui.size()
frame_rate = 20

# Audio settings
audio_rate = 48000
audio_channels = 1
audio_chunk = 2048

# Global variables
recording = False
desktop_audio_enabled = False
desktop_audio_device_name = None

def get_audio_devices():
    output_devices = [(dev.name, dev.name) for dev in sc.all_speakers()]
    return output_devices

def record_desktop_audio(audio_filename, device_name, enabled):
    if not enabled:
        return

    try:
        with sc.get_microphone(id=device_name, include_loopback=True).recorder(samplerate=audio_rate) as mic:
            frames = []
            while recording:
                data = mic.record(numframes=audio_chunk) #fixed audio chunk
                frames.append(data)

            final_data = np.concatenate(frames)
            sf.write(file=audio_filename, data=final_data[:, 0], samplerate=audio_rate)

    except Exception as e:
        print(f"Error recording desktop audio from {device_name}: {e}")

def record_screen():
    global recording
    recording = True

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter("screen_record.avi", fourcc, frame_rate, (screen_width, screen_height))

    desktop_audio_thread = threading.Thread(target=record_desktop_audio, args=("desktop_audio.wav", desktop_audio_device_name, desktop_audio_enabled))

    if desktop_audio_enabled:
        desktop_audio_thread.start()

    while recording:
        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out.write(frame)

    out.release()
    combine_audio_video()

def combine_audio_video():
    try:
        video = mp.VideoFileClip("screen_record.avi")
        audio_clips = []
        if desktop_audio_enabled:
            audio_clips.append(mp.AudioFileClip("desktop_audio.wav"))

        if audio_clips:
            final_audio = mp.CompositeAudioClip(audio_clips)
            final_video = video.set_audio(final_audio)
        else:
            final_video = video

        final_video.write_videofile("final_record.mp4", codec="libx264", audio_codec="aac")

    except Exception as e:
        print(f"Error combining audio and video: {e}")
    finally:
        import os
        for file in ["screen_record.avi", "desktop_audio.wav"]:
            if os.path.exists(file):
                os.remove(file)

def stop_recording():
    global recording
    recording = False

def start_gui():
    global desktop_audio_device_name, desktop_audio_enabled
    root = tk.Tk()
    root.title("Screen Recorder")
    root.geometry("400x300")

    output_devices = get_audio_devices()

    # Desktop audio selection
    desktop_label = tk.Label(root, text="Desktop Audio:")
    desktop_label.pack()
    desktop_combo = ttk.Combobox(root, values=[name for name, index in output_devices], state="readonly")
    desktop_combo.pack()
    desktop_combo.current(0)
    print(f"desktop_audio_device_name {output_devices[desktop_combo.current()][0]}")
    desktop_audio_device_name = output_devices[desktop_combo.current()][0]

    desktop_check = tk.Checkbutton(root, text="Enable Desktop Audio", variable=tk.BooleanVar(value=desktop_audio_enabled), command=lambda: toggle_desktop_audio())
    desktop_check.pack()

    # Start/Stop buttons
    start_btn = tk.Button(root, text="Start Recording", command=lambda: threading.Thread(target=record_screen).start(), fg="white", bg="green")
    start_btn.pack(pady=10)

    stop_btn = tk.Button(root, text="Stop Recording", command=stop_recording, fg="white", bg="red")
    stop_btn.pack(pady=10)

    root.mainloop()

def toggle_desktop_audio():
    global desktop_audio_enabled
    desktop_audio_enabled = not desktop_audio_enabled

start_gui()