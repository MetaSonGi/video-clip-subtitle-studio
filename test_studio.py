import tempfile
import unittest
from pathlib import Path
from studio import draft, trim, output, transcript_text

class StudioTests(unittest.TestCase):
    def test_srt_and_draft(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.srt'; p.write_text('1\n00:00:00,000 --> 00:00:01,000\n로봇 관절 제어\n',encoding='utf-8')
            self.assertEqual(transcript_text(p),'로봇 관절 제어')
            dest=Path(d)/'draft.md'; draft(p,dest)
            self.assertIn('AI 생성 아님',dest.read_text(encoding='utf-8'))
            with self.assertRaises(ValueError): output(dest)
    def test_invalid_trim(self):
        for a,b in [(2,1),(-1,1),(0,float('nan'))]:
            with self.assertRaises(ValueError): trim('missing','out.mp4',a,b)

if __name__=='__main__': unittest.main()
