"""
Batch Extract Script for VidExtract.

This script allows the user to select a parent directory containing subfolders with rangetime.txt files.
It processes each subfolder, extracting video segments based on the timestamps in the rangetime.txt files.
"""

import sys
import os
import re
import threading
import csv
from datetime import datetime
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox

# Import components from main.py
from main import (
    extract_snippet,
    OCRConfig,
    parse_timestamp,
    TIMESTAMP_PATTERNS,
)

# Import UI class
from ui_batch import Ui_BatchExtractWindow

# Add a new timestamp pattern for the rangetime.txt format (YYYYMMDD_hhmmss.SSS)
RANGETIME_PATTERN = (re.compile(r"(\d{8}_\d{6}\.\d{3})"), "%Y%m%d_%H%M%S.%f")

def convert_rangetime_timestamp(timestamp_str):
    """
    Convert a timestamp from YYYYMMDD_hhmmss.SSS format to a datetime object.

    Args:
        timestamp_str: Timestamp string in YYYYMMDD_hhmmss.SSS format

    Returns:
        datetime object or None if conversion fails
    """
    try:
        # Parse the timestamp using the rangetime pattern
        dt = datetime.strptime(timestamp_str, RANGETIME_PATTERN[1])
        return dt
    except ValueError:
        return None

def process_rangetime_file(rangetime_path, video_path, callback=None):
    """
    Process a rangetime.txt file and extract video segments.

    Args:
        rangetime_path: Path to the rangetime.txt file
        video_path: Path to the video file
        callback: Optional callback function for progress updates

    Returns:
        List of (start_time, end_time, output_path) tuples for extracted segments
    """
    if callback:
        callback(0, f"Processing {rangetime_path}")

    # Get the directory containing the rangetime.txt file
    output_dir = os.path.dirname(rangetime_path)

    # Read the rangetime.txt file
    segments = []
    try:
        with open(rangetime_path, 'r') as f:
            reader = csv.reader(f)
            # Skip header row
            next(reader, None)

            for row in reader:
                if len(row) >= 2:
                    start_str = row[0].strip()
                    end_str = row[1].strip()

                    # Convert timestamps to datetime objects
                    start_time = convert_rangetime_timestamp(start_str)
                    end_time = convert_rangetime_timestamp(end_str)

                    if start_time and end_time:
                        # Define output path
                        output_path = os.path.join(output_dir, "video.avi")
                        segments.append((start_time, end_time, output_path))
                    else:
                        if callback:
                            callback(0, f"Error: Invalid timestamp format in {rangetime_path}")
    except Exception as e:
        if callback:
            callback(0, f"Error reading {rangetime_path}: {str(e)}")

    return segments

def extract_batch_segments(video_path, parent_dir, callback=None):
    """
    Extract video segments for all subfolders in the parent directory.

    Args:
        video_path: Path to the video file
        parent_dir: Path to the parent directory containing subfolders with rangetime.txt files
        callback: Optional callback function for progress updates

    Returns:
        Number of successfully processed segments
    """
    if callback:
        callback(0, f"Scanning {parent_dir} for rangetime.txt files")

    # Find all rangetime.txt files in subfolders
    rangetime_files = []
    for root, dirs, files in os.walk(parent_dir):
        for file in files:
            if file.lower() == "rangetime.txt":
                rangetime_files.append(os.path.join(root, file))

    if not rangetime_files:
        if callback:
            callback(0, "No rangetime.txt files found")
        return 0

    if callback:
        callback(0, f"Found {len(rangetime_files)} rangetime.txt files")

    # Process each rangetime.txt file
    total_segments = 0
    processed_segments = 0

    # First, collect all segments to process
    all_segments = []
    for rangetime_path in rangetime_files:
        segments = process_rangetime_file(rangetime_path, video_path, callback)
        all_segments.extend(segments)
        total_segments += len(segments)

    if total_segments == 0:
        if callback:
            callback(0, "No valid segments found in rangetime.txt files")
        return 0

    # Create OCR config
    ocr_config = OCRConfig()

    # Process each segment
    for i, (start_time, end_time, output_path) in enumerate(all_segments):
        if callback:
            progress = int(i * 100 / total_segments)
            callback(progress, f"Processing segment {i+1}/{total_segments}")

        try:
            # Create a callback function that updates progress for this segment
            def segment_callback(segment_progress, status_text):
                if callback:
                    # Scale the progress to the overall progress
                    overall_progress = int(((i * 100) + segment_progress) / total_segments)
                    callback(overall_progress, f"Segment {i+1}/{total_segments}: {status_text}")

            # Add buffer: subtract 1 minute from start time and add 1 minute to end time
            from datetime import timedelta
            buffered_start_time = start_time - timedelta(minutes=1)
            buffered_end_time = end_time + timedelta(minutes=1)

            # Extract the segment with buffered timestamps
            extract_snippet(video_path, buffered_start_time, buffered_end_time, output_path, segment_callback, ocr_config)
            processed_segments += 1

            if callback:
                callback(int((i+1) * 100 / total_segments), f"Completed segment {i+1}/{total_segments}")

        except Exception as e:
            if callback:
                callback(int((i+1) * 100 / total_segments), f"Error processing segment {i+1}/{total_segments}: {str(e)}")

    return processed_segments

class BatchExtractWindow(QMainWindow):
    """Main window for the batch extract application."""

    # Define signals
    stop_pulse_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()

        # Initialize UI from .ui file
        self.ui = Ui_BatchExtractWindow()
        self.ui.setupUi(self)

        # Initialize variables
        self.video_path = None
        self.parent_dir = None
        self.processing = False
        self.progress_timer = None

        # Connect signals to slots
        self.stop_pulse_signal.connect(self._stop_progress_pulse_slot)
        self.ui.select_file_button.clicked.connect(self.select_file)
        self.ui.select_dir_button.clicked.connect(self.select_directory)
        self.ui.extract_button.clicked.connect(self.on_extract)
        self.ui.close_button.clicked.connect(self.close)

        # Set initial UI state
        self.ui.progress_bar.setValue(0)
        self.ui.status_label.setText("Ready")

        # Initialize status text area with instructions
        self.ui.status_text.clear()
        self.log_status("Welcome to VidExtract Batch Extract")
        self.log_status("1. Select a video file using the 'Select Video' button")
        self.log_status("2. Select a parent directory containing subfolders with rangetime.txt files")
        self.log_status("3. Click 'Extract' to process all subfolders")
        self.log_status("Status messages will appear here during processing")


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
            self.ui.file_path_label.setText(os.path.basename(path))

    def select_directory(self):
        """Handle directory selection."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Parent Directory"
        )
        if path:
            self.parent_dir = path
            self.ui.dir_path_label.setText(path)

    def on_extract(self):
        """Handle the extract button click event."""
        if self.processing:
            QMessageBox.information(self, "Info", "Processing is already in progress")
            return

        if not self.video_path:
            QMessageBox.critical(self, "Error", "No video selected")
            return

        if not self.parent_dir:
            QMessageBox.critical(self, "Error", "No parent directory selected")
            return

        # Disable UI elements during processing
        self.processing = True
        self.ui.extract_button.setEnabled(False)
        self.ui.select_file_button.setEnabled(False)
        self.ui.select_dir_button.setEnabled(False)
        self.ui.progress_bar.setValue(0)
        self.ui.status_label.setText("Starting batch extraction...")

        # Clear status log for new operation
        self.clear_status_log()

        # Set wait cursor to indicate processing
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))

        # Start progress bar pulsing animation
        self.start_progress_pulse()

        # Run extraction in a separate thread to keep UI responsive
        def extraction_thread():
            try:
                processed_segments = extract_batch_segments(
                    self.video_path,
                    self.parent_dir,
                    self.update_progress
                )

                # Show success message on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self, 
                    "show_success_message", 
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(int, processed_segments)
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

    def update_progress(self, progress, status_text):
        """Update the progress bar and status label.

        Args:
            progress: Progress value (0-100)
            status_text: Status text to display
        """
        # Stop pulsing if we're getting actual progress updates
        # Use signal to stop the timer in the main thread
        self.stop_pulse_signal.emit()

        # Update UI in the main thread using invokeMethod if called from another thread
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(
                self,
                "_update_progress_main_thread",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(int, progress),
                QtCore.Q_ARG(str, status_text)
            )
        else:
            self._update_progress_main_thread(progress, status_text)

    @QtCore.pyqtSlot(int, str)
    def _update_progress_main_thread(self, progress, status_text):
        """Update the progress bar and status label in the main thread.

        Args:
            progress: Progress value (0-100)
            status_text: Status text to display
        """
        self.ui.progress_bar.setValue(progress)
        self.ui.status_label.setText(status_text)

        # Log the status message to the text area
        self.log_status(status_text)

        QApplication.processEvents()  # Force update of the UI

    def log_status(self, message):
        """Append a status message to the status text edit with timestamp.

        Args:
            message: Status message to append
        """
        # Update UI in the main thread using invokeMethod if called from another thread
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(
                self,
                "_log_status_main_thread",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, message)
            )
        else:
            self._log_status_main_thread(message)

    @QtCore.pyqtSlot(str)
    def _log_status_main_thread(self, message):
        """Append a status message to the status text edit with timestamp in the main thread.

        Args:
            message: Status message to append
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.status_text.append(f"[{timestamp}] {message}")

        # Scroll to the bottom
        self.ui.status_text.verticalScrollBar().setValue(
            self.ui.status_text.verticalScrollBar().maximum()
        )

        QApplication.processEvents()  # Force update of the UI

    def clear_status_log(self):
        """Clear the status text edit."""
        # Update UI in the main thread using invokeMethod if called from another thread
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(
                self,
                "_clear_status_log_main_thread",
                QtCore.Qt.ConnectionType.QueuedConnection
            )
        else:
            self._clear_status_log_main_thread()

    @QtCore.pyqtSlot()
    def _clear_status_log_main_thread(self):
        """Clear the status text edit in the main thread."""
        self.ui.status_text.clear()
        QApplication.processEvents()  # Force update of the UI

    def start_progress_pulse(self):
        """Start the progress bar pulsing animation."""
        if self.progress_timer is None:
            self.progress_timer = QtCore.QTimer(self)
            self.progress_timer.timeout.connect(self._update_pulse)
            self.progress_timer.start(100)  # Update every 100ms

    def _update_pulse(self):
        """Update the progress bar pulse animation."""
        value = self.ui.progress_bar.value()
        if value >= 99:
            value = 0
        else:
            value += 1
        self.ui.progress_bar.setValue(value)

    def stop_progress_pulse(self):
        """Stop the progress bar pulsing animation."""
        # Emit signal to stop the timer in the main thread
        self.stop_pulse_signal.emit()

    @QtCore.pyqtSlot()
    def _stop_progress_pulse_slot(self):
        """Slot method to stop the progress pulse timer in the main thread."""
        if self.progress_timer is not None:
            self.progress_timer.stop()
            self.progress_timer = None

    @QtCore.pyqtSlot(int)
    def show_success_message(self, processed_segments):
        """Show success message dialog."""
        # Restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()
        QMessageBox.information(
            self, 
            "Done", 
            f"Batch extraction complete. Processed {processed_segments} segments."
        )

    @QtCore.pyqtSlot(str)
    def show_error_message(self, error_message):
        """Show error message dialog."""
        # Restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Error", error_message)

    @QtCore.pyqtSlot()
    def reset_ui(self):
        """Reset the UI after processing is complete."""
        self.processing = False
        self.ui.extract_button.setEnabled(True)
        self.ui.select_file_button.setEnabled(True)
        self.ui.select_dir_button.setEnabled(True)
        self.stop_progress_pulse()
        self.ui.progress_bar.setValue(100)
        self.ui.status_label.setText("Ready")

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    window = BatchExtractWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
