import sys
import cv2
import pytesseract
import re
from datetime import datetime
import os
import threading
import math
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

The application prioritizes time over date when comparing timestamps, assuming that
video data collection happens on the same day. This means that even if the date part
of the timestamp changes, the application will still correctly extract snippets based
on the time range.

The application uses an optimized search algorithm that leverages the video's FPS and
initial timestamp readings to make intelligent jumps when searching for frames. This
significantly improves performance by reducing the number of frames that need to be
processed with OCR. The optimization works by:
1. Reading a frame from an early position in the video (10% of the way through) to get an initial timestamp
2. Using the video's FPS to estimate frame positions based on time differences
3. Using timestamp readings as reference points for both start and end timestamp searches
4. Jumping directly to estimated frame positions and then refining the search
5. Falling back to traditional search methods if the optimized approach fails

This approach avoids scanning from the beginning of the video, which can be very time-consuming
for large video files, especially when the target timestamps are far into the video.

Future improvements:
1. Add support for more video formats beyond MKV
2. Allow customization of the timestamp format and position
3. Add options to configure OCR parameters for better recognition
4. Implement a preview feature to verify timestamp detection
"""

# Default timestamp patterns with their corresponding datetime format strings
TIMESTAMP_PATTERNS = [
    # MM/DD/YYYY HH:mm:ss:SSS (default)
    (re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}:\d{3})"), "%m/%d/%Y %H:%M:%S:%f"),
    # DD/MM/YYYY HH:mm:ss:SSS
    (re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}:\d{3})"), "%d/%m/%Y %H:%M:%S:%f"),
    # YYYY-MM-DD HH:mm:ss.SSS
    (re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"), "%Y-%m-%d %H:%M:%S.%f"),
    # HH:mm:ss:SSS (time only)
    (re.compile(r"(\d{2}:\d{2}:\d{2}:\d{3})"), "%H:%M:%S:%f"),
    # HH:mm:ss.SSS (time only with dot)
    (re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3})"), "%H:%M:%S.%f"),
]


def compare_timestamps_by_time(ts1, ts2):
    """Compare two timestamps by time only, ignoring the date component.

    Args:
        ts1: First timestamp (datetime object)
        ts2: Second timestamp (datetime object)

    Returns:
        -1 if ts1's time is earlier than ts2's time
        0 if ts1's time is equal to ts2's time
        1 if ts1's time is later than ts2's time
    """
    if ts1 is None or ts2 is None:
        return 0

    # Extract time components
    t1 = ts1.time()
    t2 = ts2.time()

    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    else:
        return 0

def is_time_gte(ts1, ts2):
    """Check if ts1's time is greater than or equal to ts2's time, ignoring date.

    Args:
        ts1: First timestamp (datetime object)
        ts2: Second timestamp (datetime object)

    Returns:
        True if ts1's time is greater than or equal to ts2's time, False otherwise
    """
    return compare_timestamps_by_time(ts1, ts2) >= 0

def is_time_lt(ts1, ts2):
    """Check if ts1's time is less than ts2's time, ignoring date.

    Args:
        ts1: First timestamp (datetime object)
        ts2: Second timestamp (datetime object)

    Returns:
        True if ts1's time is less than ts2's time, False otherwise
    """
    return compare_timestamps_by_time(ts1, ts2) < 0

def is_time_gt(ts1, ts2):
    """Check if ts1's time is greater than ts2's time, ignoring date.

    Args:
        ts1: First timestamp (datetime object)
        ts2: Second timestamp (datetime object)

    Returns:
        True if ts1's time is greater than ts2's time, False otherwise
    """
    return compare_timestamps_by_time(ts1, ts2) > 0

def time_diff_seconds(ts1, ts2):
    """Calculate the time difference in seconds, ignoring date.

    Args:
        ts1: First timestamp (datetime object)
        ts2: Second timestamp (datetime object)

    Returns:
        Time difference in seconds (float)
    """
    if ts1 is None or ts2 is None:
        return 0

    # Extract time components
    t1 = ts1.time()
    t2 = ts2.time()

    # Convert to seconds since midnight
    t1_seconds = t1.hour * 3600 + t1.minute * 60 + t1.second + t1.microsecond / 1000000
    t2_seconds = t2.hour * 3600 + t2.minute * 60 + t2.second + t2.microsecond / 1000000

    return abs(t1_seconds - t2_seconds)

def parse_timestamp(text: str, patterns=None, reference_date=None, prioritize_time=True):
    """Parse timestamp from text using multiple patterns.

    Args:
        text: Text containing timestamp
        patterns: List of (regex, format) tuples to try (default: TIMESTAMP_PATTERNS)
        reference_date: Date to use for time-only formats (default: today's date)
        prioritize_time: If True, use reference_date for all formats (default: True)

    Returns:
        datetime object or None if no timestamp found
    """
    if patterns is None:
        patterns = TIMESTAMP_PATTERNS

    if reference_date is None:
        reference_date = datetime.now().date()

    for pattern, format_str in patterns:
        match = pattern.search(text)
        if match:
            try:
                dt = datetime.strptime(match.group(1), format_str)

                # If this is a time-only format (no date info), use the reference date
                if format_str in ["%H:%M:%S:%f", "%H:%M:%S.%f"]:
                    dt = datetime.combine(reference_date, dt.time())
                # For formats with date, optionally use the time but with the reference date
                # This ensures all timestamps are treated as being from the same day
                elif prioritize_time:
                    dt = datetime.combine(reference_date, dt.time())

                return dt
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


def find_frame_for_time(cap, target_time, frame_sampling=10, cache=None, ocr_config=None, callback=None, max_search_time=300, first_timestamp=None, first_frame=None):
    """Find the frame corresponding to the target timestamp with adaptive frame sampling and caching.

    This function uses an optimized search algorithm that leverages the video's FPS and a known
    timestamp (if provided) to estimate the frame position of the target timestamp. This can
    significantly reduce the search time by jumping directly to a frame close to the target.

    The optimization works as follows:
    1. If a first_timestamp and first_frame are provided, calculate the time difference between
       the first_timestamp and the target_time.
    2. Use the time difference and the video's FPS to estimate the frame difference.
    3. Jump directly to the estimated frame and start a more focused search from there.
    4. If no first_timestamp is provided, fall back to the traditional search method.

    Args:
        cap: Video capture object
        target_time: Target timestamp to find
        frame_sampling: Initial sample every Nth frame (default: 10)
        cache: Dictionary to cache OCR results (default: None)
        ocr_config: OCR configuration (default: None, uses default config)
        callback: Optional callback function for progress updates
        max_search_time: Maximum search time in seconds (default: 300)
        first_timestamp: First known timestamp in the video (default: None)
        first_frame: Frame number corresponding to first_timestamp (default: None)

    Returns:
        Frame number or None if not found

    Raises:
        RuntimeError: If Tesseract OCR is not installed or not in PATH or if search times out
    """
    if cache is None:
        cache = {}

    if ocr_config is None:
        ocr_config = OCRConfig()

    # Report initial status
    if callback:
        callback(0, "Initializing timestamp search...")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Get region coordinates based on configuration
    x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

    # Report region being searched
    if callback:
        region_info = f"Searching for timestamp in region: ({x_start},{y_start}) {region_width}x{region_height}"
        callback(0, region_info)

    # Initialize search variables
    frame_num = 0
    last_valid_ts = None
    last_valid_frame = None

    # If we have a first timestamp and frame, use them to estimate the target frame
    if first_timestamp is not None and first_frame is not None and fps > 0:
        # Calculate time difference in seconds (using time_diff_seconds to ignore date)
        time_diff = time_diff_seconds(target_time, first_timestamp)

        # Estimate frame difference based on FPS
        estimated_frame_diff = int(time_diff * fps)

        # Calculate estimated frame number
        estimated_frame = first_frame + estimated_frame_diff

        # Ensure estimated frame is within valid range
        estimated_frame = max(0, min(estimated_frame, total_frames - 1))

        if callback:
            callback(0, f"Using first timestamp at frame {first_frame} to estimate target frame")
            callback(0, f"Time difference: {time_diff:.2f} seconds, estimated frame: {estimated_frame}")

        # Start search from estimated frame
        frame_num = estimated_frame

        # Set a smaller initial sampling interval for more precise search
        adaptive_sampling = max(1, min(frame_sampling, 5))
    else:
        # No first timestamp provided, start from beginning with default sampling
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_num = 0

        # Start with a larger sampling interval for efficiency
        adaptive_sampling = min(frame_sampling * 3, 30)  # Start with larger interval but cap at 30

    consecutive_failures = 0
    max_consecutive_failures = 5  # Reduce sampling rate after this many failures

    # Report start of search
    if callback:
        callback(0, f"Starting search with sampling interval: {adaptive_sampling}")

    # Variables for progress reporting
    frames_checked = 0
    last_progress_report = 0
    progress_report_interval = max(1, total_frames // 100)  # Report progress every 1% of frames

    # For timeout tracking
    start_time = datetime.now()
    timeout_warning_shown = False

    while frame_num < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            if callback:
                callback(0, f"Error reading frame {frame_num}")
            break

        # Update progress reporting
        frames_checked += 1
        if callback and (frames_checked - last_progress_report) >= progress_report_interval:
            progress_percent = min(5 + int(90 * frame_num / total_frames), 95)  # Keep between 5-95%
            callback(progress_percent, f"Checking frame {frame_num}/{total_frames} ({frame_num/total_frames:.1%})")
            last_progress_report = frames_checked

        # Check for timeout
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time > max_search_time:
            if callback:
                callback(0, f"Search timed out after {elapsed_time:.1f} seconds")
            raise RuntimeError(
                f"Search timed out after {elapsed_time:.1f} seconds. Please try:\n"
                "1. Checking if timestamps are clearly visible in the video\n"
                "2. Using the Preview feature to verify timestamp detection\n"
                "3. Adjusting the timestamp format to match what appears in the video\n"
                "4. Selecting a different region if timestamps appear elsewhere in the frame"
            )
        elif elapsed_time > max_search_time * 0.8 and not timeout_warning_shown:
            # Show warning at 80% of timeout
            if callback:
                callback(0, f"Search taking longer than expected ({elapsed_time:.1f} seconds). Will timeout in {max_search_time - elapsed_time:.1f} seconds")
            timeout_warning_shown = True

        # Adjust sampling rate based on success/failure and proximity to target
        if last_valid_ts is not None:
            # If we're getting closer to the target time, reduce sampling interval
            # Use time_diff_seconds to compare by time only, ignoring date
            time_diff = time_diff_seconds(target_time, last_valid_ts)
            if time_diff < 60:  # Within a minute of target
                new_sampling = max(1, min(adaptive_sampling, int(frame_sampling * 0.5)))
                if new_sampling != adaptive_sampling and callback:
                    callback(0, f"Getting closer to target time ({time_diff:.1f} seconds). Reducing sampling interval to {new_sampling}")
                adaptive_sampling = new_sampling
            elif time_diff < 300:  # Within 5 minutes of target
                new_sampling = max(1, min(adaptive_sampling, frame_sampling))
                if new_sampling != adaptive_sampling and callback:
                    callback(0, f"Getting closer to target time ({time_diff/60:.1f} minutes). Adjusting sampling interval to {new_sampling}")
                adaptive_sampling = new_sampling

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
            if callback:
                callback(0, f"Found timestamp {ts} at frame {frame_num}")

            # Compare timestamps by time only, ignoring date
            if is_time_gte(ts, target_time):
                # If we found a timestamp after our target, we need to search more precisely
                if last_valid_ts and is_time_lt(last_valid_ts, target_time):
                    # We have a range to search in
                    if callback:
                        callback(0, f"Found timestamp range containing target. Performing binary search between frames {last_valid_frame} and {frame_num}")
                    # Use 20% of the remaining time for binary search
                    remaining_time = max_search_time - (datetime.now() - start_time).total_seconds()
                    binary_search_timeout = max(30, min(60, remaining_time * 0.2))
                    return binary_search_frames(cap, last_valid_frame, frame_num, target_time, cache, ocr_config, callback, binary_search_timeout)
                if callback:
                    callback(0, f"Found timestamp matching or exceeding target at frame {frame_num}")
                return frame_num
            last_valid_ts = ts
            last_valid_frame = frame_num
        else:
            # No timestamp found, count as a failure
            consecutive_failures += 1
            if callback and consecutive_failures == 1:  # Only report on first failure to avoid spam
                callback(0, f"No timestamp found at frame {frame_num}")

            if consecutive_failures >= max_consecutive_failures:
                # Too many failures, reduce sampling interval to avoid missing timestamps
                new_sampling = max(1, int(adaptive_sampling * 0.5))
                if callback:
                    callback(0, f"Multiple failures detected. Reducing sampling interval to {new_sampling}")
                adaptive_sampling = new_sampling
                consecutive_failures = 0  # Reset counter

        frame_num += adaptive_sampling

    # If we didn't find an exact match but have a valid timestamp before target
    if last_valid_frame is not None:
        if callback:
            callback(0, f"Search complete. Using closest timestamp before target at frame {last_valid_frame}")
        return last_valid_frame

    if callback:
        callback(0, "Search complete. No suitable timestamp found.")
    return None

def binary_search_frames(cap, start_frame, end_frame, target_time, cache, ocr_config=None, callback=None, max_search_time=60):
    """Binary search between two frames to find the closest match to target time.

    Args:
        cap: Video capture object
        start_frame: Starting frame number
        end_frame: Ending frame number
        target_time: Target timestamp to find
        cache: Dictionary to cache OCR results
        ocr_config: OCR configuration (default: None, uses default config)
        callback: Optional callback function for progress updates
        max_search_time: Maximum search time in seconds (default: 60)

    Returns:
        Frame number closest to target time

    Raises:
        RuntimeError: If Tesseract OCR is not installed or not in PATH or if search times out
    """
    if ocr_config is None:
        ocr_config = OCRConfig()

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Get region coordinates based on configuration
    x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

    if callback:
        callback(0, f"Starting binary search between frames {start_frame} and {end_frame}")

    # For progress reporting
    total_iterations = int(math.log2(end_frame - start_frame + 1)) + 1
    current_iteration = 0

    # For timeout tracking
    start_time = datetime.now()
    timeout_warning_shown = False

    while start_frame <= end_frame:
        mid_frame = (start_frame + end_frame) // 2

        # Update progress
        current_iteration += 1
        if callback:
            progress_percent = min(5 + int(90 * current_iteration / total_iterations), 95)
            callback(progress_percent, f"Binary search iteration {current_iteration}/{total_iterations}: checking frame {mid_frame}")

        # Check for timeout
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time > max_search_time:
            if callback:
                callback(0, f"Binary search timed out after {elapsed_time:.1f} seconds")
            raise RuntimeError(
                f"Binary search timed out after {elapsed_time:.1f} seconds. Please try:\n"
                "1. Checking if timestamps are clearly visible in the video\n"
                "2. Using the Preview feature to verify timestamp detection\n"
                "3. Adjusting the timestamp format to match what appears in the video"
            )
        elif elapsed_time > max_search_time * 0.8 and not timeout_warning_shown:
            # Show warning at 80% of timeout
            if callback:
                callback(0, f"Binary search taking longer than expected ({elapsed_time:.1f} seconds). Will timeout in {max_search_time - elapsed_time:.1f} seconds")
            timeout_warning_shown = True

        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        if not ret:
            if callback:
                callback(0, f"Error reading frame {mid_frame}")
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
            if callback:
                callback(0, f"No timestamp found at frame {mid_frame}")
            start_frame = mid_frame + 1
            continue

        if callback:
            callback(0, f"Found timestamp {ts} at frame {mid_frame}")

        # Compare timestamps by time only, ignoring date
        comparison = compare_timestamps_by_time(ts, target_time)
        if comparison < 0:  # ts's time is earlier than target_time's time
            if callback:
                callback(0, f"Timestamp {ts} is before target {target_time}, searching in upper half")
            start_frame = mid_frame + 1
        elif comparison > 0:  # ts's time is later than target_time's time
            if callback:
                callback(0, f"Timestamp {ts} is after target {target_time}, searching in lower half")
            end_frame = mid_frame - 1
        else:
            # Exact match (times are equal)
            if callback:
                callback(0, f"Found exact match for target timestamp at frame {mid_frame}")
            return mid_frame

    # Return the closest frame
    if callback:
        callback(0, f"Binary search complete. Using closest frame: {start_frame}")
    return start_frame


def extract_snippet(video_path, start_time, end_time, output_path, callback=None, ocr_config=None):
    """Extract a video snippet between start_time and end_time.

    This function uses an optimized search algorithm to find the frames corresponding to the
    start and end timestamps. The optimization works as follows:

    1. First, it reads a frame from an early position in the video (10% of the way through)
       to get an initial timestamp reading.
    2. It uses this initial timestamp and the video's FPS to estimate where the start timestamp
       might be located, allowing it to start searching from a position close to the target.
    3. After finding the start frame, it reads the actual timestamp at that position.
    4. For the end timestamp search, it uses the start frame timestamp as a reference point
       and the video's FPS to estimate where the end timestamp might be located.
    5. This allows the function to jump directly to frames close to the target timestamps,
       significantly reducing the search time.
    6. If the optimized search fails, it falls back to the traditional search method.

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
        callback(0, "Reading initial frame to optimize search...")

    # Get an initial timestamp reading from an early frame in the video
    initial_frame_position = int(total_frames * 0.1)  # 10% of the way through the video
    initial_timestamp = None
    initial_frame_num = None

    # Try to get an initial timestamp reading
    try:
        # Set position and read frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, initial_frame_position)
        ret, frame = cap.read()
        if ret:
            # Get region coordinates based on configuration
            x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

            # Extract region for OCR
            region = frame[y_start:y_start+region_height, x_start:x_start+region_width]

            # Perform OCR
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, config='--psm 7')
            initial_timestamp = parse_timestamp(text, ocr_config.patterns)

            if initial_timestamp:
                initial_frame_num = initial_frame_position
                ocr_cache[initial_frame_num] = initial_timestamp
                if callback:
                    callback(0, f"Found initial timestamp {initial_timestamp} at frame {initial_frame_num}")
            else:
                if callback:
                    callback(0, "No timestamp found in initial frame, falling back to traditional search")
        else:
            if callback:
                callback(0, "Failed to read initial frame, falling back to traditional search")
    except Exception as e:
        if callback:
            callback(0, f"Error reading initial frame: {str(e)}, falling back to traditional search")

    # Update callback
    if callback:
        callback(0, "Searching for start time...")

    # Find start frame with sampling and caching, using initial timestamp as reference if available
    try:
        start_frame = find_frame_for_time(
            cap, 
            start_time, 
            frame_sampling=15, 
            cache=ocr_cache, 
            ocr_config=ocr_config, 
            callback=callback,
            first_timestamp=initial_timestamp,
            first_frame=initial_frame_num
        )
        if start_frame is None:
            raise RuntimeError(
                "Start time not found in video. Please check that:\n"
                "1. The timestamp format matches what appears in the video\n"
                "2. The timestamp is visible in the selected region\n"
                "3. The video contains frames with the specified timestamp\n"
                "4. The OCR is able to recognize the text (try the Preview feature)"
            )
    except RuntimeError as e:
        # Re-raise the error with the original message
        if "timed out" in str(e).lower():
            if callback:
                callback(0, "Search for start time timed out")
            raise RuntimeError(str(e))
        raise

    # Update callback
    if callback:
        callback(10, "Start time found. Searching for end time...")

    # Get the timestamp at the start frame to use as reference
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Error reading start frame")

    # Get region coordinates based on configuration
    x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

    # Get the timestamp at the start frame
    start_frame_ts = None
    if start_frame in ocr_cache:
        start_frame_ts = ocr_cache[start_frame]
    else:
        overlay = frame[y_start:y_start+region_height, x_start:x_start+region_width]
        gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
        try:
            text = pytesseract.image_to_string(gray, config='--psm 7')
            start_frame_ts = parse_timestamp(text, ocr_config.patterns)
            ocr_cache[start_frame] = start_frame_ts
        except Exception as e:
            # If there's an error, just continue without a reference timestamp
            if callback:
                callback(0, "Error reading timestamp at start frame, continuing without optimization")

    # Find end frame with sampling and caching, using start frame as reference if possible
    if start_frame_ts is not None and callback:
        callback(0, f"Using start frame timestamp ({start_frame_ts}) as reference for end time search")

    try:
        # Use the optimized search with the start frame timestamp as reference
        end_frame = find_frame_for_time(
            cap, 
            end_time, 
            frame_sampling=15, 
            cache=ocr_cache, 
            ocr_config=ocr_config, 
            callback=callback,
            first_timestamp=start_frame_ts,
            first_frame=start_frame
        )

        if end_frame is None:
            # If optimized search fails, fall back to traditional search
            if callback:
                callback(0, "Optimized search failed to find end time, falling back to traditional search")

            # Traditional search method
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            end_frame = None
            frame_sampling = 15
            current_frame = start_frame

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

                # Compare timestamps by time only, ignoring date
                if ts and is_time_gte(ts, end_time):
                    end_frame = current_frame
                    break

                current_frame += frame_sampling
    except RuntimeError as e:
        # Re-raise the error with the original message
        if "timed out" in str(e).lower():
            if callback:
                callback(0, "Search for end time timed out")
            raise RuntimeError(str(e))
        raise

    # If we didn't find the end time with sampling, use the last frame
    if end_frame is None:
        if callback:
            callback(50, "End time not found. Using all remaining frames...")
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

    # Process all frames between start and end (or until end of video if end_frame is None)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frames_processed = 0
    total_frames_estimate = end_frame - start_frame if end_frame is not None else total_frames - start_frame

    # Process in chunks to limit memory usage
    while True:
        # Determine chunk size
        chunk_size = max_frames_in_memory
        chunk_frames = []

        # Read chunk of frames
        for i in range(chunk_size):
            if callback and (frames_processed + i) % 30 == 0:
                progress = 50 + int(40 * min(frames_processed + i, total_frames_estimate) / total_frames_estimate)
                callback(progress, f"Extracting frames... ({frames_processed + i})")

            ret, frame = cap.read()
            if not ret:
                break

            # If we have an end frame and we've reached it, stop
            if end_frame is not None and start_frame + frames_processed + i >= end_frame:
                break

            chunk_frames.append(frame)

        # If no frames were read, we're done
        if not chunk_frames:
            break

        # Write chunk to output
        for i, fr in enumerate(chunk_frames):
            if callback and i % 30 == 0:
                progress = 90 + int(10 * min(frames_processed + i, total_frames_estimate) / total_frames_estimate)
                callback(progress, f"Writing output... ({frames_processed + i})")
            out.write(fr)

        frames_processed += len(chunk_frames)
        chunk_frames = []  # Clear memory

        # If we have an end frame and we've processed all frames up to it, we're done
        if end_frame is not None and start_frame + frames_processed >= end_frame:
            break

    # If no frames were processed, raise an error
    if frames_processed == 0:
        raise RuntimeError(
            "No frames extracted. Please check that:\n"
            "1. The start time is before the end time\n"
            "2. Both timestamps exist in the video\n"
            "3. The time range between start and end contains frames\n"
            "4. The OCR is correctly recognizing the timestamps (try the Preview feature)"
        )

    cap.release()

    out.release()

    if callback:
        callback(100, "Done!")


class MainWindow(QMainWindow):
    # Define signals
    stop_pulse_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Initialize variables
        self.video_path = None
        self.processing = False
        self.ocr_config = OCRConfig()
        self.preview_dialog = None
        self.progress_timer = None

        # Connect signals to slots
        self.stop_pulse_signal.connect(self._stop_progress_pulse_slot)
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

        # Initialize status text area with instructions
        self.ui.statusTextEdit.clear()
        self.log_status("Welcome to VidExtract")
        self.log_status("1. Select a video file using the 'Select MKV' button")
        self.log_status("2. Enter start and end timestamps that appear in the video")
        self.log_status("3. Click 'Preview' to verify timestamp detection")
        self.log_status("4. Click 'Extract' to extract the video snippet")
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
            self.ui.filePathLabel.setText(os.path.basename(path))

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
        self.ui.progressBar.setValue(progress)
        self.ui.statusLabel.setText(status_text)

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
        # Get current time
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Format the message with timestamp
        formatted_message = f"[{current_time}] {message}"

        # Append to the text edit
        self.ui.statusTextEdit.append(formatted_message)

        # Scroll to the bottom to show the latest message
        self.ui.statusTextEdit.verticalScrollBar().setValue(
            self.ui.statusTextEdit.verticalScrollBar().maximum()
        )

        # Force update of the UI
        QApplication.processEvents()

    def clear_status_log(self):
        """Clear the status text edit and add a separator for a new operation."""
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
        """Clear the status text edit and add a separator for a new operation in the main thread."""
        self.ui.statusTextEdit.clear()
        self._log_status_main_thread("Starting new operation...")
        self._log_status_main_thread("-" * 50)

    def start_progress_pulse(self):
        """Start a pulsing animation on the progress bar to indicate activity."""
        if self.progress_timer is None:
            self.progress_timer = QtCore.QTimer(self)
            self.progress_timer.timeout.connect(self._update_pulse)
            self.progress_pulse_value = 0
            self.progress_pulse_direction = 1
            self.progress_timer.start(50)  # Update every 50ms

    def _update_pulse(self):
        """Update the progress bar pulse animation."""
        if self.progress_pulse_direction > 0:
            self.progress_pulse_value += 2
            if self.progress_pulse_value >= 100:
                self.progress_pulse_value = 100
                self.progress_pulse_direction = -1
        else:
            self.progress_pulse_value -= 2
            if self.progress_pulse_value <= 0:
                self.progress_pulse_value = 0
                self.progress_pulse_direction = 1

        self.ui.progressBar.setValue(self.progress_pulse_value)
        QApplication.processEvents()  # Force update of the UI

    def stop_progress_pulse(self):
        """Stop the pulsing animation on the progress bar.

        This method emits a signal to stop the timer in the main thread.
        """
        # Emit signal to stop the timer in the main thread
        self.stop_pulse_signal.emit()

    @QtCore.pyqtSlot()
    def _stop_progress_pulse_slot(self):
        """Slot method to stop the progress pulse timer in the main thread."""
        if self.progress_timer is not None:
            self.progress_timer.stop()
            self.progress_timer = None

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

        # Use a fixed output path for testing
        default_name = f"snippet_{start_ts.strftime('%Y%m%d_%H%M%S')}.mp4"
        default_dir = os.path.dirname(self.video_path)
        output_path = os.path.join(default_dir, "ui_test_snippet.mp4")

        # Log the output path
        self.log_status(f"Using output path: {output_path}")

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Disable UI elements during processing
        self.processing = True
        self.ui.extractButton.setEnabled(False)
        self.ui.previewButton.setEnabled(False)
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Starting extraction...")

        # Clear status log for new operation
        self.clear_status_log()

        # Set wait cursor to indicate processing
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))

        # Start progress bar pulsing animation
        self.start_progress_pulse()

        # Run extraction in a separate thread to keep UI responsive
        def extraction_thread():
            try:
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
        # Restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Done", f"Snippet saved to {output_path}")

    @QtCore.pyqtSlot(str)
    def show_error_message(self, error_message):
        """Show error message dialog."""
        # Restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Error", error_message)

    def on_preview(self):
        """Handle preview button click event."""
        if not self.video_path:
            QMessageBox.critical(self, "Error", "No video selected")
            return

        if self.processing:
            QMessageBox.information(self, "Info", "Processing is already in progress")
            return

        # Disable UI elements during processing
        self.processing = True
        self.ui.extractButton.setEnabled(False)
        self.ui.previewButton.setEnabled(False)
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Starting preview generation...")

        # Clear status log for new operation
        self.clear_status_log()

        # Set wait cursor to indicate processing
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))

        # Start progress bar pulsing animation
        self.start_progress_pulse()

        # Run preview generation in a separate thread to keep UI responsive
        def preview_thread():
            try:
                # Get frame from 10% of the video
                frame, timestamp, text = preview_timestamp_detection(
                    self.video_path, 
                    None, 
                    self.ocr_config,
                    self.update_progress  # Pass the update_progress method as callback
                )

                # Update UI on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "show_preview_result",
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(object, frame),
                    QtCore.Q_ARG(object, timestamp),
                    QtCore.Q_ARG(str, text)
                )

            except Exception as e:
                # Show error message on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "show_preview_error",
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, str(e))
                )

            finally:
                # Reset processing flag on the main thread
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "reset_ui",
                    QtCore.Qt.ConnectionType.QueuedConnection
                )

        # Start preview thread
        thread = threading.Thread(target=preview_thread)
        thread.daemon = True
        thread.start()

    @QtCore.pyqtSlot(object, object, str)
    def show_preview_result(self, frame, timestamp, text):
        """Show preview results in a dialog."""
        # Restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()

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

        # Show preview dialog
        preview_dialog.exec()

    @QtCore.pyqtSlot(str)
    def show_preview_error(self, error_message):
        """Show error message for preview generation."""
        # Restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()

        QMessageBox.critical(self, "Error", f"Error generating preview: {error_message}")

    @QtCore.pyqtSlot()
    def reset_ui(self):
        """Reset UI elements after processing."""
        self.processing = False
        self.ui.extractButton.setEnabled(True)
        self.ui.previewButton.setEnabled(True)
        self.ui.statusLabel.setText("Ready")

        # Stop progress bar pulsing animation
        self.stop_progress_pulse()

        # Reset progress bar to 0
        self.ui.progressBar.setValue(0)

        # Restore cursor if it hasn't been restored yet
        if QtWidgets.QApplication.overrideCursor() is not None:
            QtWidgets.QApplication.restoreOverrideCursor()


def preview_timestamp_detection(video_path, frame_position=None, ocr_config=None, callback=None):
    """Capture a frame from the video and detect timestamp for preview.

    Args:
        video_path: Path to the video file
        frame_position: Position of the frame to capture (default: None, uses 10% of video)
        ocr_config: OCR configuration (default: None, uses default config)
        callback: Optional callback function for progress updates

    Returns:
        Tuple of (frame, detected_timestamp, timestamp_text) or (None, None, error_message) on error
    """
    if ocr_config is None:
        ocr_config = OCRConfig()

    try:
        # Update progress
        if callback:
            callback(10, "Opening video file...")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None, "Unable to open video file"

        # Update progress
        if callback:
            callback(20, "Analyzing video...")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # If no frame position specified, use 10% of the video
        if frame_position is None or frame_position <= 0:
            frame_position = int(total_frames * 0.1)

        # Ensure frame position is valid
        frame_position = min(frame_position, total_frames - 1)

        # Update progress
        if callback:
            callback(40, "Seeking to frame position...")

        # Set position and read frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()
        if not ret:
            return None, None, "Failed to read frame from video"

        # Update progress
        if callback:
            callback(60, "Preparing for OCR...")

        # Get frame dimensions
        height, width = frame.shape[:2]

        # Get region coordinates
        x_start, y_start, region_width, region_height = ocr_config.get_region_coords(width, height)

        # Extract region for OCR
        region = frame[y_start:y_start+region_height, x_start:x_start+region_width]

        # Draw rectangle around the region on the original frame
        cv2.rectangle(frame, (x_start, y_start), (x_start+region_width, y_start+region_height), (0, 255, 0), 2)

        # Update progress
        if callback:
            callback(80, "Performing OCR...")

        # Perform OCR
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 7')
        timestamp = parse_timestamp(text, ocr_config.patterns)

        cap.release()

        # Update progress
        if callback:
            callback(100, "Preview generation complete")

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
