import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import pytesseract
import re
from datetime import datetime
import os

# Regex pattern for DD/MM/YYYY HH:mm:ss:SSS
TIMESTAMP_PATTERN = re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}:\d{3})")


def parse_timestamp(text: str):
    match = TIMESTAMP_PATTERN.search(text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%d/%m/%Y %H:%M:%S:%f")
        except ValueError:
            return None
    return None


def find_frame_for_time(cap, target_time):
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    region_width = 300
    region_height = 50
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    x_start = max(0, width - region_width)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        overlay = frame[0:region_height, x_start:width]
        gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 7')
        ts = parse_timestamp(text)
        if ts and ts >= target_time:
            return int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    return None


def extract_snippet(video_path, start_time, end_time, output_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Unable to open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    start_frame = find_frame_for_time(cap, start_time)
    if start_frame is None:
        raise RuntimeError("Start time not found")

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        overlay = frame[0:50, width-300:width]
        gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 7')
        ts = parse_timestamp(text)
        if ts and ts >= end_time:
            break
        frames.append(frame)
    cap.release()

    if not frames:
        raise RuntimeError("No frames extracted")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    for fr in frames:
        out.write(fr)
    out.release()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VidExtract")
        self.geometry("400x200")
        self.configure(bg="#1e1e1e")
        style = ttk.Style(self)
        style.theme_use('alt')
        style.configure('TLabel', background="#1e1e1e", foreground="white")
        style.configure('TButton', background="#333333", foreground="white")
        style.configure('TEntry', fieldbackground="#333333", foreground="white")

        self.video_path = None

        btn_select = ttk.Button(self, text="Select MKV", command=self.select_file)
        btn_select.pack(pady=10)

        self.lbl_file = ttk.Label(self, text="No file selected")
        self.lbl_file.pack()

        frm_inputs = ttk.Frame(self)
        frm_inputs.pack(pady=10)
        ttk.Label(frm_inputs, text="Start time (DD/MM/YYYY HH:mm:ss:SSS)").grid(row=0, column=0, sticky="e")
        ttk.Label(frm_inputs, text="End time (DD/MM/YYYY HH:mm:ss:SSS)").grid(row=1, column=0, sticky="e")
        self.start_entry = ttk.Entry(frm_inputs, width=30)
        self.start_entry.grid(row=0, column=1, padx=5, pady=2)
        self.end_entry = ttk.Entry(frm_inputs, width=30)
        self.end_entry.grid(row=1, column=1, padx=5, pady=2)

        self.btn_extract = ttk.Button(self, text="Extract", command=self.on_extract)
        self.btn_extract.pack(pady=10)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("MKV files", "*.mkv"), ("All files", "*.*")])
        if path:
            self.video_path = path
            self.lbl_file.config(text=os.path.basename(path))

    def on_extract(self):
        if not self.video_path:
            messagebox.showerror("Error", "No video selected")
            return
        start_str = self.start_entry.get().strip()
        end_str = self.end_entry.get().strip()
        try:
            start_ts = datetime.strptime(start_str, "%d/%m/%Y %H:%M:%S:%f")
            end_ts = datetime.strptime(end_str, "%d/%m/%Y %H:%M:%S:%f")
        except ValueError:
            messagebox.showerror("Error", "Invalid timestamp format")
            return
        try:
            output_path = os.path.join(os.path.dirname(self.video_path), "snippet.mp4")
            extract_snippet(self.video_path, start_ts, end_ts, output_path)
            messagebox.showinfo("Done", f"Snippet saved to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
