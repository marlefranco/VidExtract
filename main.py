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

# Uncomment and modify the line below to set a custom path to Tesseract OCR executable
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows example
# pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # macOS/Linux example

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

# Default timestamp patterns with their corresponding datetime format strings
TIMESTAMP_PATTERNS = [
    # DD/MM/YYYY HH:mm:ss:SSS (default)
    (re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}:\d{3})"), "%d/%m/%Y %H:%M:%S:%f"),
    # MM/DD/YYYY HH:mm:ss:SSS
    (re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}:\d{3})"), "%m/%d/%Y %H:%M:%S:%f"),
    # YYYY-MM-DD HH:mm:ss.SSS
    (re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"), "%Y-%m-%d %H:%M:%S.%f"),
    # HH:mm:ss:SSS (time only)
    (re.compile(r"(\d{2}:\d{2}:\d{2}:\d{3})"), "%H:%M:%S:%f"),
    # HH:mm:ss.SSS (time only with dot)
    (re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3})"), "%H:%M:%S.%f"),
]


def parse_timestamp(text: str, patterns=None):
    """Parse timestamp from text using multiple patterns.

    Args:
        text: Text containing timestamp
        patterns: List of (regex, format) tuples to try (default: TIMESTAMP_PATTERNS)

    Returns:
        datetime object or None if no timestamp found
    """
    if patterns is None:
        patterns = TIMESTAMP_PATTERNS

    for pattern, format_str in patterns:
        match = pattern.search(text)
        if match:
            try:
                return datetime.strptime(match.group(1), format_str)
            except ValueError:
                # Try next pattern if this one doesn't work
                continue

    return None


class OCRConfig:
    """Configuration for OCR processing."""

    # Predefined regions
    REGION_TOP_RIGHT = "top-right"
    REGION_TOP_LEFT = "top-left"
    REGION_BOTTOM_RIGHT = "bottom-right"
    REGION_BOTTOM_LEFT = "bottom-left"
    REGION_CUSTOM = "custom"

    def __init__(self):
        # Default values
        self.region = self.REGION_TOP_RIGHT
        self.region_width = 300
        self.region_height = 50
        self.custom_x = 0
        self.custom_y = 0
        self.custom_width = 300
        self.custom_height = 50
        self.patterns = TIMESTAMP_PATTERNS

    def get_region_coords(self, frame_width, frame_height):
        """Get the coordinates for the region of interest based on the current configuration.

        Args:
            frame_width: Width of the video frame
            frame_height: Height of the video frame

        Returns:
            Tuple of (x_start, y_start, width, height)
        """
        if self.region == self.REGION_TOP_RIGHT:
            return (max(0, frame_width - self.region_width), 0, 
                    self.region_width, self.region_height)
        elif self.region == self.REGION_TOP_LEFT:
            return (0, 0, self.region_width, self.region_height)
        elif self.region == self.REGION_BOTTOM_RIGHT:
            return (max(0, frame_width - self.region_width), 
                    max(0, frame_height - self.region_height),
                    self.region_width, self.region_height)
        elif self.region == self.REGION_BOTTOM_LEFT:
            return (0, max(0, frame_height - self.region_height),
                    self.region_width, self.region_height)
        elif self.region == self.REGION_CUSTOM:
            return (self.custom_x, self.custom_y, 
                    self.custom_width, self.custom_height)
        else:
            # Default to top-right if invalid region
            return (max(0, frame_width - self.region_width), 0, 
                    self.region_width, self.region_height)


def find_frame_for_time(cap, target_time, frame_sampling=10, cache=None, ocr_config=None):
    """Find the frame corresponding to the target timestamp with adaptive frame sampling and caching.

    Args:
        cap: Video capture object
        target_time: Target timestamp to find
        frame_sampling: Initial sample every Nth frame (default: 10)
        cache: Dictionary to cache OCR results (default: None)
        ocr_config: OCR configuration (default: None, uses default config)

    Returns:
        Frame number or None if not found

    Raises:
        RuntimeError: If Tesseract OCR is not installed or not in PATH
    """
    if cache is None:
        cache = {}

    if ocr_config is None:
        ocr_config = OCRConfig()

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Get region coordinates based on configuration
    x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

    # First pass: Sample frames at intervals with adaptive sampling
    frame_num = 0
    last_valid_ts = None
    last_valid_frame = None

    # Start with a larger sampling interval for efficiency
    adaptive_sampling = min(frame_sampling * 3, 30)  # Start with larger interval but cap at 30
    consecutive_failures = 0
    max_consecutive_failures = 5  # Reduce sampling rate after this many failures

    while frame_num < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            break

        # Adjust sampling rate based on success/failure and proximity to target
        if last_valid_ts is not None:
            # If we're getting closer to the target time, reduce sampling interval
            time_diff = abs((target_time - last_valid_ts).total_seconds())
            if time_diff < 60:  # Within a minute of target
                adaptive_sampling = max(1, min(adaptive_sampling, int(frame_sampling * 0.5)))
            elif time_diff < 300:  # Within 5 minutes of target
                adaptive_sampling = max(1, min(adaptive_sampling, frame_sampling))

        # Check if this frame is already in cache
        if frame_num in cache:
            ts = cache[frame_num]
        else:
            overlay = frame[y_start:y_start+region_height, x_start:x_start+region_width]
            gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(gray, config='--psm 7')
                ts = parse_timestamp(text, ocr_config.patterns)
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
            consecutive_failures = 0  # Reset failure counter on success
            if ts >= target_time:
                # If we found a timestamp after our target, we need to search more precisely
                if last_valid_ts and last_valid_ts < target_time:
                    # We have a range to search in
                    return binary_search_frames(cap, last_valid_frame, frame_num, target_time, cache, ocr_config)
                return frame_num
            last_valid_ts = ts
            last_valid_frame = frame_num
        else:
            # No timestamp found, count as a failure
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                # Too many failures, reduce sampling interval to avoid missing timestamps
                adaptive_sampling = max(1, int(adaptive_sampling * 0.5))
                consecutive_failures = 0  # Reset counter

        frame_num += adaptive_sampling

    # If we didn't find an exact match but have a valid timestamp before target
    if last_valid_frame is not None:
        return last_valid_frame

    return None

def binary_search_frames(cap, start_frame, end_frame, target_time, cache, ocr_config=None):
    """Binary search between two frames to find the closest match to target time.

    Args:
        cap: Video capture object
        start_frame: Starting frame number
        end_frame: Ending frame number
        target_time: Target timestamp to find
        cache: Dictionary to cache OCR results
        ocr_config: OCR configuration (default: None, uses default config)

    Returns:
        Frame number closest to target time

    Raises:
        RuntimeError: If Tesseract OCR is not installed or not in PATH
    """
    if ocr_config is None:
        ocr_config = OCRConfig()

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Get region coordinates based on configuration
    x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

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
            overlay = frame[y_start:y_start+region_height, x_start:x_start+region_width]
            gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(gray, config='--psm 7')
                ts = parse_timestamp(text, ocr_config.patterns)
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


def extract_snippet(video_path, start_time, end_time, output_path, callback=None, ocr_config=None):
    """Extract a video snippet between start_time and end_time.

    Args:
        video_path: Path to the source video
        start_time: Start timestamp
        end_time: End timestamp
        output_path: Path to save the output video
        callback: Optional callback function for progress updates
        ocr_config: OCR configuration (default: None, uses default config)

    Raises:
        RuntimeError: If video can't be opened, timestamps not found, or no frames extracted
    """
    if ocr_config is None:
        ocr_config = OCRConfig()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(
            "Unable to open video file. Please check that:\n"
            "1. The file exists and is not corrupted\n"
            "2. You have the necessary codecs installed\n"
            "3. The file is a supported video format"
        )

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
    start_frame = find_frame_for_time(cap, start_time, frame_sampling=15, cache=ocr_cache, ocr_config=ocr_config)
    if start_frame is None:
        raise RuntimeError(
            "Start time not found in video. Please check that:\n"
            "1. The timestamp format matches what appears in the video\n"
            "2. The timestamp is visible in the selected region\n"
            "3. The video contains frames with the specified timestamp\n"
            "4. The OCR is able to recognize the text (try the Preview feature)"
        )

    # Update callback
    if callback:
        callback(10, "Start time found. Searching for end time...")

    # Find end frame with sampling and caching
    # First try to find it from the start frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    end_frame = None

    # Get region coordinates based on configuration
    x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

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
            overlay = frame[y_start:y_start+region_height, x_start:x_start+region_width]
            gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(gray, config='--psm 7')
                ts = parse_timestamp(text, ocr_config.patterns)
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

        # Process frames in chunks to limit memory usage
    max_frames_in_memory = 100  # Maximum number of frames to keep in memory at once

    if callback:
        callback(50, "Preparing for extraction...")

    # Create output video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # If we found the end frame, process all frames between start and end
    if end_frame is not None:
        total_frames_to_process = end_frame - start_frame
        frames_processed = 0

        # Process in chunks to limit memory usage
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        while frames_processed < total_frames_to_process:
            # Determine chunk size
            chunk_size = min(max_frames_in_memory, total_frames_to_process - frames_processed)
            chunk_frames = []

            # Read chunk of frames
            for i in range(chunk_size):
                if callback and (frames_processed + i) % 30 == 0:
                    progress = 50 + int(40 * (frames_processed + i) / total_frames_to_process)
                    callback(progress, f"Extracting frames... ({frames_processed + i}/{total_frames_to_process})")

                ret, frame = cap.read()
                if not ret:
                    break
                chunk_frames.append(frame)

            # Write chunk to output
            for i, fr in enumerate(chunk_frames):
                if callback and i % 30 == 0:
                    progress = 90 + int(10 * (frames_processed + i) / total_frames_to_process)
                    callback(progress, f"Writing output... ({frames_processed + i}/{total_frames_to_process})")
                out.write(fr)

            frames_processed += len(chunk_frames)
            chunk_frames = []  # Clear memory
    else:
        # If we didn't find the end frame, use the frames we collected during sampling
        if not frames_to_extract:
            raise RuntimeError(
                "No frames extracted. Please check that:\n"
                "1. The start time is before the end time\n"
                "2. Both timestamps exist in the video\n"
                "3. The time range between start and end contains frames\n"
                "4. The OCR is correctly recognizing the timestamps (try the Preview feature)"
            )

        total_frames = len(frames_to_extract)

        # Process in chunks to limit memory usage
        for i in range(0, total_frames, max_frames_in_memory):
            chunk = frames_to_extract[i:i + max_frames_in_memory]

            for j, fr in enumerate(chunk):
                if callback and (i + j) % 30 == 0:
                    progress = 90 + int(10 * (i + j) / total_frames)
                    callback(progress, f"Writing output... ({i + j}/{total_frames})")
                out.write(fr)

    cap.release()

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
        self.ocr_config = OCRConfig()
        self.preview_dialog = None

        # Connect signals to slots
        self.ui.selectFileButton.clicked.connect(self.select_file)
        self.ui.extractButton.clicked.connect(self.on_extract)
        self.ui.actionOpen.triggered.connect(self.select_file)
        self.ui.actionExit.triggered.connect(self.close)

        # Add preview button if it exists in the UI
        try:
            self.ui.previewButton.clicked.connect(self.on_preview)
        except AttributeError:
            # If the button doesn't exist in the UI, create it
            self.ui.previewButton = QtWidgets.QPushButton("Preview")
            self.ui.previewButton.setMinimumSize(QtCore.QSize(100, 30))
            self.ui.previewButton.setStyleSheet("background-color: #333333; border-radius: 4px;")
            # Add it to the layout before the extract button
            layout = self.ui.extractButton.parent().layout()
            layout.insertWidget(layout.indexOf(self.ui.extractButton), self.ui.previewButton)
            self.ui.previewButton.clicked.connect(self.on_preview)

        # Set initial UI state
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Ready")

    def select_file(self):
        """Handle file selection."""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File", 
            "", 
            "Video files (*.mkv *.mp4 *.avi *.mov *.wmv);;MKV files (*.mkv);;MP4 files (*.mp4);;AVI files (*.avi);;MOV files (*.mov);;WMV files (*.wmv);;All files (*.*)"
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
            # Check if timestamps are empty
            if not start_str or not end_str:
                QMessageBox.critical(self, "Error", "Start and end timestamps are required")
                return

            # Try to parse with multiple formats
            start_ts = None
            end_ts = None

            # Try each pattern in the OCR config
            for pattern, format_str in self.ocr_config.patterns:
                try:
                    if not start_ts:
                        start_ts = datetime.strptime(start_str, format_str)
                    if not end_ts:
                        end_ts = datetime.strptime(end_str, format_str)

                    # If both timestamps are parsed, break
                    if start_ts and end_ts:
                        break
                except ValueError:
                    continue

            # If we couldn't parse the timestamps
            if not start_ts:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Invalid start timestamp format: {start_str}\n\n"
                    "Please use one of the supported formats:\n"
                    "- DD/MM/YYYY HH:mm:ss:SSS\n"
                    "- MM/DD/YYYY HH:mm:ss:SSS\n"
                    "- YYYY-MM-DD HH:mm:ss.SSS\n"
                    "- HH:mm:ss:SSS\n"
                    "- HH:mm:ss.SSS"
                )
                return

            if not end_ts:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Invalid end timestamp format: {end_str}\n\n"
                    "Please use one of the supported formats:\n"
                    "- DD/MM/YYYY HH:mm:ss:SSS\n"
                    "- MM/DD/YYYY HH:mm:ss:SSS\n"
                    "- YYYY-MM-DD HH:mm:ss.SSS\n"
                    "- HH:mm:ss:SSS\n"
                    "- HH:mm:ss.SSS"
                )
                return

            # Check if start time is before end time
            if start_ts >= end_ts:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    "Start time must be before end time\n\n"
                    f"Start: {start_ts}\n"
                    f"End: {end_ts}"
                )
                return

            # Check if the time difference is reasonable (not too short or too long)
            time_diff = (end_ts - start_ts).total_seconds()
            if time_diff < 0.5:
                result = QMessageBox.warning(
                    self, 
                    "Warning", 
                    f"The time difference is very short ({time_diff:.2f} seconds).\n"
                    "This may result in very few or no frames being extracted.\n\n"
                    "Do you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result != QMessageBox.StandardButton.Yes:
                    return

            if time_diff > 3600:  # More than 1 hour
                result = QMessageBox.warning(
                    self, 
                    "Warning", 
                    f"The time difference is very long ({time_diff/3600:.2f} hours).\n"
                    "This may result in a very large output file and take a long time to process.\n\n"
                    "Do you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result != QMessageBox.StandardButton.Yes:
                    return

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error validating timestamps: {str(e)}")
            return

        # Disable UI elements during processing
        self.processing = True
        self.ui.extractButton.setEnabled(False)
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Starting extraction...")

        # Run extraction in a separate thread to keep UI responsive
        def extraction_thread():
            try:
                # Ask user for output file name and location
                default_name = f"snippet_{start_ts.strftime('%Y%m%d_%H%M%S')}.mp4"
                default_dir = os.path.dirname(self.video_path)
                output_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Output File",
                    os.path.join(default_dir, default_name),
                    "MP4 files (*.mp4);;MKV files (*.mkv);;AVI files (*.avi);;All files (*.*)"
                )

                if not output_path:
                    # User cancelled
                    return

                extract_snippet(self.video_path, start_ts, end_ts, output_path, self.update_progress, self.ocr_config)

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

    def on_preview(self):
        """Handle preview button click event."""
        if not self.video_path:
            QMessageBox.critical(self, "Error", "No video selected")
            return

        if self.processing:
            QMessageBox.information(self, "Info", "Processing is already in progress")
            return

        # Show a progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Generating preview...", "Cancel", 0, 0, self)
        progress_dialog.setWindowTitle("Preview")
        progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress_dialog.show()
        QApplication.processEvents()

        try:
            # Get frame from 10% of the video
            frame, timestamp, text = preview_timestamp_detection(self.video_path, None, self.ocr_config)

            if frame is None:
                QMessageBox.critical(self, "Error", text)
                return

            # Convert frame to QImage for display
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QtGui.QImage(frame.data, width, height, bytes_per_line, QtGui.QImage.Format.Format_RGB888).rgbSwapped()

            # Create a dialog to display the preview
            preview_dialog = QtWidgets.QDialog(self)
            preview_dialog.setWindowTitle("Timestamp Preview")
            preview_dialog.setMinimumSize(640, 480)

            # Create layout
            layout = QtWidgets.QVBoxLayout(preview_dialog)

            # Add image label
            image_label = QtWidgets.QLabel()
            image_label.setPixmap(QtGui.QPixmap.fromImage(q_img).scaled(
                600, 400, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            layout.addWidget(image_label)

            # Add timestamp info
            if timestamp:
                info_text = f"Detected timestamp: {timestamp.strftime('%d/%m/%Y %H:%M:%S:%f')[:-3]}"
            else:
                info_text = "No timestamp detected"

            info_label = QtWidgets.QLabel(info_text)
            layout.addWidget(info_label)

            # Add OCR text
            ocr_label = QtWidgets.QLabel(f"OCR text: {text}")
            ocr_label.setWordWrap(True)
            layout.addWidget(ocr_label)

            # Add close button
            close_button = QtWidgets.QPushButton("Close")
            close_button.clicked.connect(preview_dialog.accept)
            layout.addWidget(close_button)

            # Close progress dialog
            progress_dialog.close()

            # Show preview dialog
            preview_dialog.exec()

        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Error generating preview: {str(e)}")

    @QtCore.pyqtSlot()
    def reset_ui(self):
        """Reset UI elements after processing."""
        self.processing = False
        self.ui.extractButton.setEnabled(True)
        self.ui.statusLabel.setText("Ready")


def preview_timestamp_detection(video_path, frame_position=None, ocr_config=None):
    """Capture a frame from the video and detect timestamp for preview.

    Args:
        video_path: Path to the video file
        frame_position: Position of the frame to capture (default: None, uses 10% of video)
        ocr_config: OCR configuration (default: None, uses default config)

    Returns:
        Tuple of (frame, detected_timestamp, timestamp_text) or (None, None, error_message) on error
    """
    if ocr_config is None:
        ocr_config = OCRConfig()

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None, "Unable to open video file"

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # If no frame position specified, use 10% of the video
        if frame_position is None or frame_position <= 0:
            frame_position = int(total_frames * 0.1)

        # Ensure frame position is valid
        frame_position = min(frame_position, total_frames - 1)

        # Set position and read frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()
        if not ret:
            return None, None, "Failed to read frame from video"

        # Get frame dimensions
        height, width = frame.shape[:2]

        # Get region coordinates
        x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

        # Extract region for OCR
        region = frame[y_start:y_start+region_height, x_start:x_start+region_width]

        # Draw rectangle around the region on the original frame
        cv2.rectangle(frame, (x_start, y_start), (x_start+region_width, y_start+region_height), (0, 255, 0), 2)

        # Perform OCR
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 7')
        timestamp = parse_timestamp(text, ocr_config.patterns)

        cap.release()

        if timestamp:
            return frame, timestamp, text
        else:
            return frame, None, f"No timestamp detected. OCR text: {text}"

    except Exception as e:
        return None, None, f"Error during preview: {str(e)}"


def find_tesseract_executable():
    """Find the Tesseract executable on the system.

    Returns:
        Tuple of (success, path_or_error_message)
    """
    # First check if it's already configured and working
    try:
        version = pytesseract.get_tesseract_version()
        return True, f"Tesseract is properly configured (version {version})"
    except Exception:
        pass

    # Try to find Tesseract in common locations
    possible_locations = []

    # Windows common locations
    if os.name == 'nt':
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')

        possible_locations = [
            os.path.join(program_files, 'Tesseract-OCR', 'tesseract.exe'),
            os.path.join(program_files_x86, 'Tesseract-OCR', 'tesseract.exe'),
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
    # macOS and Linux common locations
    else:
        possible_locations = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',  # M1 Mac Homebrew
        ]

    # Check each location
    for location in possible_locations:
        if os.path.isfile(location):
            try:
                # Try to set and test this location
                pytesseract.pytesseract.tesseract_cmd = location
                version = pytesseract.get_tesseract_version()
                return True, f"Found Tesseract at {location} (version {version})"
            except Exception:
                continue

    # If we get here, Tesseract wasn't found or couldn't be configured
    return False, (
        "Tesseract OCR not found or not working. Please:\n"
        "1. Install Tesseract OCR from https://github.com/tesseract-ocr/tesseract\n"
        "2. Make sure it's in your system PATH\n"
        "3. Or uncomment and set pytesseract.pytesseract.tesseract_cmd in main.py"
    )


def check_tesseract_installed():
    """Check if Tesseract OCR is installed and available in PATH."""
    success, _ = find_tesseract_executable()
    return success

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Check if Tesseract is installed
    success, message = find_tesseract_executable()
    if not success:
        QMessageBox.critical(
            None, 
            "Tesseract OCR Not Found", 
            message
        )
        sys.exit(1)
    else:
        print(f"Tesseract status: {message}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
