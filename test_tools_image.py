#!/usr/bin/env python3
"""Unit tests for image tools. Mocks Pixelmator to run on Linux CI."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
import re

import tools_image


class MockPxmError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class TestImageTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.home = os.path.expanduser("~")

        # Create a test image file
        self.test_image = os.path.join(self.temp_dir, "test.jpg")
        with open(self.test_image, "wb") as f:
            f.write(b"fake jpg data")

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_remove_background_path_outside_home(self):
        result = tools_image.remove_background("/etc/passwd")
        self.assertIn("No image at", result)

    def test_remove_background_missing_file(self):
        result = tools_image.remove_background("~/nonexistent.jpg")
        self.assertIn("No image at", result)

    def test_remove_background_non_image(self):
        temp_txt = os.path.join(self.temp_dir, "test.txt")
        with open(temp_txt, "w") as f:
            f.write("not an image")
        result = tools_image.remove_background(temp_txt)
        self.assertIn("No image at", result)

    @patch('tools_image.pxm.build_lock')
    @patch('tools_image.pxm.run_applescript')
    @patch('tools_image.pxm.hide_app')
    def test_remove_background_script_generation(self, mock_hide, mock_run, mock_lock):
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        mock_run.return_value = ""

        # Create a temporary file in home
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-remove-bg.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('os.path.exists', return_value=True):
                result = tools_image.remove_background(test_file)
                self.assertIn("Background removed", result)

                # Verify the script was called
                self.assertTrue(mock_run.called)
                script = mock_run.call_args[0][0]
                self.assertIn("remove background", script)
                self.assertIn("export", script)
                self.assertIn("saving no", script)
                self.assertIn(test_file, script)
                # Output path should NOT be input path
                self.assertNotIn("samantha-nobg.png", test_file)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('tools_image.pxm.build_lock')
    @patch('tools_image.pxm.run_applescript')
    @patch('tools_image.pxm.hide_app')
    def test_upscale_image_script(self, mock_hide, mock_run, mock_lock):
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        mock_run.return_value = ""

        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-upscale.png")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake png")

        try:
            with patch('os.path.exists', return_value=True):
                result = tools_image.upscale_image(test_file)
                self.assertIn("Upscaled", result)

                script = mock_run.call_args[0][0]
                self.assertIn("super resolution", script)
                self.assertIn("export", script)
                self.assertIn("saving no", script)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_rotate_image_parsing(self):
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-rotate.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            # Test parsing "path by 180"
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript'):
                    with patch('tools_image.pxm.hide_app'):
                        with patch('os.path.exists', return_value=True):
                            result = tools_image.rotate_image(f"{test_file} by 180")
                            self.assertIn("Rotated 180", result)

            # Test invalid rotation
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript'):
                    with patch('tools_image.pxm.hide_app'):
                        result = tools_image.rotate_image(f"{test_file} by 45")
                        self.assertIn("must be 90, 180, or 270", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_resize_image_parsing(self):
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-resize.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            # Test format validation
            result = tools_image.resize_image(f"{test_file} to abc")
            self.assertIn("Format should be", result)

            # Test out-of-range size
            result = tools_image.resize_image(f"{test_file} to 5")
            self.assertIn("between 16 and 8000", result)

            result = tools_image.resize_image(f"{test_file} to 9000")
            self.assertIn("between 16 and 8000", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_convert_image_parsing(self):
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-convert.png")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake png")

        try:
            # Test invalid format
            result = tools_image.convert_image(f"{test_file} to xyz")
            self.assertIn("Unsupported format", result)

            # Test valid format parsing
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript'):
                    with patch('tools_image.pxm.hide_app'):
                        with patch('os.path.exists', return_value=True):
                            result = tools_image.convert_image(f"{test_file} to jpg")
                            self.assertIn("Converted to JPG", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_flip_image_parsing(self):
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-flip.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript'):
                    with patch('tools_image.pxm.hide_app'):
                        with patch('os.path.exists', return_value=True):
                            # Test default horizontal
                            result = tools_image.flip_image(test_file)
                            self.assertIn("Flipped horizontal", result)

                            # Test vertical
                            result = tools_image.flip_image(f"{test_file} vertical")
                            self.assertIn("Flipped vertical", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_grayscale_image_script(self):
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-gray.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript') as mock_run:
                    with patch('tools_image.pxm.hide_app'):
                        with patch('os.path.exists', return_value=True):
                            result = tools_image.grayscale_image(test_file)
                            self.assertIn("Converted to grayscale", result)

                            script = mock_run.call_args[0][0]
                            self.assertIn("black and white", script)
                            self.assertIn("saving no", script)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_enhance_image_script(self):
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-enhance.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript') as mock_run:
                    with patch('tools_image.pxm.hide_app'):
                        with patch('os.path.exists', return_value=True):
                            result = tools_image.enhance_image(test_file)
                            self.assertIn("Enhanced", result)

                            script = mock_run.call_args[0][0]
                            self.assertIn("enh", script)
                            self.assertIn("saving no", script)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('tools_image._get_image_dimensions')
    def test_crop_square_script(self, mock_dims):
        mock_dims.return_value = (1000, 800)

        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-crop.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image.pxm.build_lock'):
                with patch('tools_image.pxm.run_applescript') as mock_run:
                    with patch('tools_image.pxm.hide_app'):
                        with patch('os.path.exists', return_value=True):
                            result = tools_image.crop_square(test_file)
                            self.assertIn("Cropped to 800x800 square", result)

                            script = mock_run.call_args[0][0]
                            self.assertIn("crop", script)
                            self.assertIn("saving no", script)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('tools_image._get_image_dimensions')
    def test_image_info(self, mock_dims):
        mock_dims.return_value = (1920, 1080)

        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-info.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            result = tools_image.image_info(test_file)
            self.assertIn("1920x1080", result)
            self.assertIn("1 layer", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == "__main__":
    unittest.main()
