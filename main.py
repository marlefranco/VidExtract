import sys
import cv2
import pytesseract
import re
from datetime import datetime
import os
import threading
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox
from ui import Ui_MainWindow

"""
VidExtract - A tool to extract video snippets based on timestamp overlays.

This application extracts a video snippet from an MKV file based on timestamp overlays
that appear on the top-right corner of the frames. The timestamps must be in the format
DD/MM/YYYY HH:mm:ss:SSS.

Future improvements:
1. Add support for more video formats beyond MKV
2. Allow customization of the timestamp format and position
3. Add options to configure OCR parameters for better recognition
4. Implement a preview feature to verify timestamp detection
"""

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


def find_frame_for_time(cap, target_time, frame_sampling=10, cache=None):
    """Find the frame corresponding to the target timestamp with frame sampling and caching.

    Args:
        cap: Video capture object
        target_time: Target timestamp to find
        frame_sampling: Sample every Nth frame (default: 10)
        cache: Dictionary to cache OCR results (default: None)

    Returns:
        Frame number or None if not found

    Raises:
        RuntimeError: If Tesseract OCR is not installed or not in PATH
    """
    if cache is None:
        cache = {}

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    region_width = 300
    region_height = 50
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    x_start = max(0, width - region_width)

    # First pass: Sample frames at intervals
    frame_num = 0
    last_valid_ts = None
    last_valid_frame = None

    while frame_num < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            break

        # Check if this frame is already in cache
        if frame_num in cache:
            ts = cache[frame_num]
        else:
            overlay = frame[0:region_height, x_start:width]
            gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(gray, config='--psm 7')
                ts = parse_timestamp(text)
                cache[frame_num] = ts
            except Exception as e:
                error_msg = str(e)
                if "tesseract is not installed" in error_msg.lower() or "tesseract not found" in error_msg.lower():
                    raise RuntimeError(
                        "Tesseract OCR is not installed or not in your PATH. "
                        "Please install Tesseract OCR and make sure it's in your system PATH. "
                        "See the README.md file for more information."
                    )
                # For other OCR errors, continue with no timestamp
                ts = None
                cache[frame_num] = None

        if ts:
            if ts >= target_time:
                # If we found a timestamp after our target, we need to search more precisely
                if last_valid_ts and last_valid_ts < target_time:
                    # We have a range to search in
                    return binary_search_frames(cap, last_valid_frame, frame_num, target_time, cache)
                return frame_num
            last_valid_ts = ts
            last_valid_frame = frame_num

        frame_num += frame_sampling

    # If we didn't find an exact match but have a valid timestamp before target
    if last_valid_frame is not None:
        return last_valid_frame

    return None

def binary_search_frames(cap, start_frame, end_frame, target_time, cache):
    """Binary search between two frames to find the closest match to target time.

    Args:
        cap: Video capture object
        start_frame: Starting frame number
        end_frame: Ending frame number
        target_time: Target timestamp to find
        cache: Dictionary to cache OCR results

    Returns:
        Frame number closest to target time

    Raises:
        RuntimeError: If Tesseract OCR is not installed or not in PATH
    """
    region_width = 300
    region_height = 50
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    x_start = max(0, width - region_width)

    while start_frame <= end_frame:
        mid_frame = (start_frame + end_frame) // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        if not ret:
            return start_frame

        # Check if this frame is already in cache
        if mid_frame in cache:
            ts = cache[mid_frame]
        else:
            overlay = frame[0:region_height, x_start:width]
            gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(gray, config='--psm 7')
                ts = parse_timestamp(text)
                cache[mid_frame] = ts
            except Exception as e:
                error_msg = str(e)
                if "tesseract is not installed" in error_msg.lower() or "tesseract not found" in error_msg.lower():
                    raise RuntimeError(
                        "Tesseract OCR is not installed or not in your PATH. "
                        "Please install Tesseract OCR and make sure it's in your system PATH. "
                        "See the README.md file for more information."
                    )
                # For other OCR errors, continue with no timestamp
                ts = None
                cache[mid_frame] = None

        if not ts:
            # If no timestamp found, try the next frame
            start_frame = mid_frame + 1
            continue

        if ts < target_time:
            start_frame = mid_frame + 1
        elif ts > target_time:
            end_frame = mid_frame - 1
        else:
            # Exact match
            return mid_frame

    # Return the closest frame
    return start_frame


def extract_snippet(video_path, start_time, end_time, output_path, callback=None):
    """Extract a video snippet between start_time and end_time.

    Args:
        video_path: Path to the source video
        start_time: Start timestamp
        end_time: End timestamp
        output_path: Path to save the output video
        callback: Optional callback function for progress updates

    Raises:
        RuntimeError: If video can't be opened, timestamps not found, or no frames extracted
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Unable to open video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Initialize OCR cache
    ocr_cache = {}

    # Update callback with initial status
    if callback:
        callback(0, "Searching for start time...")

    # Find start frame with sampling and caching
    start_frame = find_frame_for_time(cap, start_time, frame_sampling=15, cache=ocr_cache)
    if start_frame is None:
        raise RuntimeError("Start time not found in video. Please check the timestamp format.")

    # Update callback
    if callback:
        callback(10, "Start time found. Searching for end time...")

    # Find end frame with sampling and caching
    # First try to find it from the start frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    end_frame = None
    region_height = 50
    region_width = 300
    x_start = max(0, width - region_width)

    # Sample frames to find end time
    frame_sampling = 15
    current_frame = start_frame
    frames_to_extract = []

    while current_frame < total_frames:
        if callback:
            progress = 10 + int(40 * (current_frame - start_frame) / (total_frames - start_frame))
            callback(progress, "Searching for end time...")

        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret:
            break

        # Check if this frame is already in cache
        if current_frame in ocr_cache:
            ts = ocr_cache[current_frame]
        else:
            overlay = frame[0:region_height, x_start:width]
            gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(gray, config='--psm 7')
                ts = parse_timestamp(text)
                ocr_cache[current_frame] = ts
            except Exception as e:
                error_msg = str(e)
                if "tesseract is not installed" in error_msg.lower() or "tesseract not found" in error_msg.lower():
                    raise RuntimeError(
                        "Tesseract OCR is not installed or not in your PATH. "
                        "Please install Tesseract OCR and make sure it's in your system PATH. "
                        "See the README.md file for more information."
                    )
                # For other OCR errors, continue with no timestamp
                ts = None
                ocr_cache[current_frame] = None

        if ts and ts >= end_time:
            end_frame = current_frame
            break

        frames_to_extract.append(frame)
        current_frame += frame_sampling

    # If we didn't find the end time with sampling, use the last frame
    if end_frame is None:
        if callback:
            callback(50, "End time not found. Using all remaining frames...")

        # Continue reading frames sequentially
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames_to_extract.append(frame)
    else:
        # We found the end frame with sampling, now get all frames between start and end
        if callback:
            callback(50, "End time found. Extracting frames...")

        # If we used sampling, we need to fill in the gaps
        if frame_sampling > 1:
            # Clear the frames we collected during sampling
            frames_to_extract = []

            # Read all frames between start and end
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            for i in range(start_frame, end_frame):
                if callback and i % 30 == 0:
                    progress = 50 + int(40 * (i - start_frame) / (end_frame - start_frame))
                    callback(progress, "Extracting frames...")

                ret, frame = cap.read()
                if not ret:
                    break
                frames_to_extract.append(frame)

    cap.release()

    if not frames_to_extract:
        raise RuntimeError("No frames extracted. Please check the timestamps.")

    if callback:
        callback(90, "Writing output video...")

    # Write the output video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for i, fr in enumerate(frames_to_extract):
        if callback and i % 30 == 0:
            progress = 90 + int(10 * i / len(frames_to_extract))
            callback(progress, "Writing output video...")
        out.write(fr)

    out.release()

    if callback:
        callback(100, "Done!")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Initialize variables
        self.video_path = None
        self.processing = False

        # Connect signals to slots
        self.ui.selectFileButton.clicked.connect(self.select_file)
        self.ui.extractButton.clicked.connect(self.on_extract)
        self.ui.actionOpen.triggered.connect(self.select_file)
        self.ui.actionExit.triggered.connect(self.close)

        # Set initial UI state
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Ready")

    def select_file(self):
        """Handle file selection."""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File", 
            "", 
            "MKV files (*.mkv);;All files (*.*)"
        )
        if path:
            self.video_path = path
            self.ui.filePathLabel.setText(os.path.basename(path))

    def update_progress(self, progress, status_text):
        """Update the progress bar and status label.

        Args:
            progress: Progress value (0-100)
            status_text: Status text to display
        """
        self.ui.progressBar.setValue(progress)
        self.ui.statusLabel.setText(status_text)
        QApplication.processEvents()  # Force update of the UI

    def on_extract(self):
        """Handle the extract button click event."""
        if self.processing:
            QMessageBox.information(self, "Info", "Processing is already in progress")
            return

        if not self.video_path:
            QMessageBox.critical(self, "Error", "No video selected")
            return

        start_str = self.ui.startTimeEdit.text().strip()
        end_str = self.ui.endTimeEdit.text().strip()

        # Validate timestamps
        try:
            start_ts = datetime.strptime(start_str, "%d/%m/%Y %H:%M:%S:%f")
            end_ts = datetime.strptime(end_str, "%d/%m/%Y %H:%M:%S:%f")

            if start_ts >= end_ts:
                QMessageBox.critical(self, "Error", "Start time must be before end time")
                return
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid timestamp format. Use DD/MM/YYYY HH:mm:ss:SSS")
            return

        # Disable UI elements during processing
        self.processing = True
        self.ui.extractButton.setEnabled(False)
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Starting extraction...")

        # Run extraction in a separate thread to keep UI responsive
        def extraction_thread():
            try:
                output_path = os.path.join(os.path.dirname(self.video_path), "snippet.mp4")
                extract_snippet(self.video_path, start_ts, end_ts, output_path, self.update_progress)

                # Show success message on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self, 
                    "show_success_message", 
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, output_path)
                )

            except Exception as e:
                # Show error message on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self, 
                    "show_error_message", 
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, str(e))
                )

            finally:
                # Re-enable UI elements on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self, 
                    "reset_ui", 
                    QtCore.Qt.ConnectionType.QueuedConnection
                )

        # Start extraction thread
        thread = threading.Thread(target=extraction_thread)
        thread.daemon = True
        thread.start()

    @QtCore.pyqtSlot(str)
    def show_success_message(self, output_path):
        """Show success message dialog."""
        QMessageBox.information(self, "Done", f"Snippet saved to {output_path}")

    @QtCore.pyqtSlot(str)
    def show_error_message(self, error_message):
        """Show error message dialog."""
        QMessageBox.critical(self, "Error", error_message)

    @QtCore.pyqtSlot()
    def reset_ui(self):
        """Reset UI elements after processing."""
        self.processing = False
        self.ui.extractButton.setEnabled(True)
        self.ui.statusLabel.setText("Ready")


def check_tesseract_installed():
    """Check if Tesseract OCR is installed and available in PATH."""
    try:
        # Try to get tesseract version
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        # If any exception occurs, Tesseract is not properly installed or configured
        return False

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Check if Tesseract is installed
    if not check_tesseract_installed():
        QMessageBox.critical(
            None, 
            "Tesseract OCR Not Found", 
            "Tesseract OCR is not installed or not in your PATH.\n\n"
            "Please install Tesseract OCR and make sure it's in your system PATH.\n"
            "See the README.md file for more information."
        )
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
