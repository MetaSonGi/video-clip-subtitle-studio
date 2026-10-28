import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
import studio
from studio import draft, ollama_generate, source, transcribe_audio, trim, output, transcript_text

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

class TranscriptTests(unittest.TestCase):
    def test_webvtt_and_blank_lines_filtered(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.vtt'
            p.write_text('WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n첫 문장\n\n00:00:01.000 --> 00:00:02.000\n두 번째 문장\n', encoding='utf-8')
            self.assertEqual(transcript_text(p), '첫 문장\n두 번째 문장')

    def test_non_utf8_and_empty_draft_raise(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / 'bad.srt'
            bad.write_bytes(b'\xff\xfe\x00\x01 not utf8')
            with self.assertRaises(ValueError):
                transcript_text(bad)
            empty = Path(d) / 'empty.srt'
            empty.write_text('1\n00:00:00,000 --> 00:00:01,000\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                draft(empty, Path(d) / 'draft.md')
            with self.assertRaises(ValueError):
                source(Path(d) / 'missing.srt')


class FakeResponse:
    """urlopen 흉내: with 문을 지원하고 JSON 바이트를 돌려준다."""
    def __init__(self, payload):
        self._buf = io.BytesIO(json.dumps(payload).encode('utf-8'))
    def __enter__(self):
        return self._buf
    def __exit__(self, *exc):
        self._buf.close()
        return False


class OllamaMockTests(unittest.TestCase):
    def test_generate_success_uses_localhost(self):
        seen = {}

        def fake_urlopen(req, timeout=None):
            seen['url'] = req.full_url
            seen['payload'] = json.loads(req.data.decode('utf-8'))
            return FakeResponse({'response': '훅: 테스트 초안'})
        body = ollama_generate('로봇 관절 제어', 'test-model', urlopen=fake_urlopen)
        self.assertEqual(body, '훅: 테스트 초안')
        self.assertEqual(seen['url'], 'http://127.0.0.1:11434/api/generate')
        self.assertEqual(seen['payload']['model'], 'test-model')
        self.assertFalse(seen['payload']['stream'])

    def test_generate_failure_becomes_value_error(self):
        def failing_urlopen(req, timeout=None):
            raise urllib.error.URLError('connection refused')
        with self.assertRaises(ValueError):
            ollama_generate('텍스트', 'test-model', urlopen=failing_urlopen)
        with self.assertRaises(ValueError):
            ollama_generate('텍스트', 'test-model',
                            urlopen=lambda req, timeout=None: FakeResponse({}))
        with self.assertRaises(ValueError):
            ollama_generate('텍스트', '   ')

    def test_draft_with_mocked_ollama(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.srt'
            p.write_text('1\n00:00:00,000 --> 00:00:01,000\n로봇 관절 제어\n', encoding='utf-8')
            with mock.patch('urllib.request.urlopen',
                            return_value=FakeResponse({'response': 'AI 초안 본문'})):
                result = draft(p, Path(d) / 'draft.md', model='test-model')
            self.assertIn('Ollama 생성 초안', result['mode'])
            self.assertIn('AI 초안 본문', (Path(d) / 'draft.md').read_text(encoding='utf-8'))


class WhisperMockTests(unittest.TestCase):
    def test_transcribe_with_fake_model(self):
        calls = []

        class FakeModel:
            def transcribe(self, src, language=None, fp16=False):
                calls.append(('transcribe', src, language))
                return {'segments': [{}, {}], 'text': '가짜 자막'}

        def fake_writer(fmt, folder):
            def write(data, src):
                calls.append(('write', fmt, folder, src))
            return write

        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'demo.mp4'
            src.write_bytes(b'fake video bytes')
            result = transcribe_audio(src, Path(d) / 'subs', 'base', 'ko',
                                      load_model=lambda name: FakeModel(),
                                      get_writer=fake_writer)
            self.assertEqual(result['segments'], 2)
            self.assertEqual([c[1] for c in calls if c[0] == 'write'], ['srt', 'txt'])

    def test_transcribe_guards_before_loading_model(self):
        loaded = []
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'subs'
            folder.mkdir()
            src = Path(d) / 'demo.mp4'
            src.write_bytes(b'fake')
            (folder / 'demo.srt').write_text('이미 있음', encoding='utf-8')
            with self.assertRaises(ValueError):
                transcribe_audio(src, folder, 'base', 'ko',
                                 load_model=lambda name: loaded.append(name) or None,
                                 get_writer=lambda fmt, folder: (lambda data, s: None))
            self.assertEqual(loaded, [])
            with self.assertRaises(ValueError):
                transcribe_audio(src, Path(d) / 'subs2', '   ', 'ko',
                                 load_model=lambda name: None,
                                 get_writer=lambda fmt, folder: (lambda data, s: None))


class TrimMockTests(unittest.TestCase):
    def test_trim_command_and_duration_guard(self):
        seen = []

        def fake_run(cmd):
            seen.append(cmd)
            if cmd[0] == 'ffprobe':
                return json.dumps({'format': {'duration': '10.0'}})
            return ''
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'in.mp4'
            src.write_bytes(b'fake')
            with mock.patch.object(studio, 'run', side_effect=fake_run), \
                 mock.patch.object(studio, 'require', side_effect=lambda name: name):
                result = trim(src, Path(d) / 'clip.mp4', 1, 3)
            self.assertEqual(result['mode'], 'stream-copy')
            self.assertIn('copy', seen[1])
            with mock.patch.object(studio, 'run', return_value=json.dumps({'format': {'duration': '10.0'}})), \
                 mock.patch.object(studio, 'require', side_effect=lambda name: name):
                with self.assertRaises(ValueError):
                    trim(src, Path(d) / 'clip2.mp4', 1, 11)

    def test_trim_rejects_non_numeric_bounds(self):
        for a, b in [('3', 5), (0, True), (None, 5)]:
            with self.assertRaises(ValueError):
                trim('missing', 'out.mp4', a, b)


class CliTests(unittest.TestCase):
    def test_doctor_and_draft_via_cli(self):
        studio_py = Path(__file__).resolve().parent / 'studio.py'
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run([sys.executable, str(studio_py), 'doctor'],
                                  capture_output=True, text=True, cwd=d)
            self.assertEqual(proc.returncode, 0)
            self.assertIn('python', json.loads(proc.stdout))
            srt = Path(d) / 'demo.srt'
            srt.write_text('1\n00:00:00,000 --> 00:00:03,000\n데모 문장\n', encoding='utf-8')
            proc = subprocess.run([sys.executable, str(studio_py), 'draft',
                                   str(srt), str(Path(d) / 'draft.md')],
                                  capture_output=True, text=True, cwd=d)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('AI 생성 아님', (Path(d) / 'draft.md').read_text(encoding='utf-8'))
            proc = subprocess.run([sys.executable, str(studio_py)],
                                  capture_output=True, text=True, cwd=d)
            self.assertNotEqual(proc.returncode, 0)


if __name__ == '__main__': unittest.main()
