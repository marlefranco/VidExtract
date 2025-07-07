# VidExtract Batch Extract

This document describes the batch extraction functionality of VidExtract, which allows you to extract multiple video segments from a single video file based on timestamp ranges stored in text files.

## Overview

The batch extraction functionality is designed to process multiple timestamp ranges from a single video file. It works by:

1. Selecting a parent directory containing subfolders
2. Looking for `rangetime.txt` files in each subfolder
3. Extracting video segments based on the timestamp ranges in these files
4. Saving the extracted segments as `video.avi` in each subfolder

## Usage

1. Launch the batch extraction application by running `batch_extract.py`
2. Click "Select Video" to choose the source video file (MKV, MP4, AVI, etc.)
3. Click "Select Parent Directory" to choose a directory containing subfolders with `rangetime.txt` files
4. Click "Extract" to start the batch extraction process
5. Monitor the progress in the status area
6. When complete, each subfolder will contain a `video.avi` file with the extracted segment

## rangetime.txt Format

Each `rangetime.txt` file should be a CSV file with the following format:

```
first_timestamp,last_timestamp
20250613_132726.332,20250613_132730.850
```

Where:
- The first line is a header (required)
- Each subsequent line contains two timestamps in the format `YYYYMMDD_hhmmss.SSS`
- The first timestamp is the start time for the video segment
- The second timestamp is the end time for the video segment

## Example

An example `rangetime.txt` file is provided in the `Example` folder. You can use this as a template for creating your own timestamp files.

## Technical Details

The batch extraction process:

1. Scans the parent directory for all `rangetime.txt` files
2. Parses each file to extract timestamp ranges
3. Converts timestamps from `YYYYMMDD_hhmmss.SSS` format to datetime objects
4. Uses the `extract_snippet` function from the main application to extract each video segment
5. Saves each segment as `video.avi` in the same folder as the corresponding `rangetime.txt` file

## Requirements

The batch extraction functionality has the same requirements as the main VidExtract application:

- Python 3.6 or higher
- PyQt6
- OpenCV (cv2)
- Tesseract OCR

See the main README.md file for detailed installation instructions.