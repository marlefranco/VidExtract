"""
Test script for VidExtract.

This script tests the key components of VidExtract to ensure they work as expected.
"""

import os
import sys
import unittest
from datetime import datetime

# Import components from main.py
try:
    from main import (
        parse_timestamp,
        OCRConfig,
        find_tesseract_executable,
        preview_timestamp_detection,
    )
except ImportError:
    print("Error: Could not import components from main.py")
    sys.exit(1)


class TestVidExtract(unittest.TestCase):
    """Test cases for VidExtract components."""

    def test_parse_timestamp(self):
        """Test the parse_timestamp function with various formats."""
        # Test default format (DD/MM/YYYY HH:mm:ss:SSS)
        ts = parse_timestamp("01/02/2023 12:34:56:789")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.day, 1)
        self.assertEqual(ts.month, 2)
        self.assertEqual(ts.year, 2023)
        self.assertEqual(ts.hour, 12)
        self.assertEqual(ts.minute, 34)
        self.assertEqual(ts.second, 56)
        self.assertEqual(ts.microsecond, 789000)

        # Test alternative format (YYYY-MM-DD HH:mm:ss.SSS)
        ts = parse_timestamp("2023-02-01 12:34:56.789")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.day, 1)
        self.assertEqual(ts.month, 2)
        self.assertEqual(ts.year, 2023)
        self.assertEqual(ts.hour, 12)
        self.assertEqual(ts.minute, 34)
        self.assertEqual(ts.second, 56)
        self.assertEqual(ts.microsecond, 789000)

        # Test time-only format (HH:mm:ss:SSS)
        ts = parse_timestamp("12:34:56:789")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.hour, 12)
        self.assertEqual(ts.minute, 34)
        self.assertEqual(ts.second, 56)
        self.assertEqual(ts.microsecond, 789000)

        # Test invalid format
        ts = parse_timestamp("invalid timestamp")
        self.assertIsNone(ts)

    def test_ocr_config(self):
        """Test the OCRConfig class."""
        config = OCRConfig()
        
        # Test default values
        self.assertEqual(config.region, OCRConfig.REGION_TOP_RIGHT)
        self.assertEqual(config.region_width, 300)
        self.assertEqual(config.region_height, 50)
        
        # Test region coordinates calculation
        x, y, w, h = config.get_region_coords(1920, 1080)
        self.assertEqual(x, 1920 - 300)
        self.assertEqual(y, 0)
        self.assertEqual(w, 300)
        self.assertEqual(h, 50)
        
        # Test different regions
        config.region = OCRConfig.REGION_TOP_LEFT
        x, y, w, h = config.get_region_coords(1920, 1080)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        
        config.region = OCRConfig.REGION_BOTTOM_RIGHT
        x, y, w, h = config.get_region_coords(1920, 1080)
        self.assertEqual(x, 1920 - 300)
        self.assertEqual(y, 1080 - 50)
        
        config.region = OCRConfig.REGION_BOTTOM_LEFT
        x, y, w, h = config.get_region_coords(1920, 1080)
        self.assertEqual(x, 0)
        self.assertEqual(y, 1080 - 50)
        
        config.region = OCRConfig.REGION_CUSTOM
        config.custom_x = 100
        config.custom_y = 200
        config.custom_width = 400
        config.custom_height = 60
        x, y, w, h = config.get_region_coords(1920, 1080)
        self.assertEqual(x, 100)
        self.assertEqual(y, 200)
        self.assertEqual(w, 400)
        self.assertEqual(h, 60)

    def test_tesseract_detection(self):
        """Test the Tesseract detection function."""
        success, message = find_tesseract_executable()
        print(f"Tesseract detection: {success}, {message}")
        # We don't assert anything here because it depends on the system configuration

    def test_timestamp_patterns(self):
        """Test that all timestamp patterns are valid."""
        from main import TIMESTAMP_PATTERNS
        
        for pattern, format_str in TIMESTAMP_PATTERNS:
            # Create a sample timestamp string for this format
            if format_str == "%d/%m/%Y %H:%M:%S:%f":
                sample = "01/02/2023 12:34:56:789"
            elif format_str == "%m/%d/%Y %H:%M:%S:%f":
                sample = "02/01/2023 12:34:56:789"
            elif format_str == "%Y-%m-%d %H:%M:%S.%f":
                sample = "2023-02-01 12:34:56.789"
            elif format_str == "%H:%M:%S:%f":
                sample = "12:34:56:789"
            elif format_str == "%H:%M:%S.%f":
                sample = "12:34:56.789"
            else:
                self.fail(f"Unexpected format string: {format_str}")
            
            # Test that the pattern matches the sample
            match = pattern.search(sample)
            self.assertIsNotNone(match, f"Pattern {pattern} did not match sample {sample}")
            
            # Test that datetime.strptime can parse it
            try:
                dt = datetime.strptime(match.group(1), format_str)
                self.assertIsInstance(dt, datetime)
            except ValueError as e:
                self.fail(f"Failed to parse {match.group(1)} with format {format_str}: {e}")


if __name__ == "__main__":
    unittest.main()