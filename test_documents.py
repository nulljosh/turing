"""Reading documents: text, RTF and PDF files in the home folder, and refusing everything else."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools_util as u

PDF = (b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
       b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
       b"4 0 obj<</Length 60>>stream\nBT /F1 14 Tf 20 100 Td (The dog is called Biscuit.) Tj ET\nendstream endobj\n"
       b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")


class DocumentTests(unittest.TestCase):
    """A folder of made-up documents inside the home folder, removed afterwards."""

    def setUp(self):
        """Make a visible folder under home with a text file and an RTF file."""
        self.dir = tempfile.mkdtemp(dir=os.path.expanduser("~"), prefix="samantha-doc-test-")
        self.txt = os.path.join(self.dir, "notes.txt")
        open(self.txt, "w").write("The wifi is on the fridge.\nThe dog is called Biscuit. He eats at six.\nThe car is blue.\n")
        self.rtf = os.path.join(self.dir, "letter.rtf")
        if shutil.which("textutil"):
            subprocess.run(["textutil", "-convert", "rtf", "-output", self.rtf, self.txt], capture_output=True)

    def tearDown(self):
        """Remove the folder."""
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_reads_a_text_file(self):
        """A plain text file comes back flattened to one line."""
        self.assertEqual(u.read_document(self.txt), "The wifi is on the fridge. The dog is called Biscuit. He eats at six. The car is blue.")

    @unittest.skipUnless(shutil.which("textutil"), "textutil is macOS only")
    def test_reads_rtf(self):
        """RTF goes through the system's textutil."""
        self.assertIn("Biscuit", u.read_document(self.rtf))

    @unittest.skipUnless(shutil.which("swift") and sys.platform == "darwin", "PDFKit needs macOS and swift")
    def test_reads_a_pdf(self):
        """A PDF goes through PDFKit."""
        path = os.path.join(self.dir, "pet.pdf")
        open(path, "wb").write(PDF)
        self.assertIn("Biscuit", u.read_document(path))

    def test_finds_passages(self):
        """Finding words returns the sentences that hold them, and says when there are none."""
        hit = u.find_in_document("dog\t" + self.txt)
        self.assertIn("dog is called Biscuit", hit)
        self.assertNotIn("wifi", hit)
        self.assertEqual(u.find_in_document("zebra\t" + self.txt), "I do not see zebra in that document.")
        self.assertEqual(u.find_in_document("\t" + self.txt), "Tell me what to look for.")

    def test_refuses_what_it_should(self):
        """Hidden files, files outside home, missing files and unknown types are all refused in words."""
        for bad in ("~/.ssh/id_rsa", "/etc/passwd", "~/../../etc/passwd", os.path.join(self.dir, "missing.pdf")):
            self.assertIn("allowed to read", u.read_document(bad))
        odd = os.path.join(self.dir, "thing.xyz")
        open(odd, "w").write("x")
        self.assertEqual(u.read_document(odd), "I do not read .xyz files.")

    def test_an_empty_file_says_so(self):
        """A file with no text is not a crash."""
        empty = os.path.join(self.dir, "empty.txt")
        open(empty, "w").write("   \n")
        self.assertIn("found no text", u.read_document(empty))


if __name__ == "__main__":
    unittest.main()
