import sys
import os
from datetime import datetime
from main import parse_timestamp, extract_snippet, OCRConfig

def main():
    # Video path from the issue description
    video_path = r"C:\Users\Marle.Franco\Olympus\Katana Machine Learning - Data Repository-TRL 5 - Animal Lab 13 JUN 2025 - Documents\Data\Session 2\Computer Data Logger Video\2025-06-13 13-02-54.mkv"

    # Check if the video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return

    # Parse start and end timestamps from the issue description
    start_time_str = "13/06/2025 13:28:27:657"
    end_time_str = "13/06/2025 13:28:37:872"

    # Parse timestamps using the DD/MM/YYYY format
    start_time = parse_timestamp(start_time_str, reference_date=None, prioritize_time=False)
    end_time = parse_timestamp(end_time_str, reference_date=None, prioritize_time=False)

    if start_time is None or end_time is None:
        print("Error: Failed to parse timestamps")
        if start_time is None:
            print(f"  Start time '{start_time_str}' could not be parsed")
        if end_time is None:
            print(f"  End time '{end_time_str}' could not be parsed")
        return

    print(f"Parsed start time: {start_time}")
    print(f"Parsed end time: {end_time}")

    # Output path for the snippet
    output_path = "snippet_test.avi"

    # Define a callback function to print progress
    def progress_callback(progress, status_text):
        print(f"Progress: {progress}%, Status: {status_text}")

    # Create OCR config
    ocr_config = OCRConfig()

    print(f"Extracting snippet from {video_path}")
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")
    print(f"Output path: {output_path}")

    try:
        # Extract the snippet
        extract_snippet(video_path, start_time, end_time, output_path, callback=progress_callback, ocr_config=ocr_config)
        print(f"Snippet successfully extracted to {output_path}")
    except Exception as e:
        print(f"Error extracting snippet: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
