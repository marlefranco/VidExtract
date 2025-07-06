# VidExtract

VidExtract is a simple GUI application that extracts a video snippet from an MKV file based on timestamp overlays that appear on the top-right corner of the frames. The timestamps must be in the format `DD/MM/YYYY HH:mm:ss:SSS`.

## Requirements

- Python 3.11
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and available in your system `PATH`
- The Python packages listed in `requirements.txt`

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

Run the application with:

```bash
python main.py
```

1. Click **Select MKV** and choose your video file.
2. Enter the desired **start** and **end** timestamps that appear in the video overlay.
3. Press **Extract**. A snippet named `snippet.mp4` will be saved in the same folder as the source video.

## Limitations and possible improvements

- The OCR step can be slow because every frame between the start and end time is scanned. A more efficient approach would be to sample frames or cache OCR results.
- Error handling could be expanded to better inform the user of OCR failures or missing timestamps.
- Adding a progress bar would help visualize the processing state while searching through the video.
- The current dark theme is very basic. Using a dedicated UI toolkit such as PySide or PyQt could provide a more modern look.
