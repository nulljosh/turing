#!/usr/bin/env python3
"""Unit tests for image tools. Mocks _run so the argv shape is pinned without a real ImageMagick call."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools_image


class TestImageTools(unittest.TestCase):
    """Unit tests for the image tools with `magick` mocked out."""
    def setUp(self):
        """Point the tools at a temporary home with a sample image."""
        self.temp_dir = tempfile.mkdtemp()
        self.home = os.path.expanduser("~")

        # Create a test image file
        self.test_image = os.path.join(self.temp_dir, "test.jpg")
        with open(self.test_image, "wb") as f:
            f.write(b"fake jpg data")

    def tearDown(self):
        """Remove the temporary home."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_remove_background_path_outside_home(self):
        """Remove background path outside home."""
        result = tools_image.remove_background("/etc/passwd")
        self.assertIn("No image at", result)

    def test_remove_background_missing_file(self):
        """Remove background missing file."""
        result = tools_image.remove_background("~/nonexistent.jpg")
        self.assertIn("No image at", result)

    def test_remove_background_non_image(self):
        """Remove background non image."""
        temp_txt = os.path.join(self.temp_dir, "test.txt")
        with open(temp_txt, "w") as f:
            f.write("not an image")
        result = tools_image.remove_background(temp_txt)
        self.assertIn("No image at", result)

    @patch('tools_image._run')
    @patch('tools_image._get_image_dimensions', return_value=(1000, 500))
    def test_remove_background_script_generation(self, mock_dims, mock_run):
        """Remove background builds a floodfill-from-corners magick call."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-remove-bg.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('os.path.exists', return_value=True):
                result = tools_image.remove_background(test_file)
                self.assertIn("Background removed", result)

                self.assertTrue(mock_run.called)
                argv = mock_run.call_args[0][0]
                self.assertEqual(argv[0], "magick")
                self.assertEqual(argv[1], test_file)
                self.assertIn("-fuzz", argv)
                self.assertIn("12%", argv)
                self.assertIn("alpha 0,0 floodfill", argv)
                self.assertIn("alpha 999,499 floodfill", argv)
                # Output path should NOT be input path
                self.assertNotIn("samantha-nobg.png", test_file)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('tools_image._run')
    def test_upscale_image_script(self, mock_run):
        """Upscale image runs the Lanczos 300% resize."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-upscale.png")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake png")

        try:
            with patch('os.path.exists', return_value=True):
                result = tools_image.upscale_image(test_file)
                self.assertIn("Upscaled", result)

                argv = mock_run.call_args[0][0]
                self.assertIn("-filter", argv)
                self.assertIn("Lanczos", argv)
                self.assertIn("-resize", argv)
                self.assertIn("300%", argv)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_rotate_image_parsing(self):
        """Rotate image parsing."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-rotate.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image._run'), patch('os.path.exists', return_value=True):
                result = tools_image.rotate_image(f"{test_file} by 180")
                self.assertIn("Rotated 180", result)

            result = tools_image.rotate_image(f"{test_file} by 45")
            self.assertIn("must be 90, 180, or 270", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_resize_image_parsing(self):
        """Resize image parsing."""
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
        """Convert image parsing."""
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
            with patch('tools_image._run'), patch('os.path.exists', return_value=True):
                result = tools_image.convert_image(f"{test_file} to jpg")
                self.assertIn("Converted to JPG", result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_flip_image_parsing(self):
        """Flip image parsing."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-flip.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image._run') as mock_run, patch('os.path.exists', return_value=True):
                # Test default horizontal
                result = tools_image.flip_image(test_file)
                self.assertIn("Flipped horizontal", result)
                self.assertIn("-flop", mock_run.call_args[0][0])

                # Test vertical
                result = tools_image.flip_image(f"{test_file} vertical")
                self.assertIn("Flipped vertical", result)
                self.assertIn("-flip", mock_run.call_args[0][0])
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_grayscale_image_script(self):
        """Grayscale image runs -colorspace Gray."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-gray.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image._run') as mock_run, patch('os.path.exists', return_value=True):
                result = tools_image.grayscale_image(test_file)
                self.assertIn("Converted to grayscale", result)

                argv = mock_run.call_args[0][0]
                self.assertIn("-colorspace", argv)
                self.assertIn("Gray", argv)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_enhance_image_script(self):
        """Enhance image runs auto-level, auto-gamma and unsharp."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-enhance.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image._run') as mock_run, patch('os.path.exists', return_value=True):
                result = tools_image.enhance_image(test_file)
                self.assertIn("Enhanced", result)

                argv = mock_run.call_args[0][0]
                self.assertIn("-auto-level", argv)
                self.assertIn("-auto-gamma", argv)
                self.assertIn("-unsharp", argv)
                self.assertIn("0x1", argv)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('tools_image._get_image_dimensions')
    def test_crop_square_script(self, mock_dims):
        """Crop square script."""
        mock_dims.return_value = (1000, 800)

        home = os.path.expanduser("~")
        test_file = os.path.join(home, ".claude", "test-crop.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "wb") as f:
            f.write(b"fake jpg")

        try:
            with patch('tools_image._run') as mock_run, patch('os.path.exists', return_value=True):
                result = tools_image.crop_square(test_file)
                self.assertIn("Cropped to 800x800 square", result)

                argv = mock_run.call_args[0][0]
                self.assertIn("-crop", argv)
                self.assertIn("800x800+100+0", argv)
                self.assertIn("+repage", argv)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch('tools_image._get_image_dimensions')
    def test_image_info(self, mock_dims):
        """Image info."""
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


class TestEveryToolScript(unittest.TestCase):
    """Pins the exact magick argv, output path and reply of every image tool, so a refactor cannot drift."""

    CASES = [
        (tools_image.upscale_image, "{p}", ["-filter", "Lanczos", "-resize", "300%"], "upscaled.png", "Upscaled 3x"),
        (tools_image.enhance_image, "{p}", ["-auto-level", "-auto-gamma", "-unsharp", "0x1"], "enhanced.png", "Enhanced"),
        (tools_image.grayscale_image, "{p}", ["-colorspace", "Gray"], "grayscale.png", "Converted to grayscale"),
        (tools_image.rotate_image, "{p} by 180", ["-rotate", "180"], "rotated.png", "Rotated 180 degrees"),
        (tools_image.rotate_image, "{p}", ["-rotate", "90"], "rotated.png", "Rotated 90 degrees"),
        (tools_image.flip_image, "{p} vertical", ["-flip"], "flipped.png", "Flipped vertical"),
        (tools_image.flip_image, "{p}", ["-flop"], "flipped.png", "Flipped horizontal"),
        (tools_image.resize_image, "{p} to 500", ["-resize", "500x250!"], "resized.png", "Resized to 500x250"),
        (tools_image.crop_square, "{p}", ["-crop", "500x500+250+0", "+repage"], "square.png", "Cropped to 500x500 square"),
        (tools_image.convert_image, "{p} to jpg", [], "converted.jpg", "Converted to JPG"),
    ]

    def test_every_tool(self):
        """Each tool runs `magick <in> <args> <out>` and says where the result went."""
        path = os.path.join(os.path.expanduser("~"), "samantha-test-every.png")
        with open(path, "wb") as f:
            f.write(b"fake png")
        try:
            for fn, args, middle, out, said in self.CASES:
                with self.subTest(fn=fn.__name__, args=args), patch("tools_image._run") as run, \
                     patch("tools_image._get_image_dimensions", return_value=(1000, 500)):
                    result = fn(args.format(p=path))
                    argv = run.call_args[0][0]
                    self.assertEqual(argv[0], "magick")
                    self.assertEqual(argv[1], path)
                    self.assertEqual(argv[2:-1], middle, argv)
                    self.assertTrue(argv[-1].endswith(f"samantha-{out}"), argv[-1])
                    # nothing was really exported, so the reply is the honest failure, never a claimed success
                    self.assertTrue(result.startswith("Failed"), result)
                with patch("tools_image._run"), patch("tools_image._get_image_dimensions", return_value=(1000, 500)), \
                     patch("os.path.exists", return_value=True), patch("os.remove"):
                    self.assertTrue(fn(args.format(p=path)).startswith(said + ", saved to "), fn.__name__)
        finally:
            os.remove(path)

    def test_remove_background_touches_all_four_corners(self):
        """remove_background floods from every corner, not just the origin."""
        path = os.path.join(os.path.expanduser("~"), "samantha-test-nobg.png")
        with open(path, "wb") as f:
            f.write(b"fake png")
        try:
            with patch("tools_image._run") as run, patch("tools_image._get_image_dimensions", return_value=(1000, 500)), \
                 patch("os.path.exists", return_value=True), patch("os.remove"):
                result = tools_image.remove_background(path)
                self.assertTrue(result.startswith("Background removed, saved to "))
                argv = run.call_args[0][0]
                for corner in ("alpha 0,0 floodfill", "alpha 999,0 floodfill", "alpha 0,499 floodfill", "alpha 999,499 floodfill"):
                    self.assertIn(corner, argv)
                self.assertIn("-fuzz", argv)
                self.assertIn("12%", argv)
                self.assertIn("-fill", argv)
                self.assertIn("none", argv)
        finally:
            os.remove(path)


class TestNoPixelmator(unittest.TestCase):
    """tools_image.py is retired from Pixelmator entirely: every tool runs through ImageMagick, no AppleScript."""

    def test_tools_image_mentions_neither_pixelmator_nor_osascript(self):
        """Pixelmator Pro is not launched by tools_image.py, not even to compare."""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools_image.py")
        with open(path) as f:
            src = f.read()
        self.assertNotIn("Pixelmator Pro", src)
        self.assertNotIn("osascript", src)


if __name__ == "__main__":
    unittest.main()
