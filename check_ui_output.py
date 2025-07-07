import os
import sys

def main():
    # Define the output path
    video_path = r"C:\Users\Marle.Franco\Olympus\Katana Machine Learning - Data Repository-TRL 5 - Animal Lab 13 JUN 2025 - Documents\Data\Session 2\Computer Data Logger Video\2025-06-13 13-02-54.mkv"
    output_path = os.path.join(os.path.dirname(video_path), "ui_test_snippet.avi")

    # Check if the output file exists
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"Output file exists at {output_path} with size {file_size} bytes")
        if file_size > 0:
            print("Extraction was successful!")
        else:
            print("Output file exists but is empty, extraction may have failed")
    else:
        print(f"Output file does not exist at {output_path}, extraction failed")

if __name__ == "__main__":
    main()
