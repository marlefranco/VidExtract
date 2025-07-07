"""
Setup script for VidExtract.

This script can be used to create standalone executables using PyInstaller or cx_Freeze.
"""

import sys
from setuptools import setup, find_packages

# Package metadata
NAME = "VidExtract"
VERSION = "1.0.0"
DESCRIPTION = "Extract video snippets based on timestamp overlays"
AUTHOR = "VidExtract Team"
AUTHOR_EMAIL = ""
URL = ""
LICENSE = "MIT"

# Dependencies
INSTALL_REQUIRES = [
    "opencv-python",
    "pytesseract",
    "Pillow",
    "PyQt6",
]

# Entry points
ENTRY_POINTS = {
    "console_scripts": [
        "vidextract=main:main",
    ],
}

# Setup configuration
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENSE,
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
    entry_points=ENTRY_POINTS,
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
    ],
)

# PyInstaller configuration
if "pyinstaller" in sys.argv:
    import PyInstaller.__main__
    
    PyInstaller.__main__.run([
        "--name=VidExtract",
        "--onefile",
        "--windowed",
        "--add-data=mainwindow.ui;.",
        "main.py",
    ])

# cx_Freeze configuration
if "build_exe" in sys.argv:
    from cx_Freeze import setup, Executable
    
    build_exe_options = {
        "packages": ["os", "sys", "cv2", "pytesseract", "PyQt6"],
        "include_files": ["mainwindow.ui"],
    }
    
    executables = [
        Executable(
            "main.py",
            base="Win32GUI" if sys.platform == "win32" else None,
            target_name="VidExtract",
        )
    ]
    
    setup(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        options={"build_exe": build_exe_options},
        executables=executables,
    )