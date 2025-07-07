"""
Test script for batch_extract.py.

This script tests the key components of the batch extraction functionality.
"""

import unittest
from datetime import datetime
from batch_extract import convert_rangetime_timestamp, RANGETIME_PATTERN

class TestBatchExtract(unittest.TestCase):
    """Test cases for batch extraction components."""

    def test_rangetime_pattern(self):
        """Test that the rangetime pattern correctly matches timestamps."""
        # Test valid timestamp
        match = RANGETIME_PATTERN[0].search("20250613_132726.332")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "20250613_132726.332")
        
        # Test invalid timestamp
        match = RANGETIME_PATTERN[0].search("invalid_timestamp")
        self.assertIsNone(match)
    
    def test_convert_rangetime_timestamp(self):
        """Test the convert_rangetime_timestamp function."""
        # Test valid timestamp
        ts = convert_rangetime_timestamp("20250613_132726.332")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.year, 2025)
        self.assertEqual(ts.month, 6)
        self.assertEqual(ts.day, 13)
        self.assertEqual(ts.hour, 13)
        self.assertEqual(ts.minute, 27)
        self.assertEqual(ts.second, 26)
        self.assertEqual(ts.microsecond, 332000)
        
        # Test invalid timestamp
        ts = convert_rangetime_timestamp("invalid_timestamp")
        self.assertIsNone(ts)
    
    def test_timestamp_conversion(self):
        """Test that timestamps are correctly converted for use with extract_snippet."""
        # Convert a rangetime timestamp
        ts = convert_rangetime_timestamp("20250613_132726.332")
        
        # Verify it's a valid datetime object that can be used with extract_snippet
        self.assertIsInstance(ts, datetime)
        
        # Verify the string representation is in a format that extract_snippet can use
        ts_str = ts.strftime("%d/%m/%Y %H:%M:%S:%f")[:-3]  # Format as DD/MM/YYYY HH:mm:ss:SSS
        self.assertEqual(ts_str, "13/06/2025 13:27:26:332")

if __name__ == "__main__":
    unittest.main()