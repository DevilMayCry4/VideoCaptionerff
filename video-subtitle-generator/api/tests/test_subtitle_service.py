import unittest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, mock_open
import json

from src.services.subtitle_service import SubtitleService


class TestSubtitleService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = SubtitleService()
        self.sample_audio_path = os.path.join(self.temp_dir, 'sample.wav')
        self.output_srt_path = os.path.join(self.temp_dir, 'output.srt')
        
        # Create a dummy audio file for testing
        with open(self.sample_audio_path, 'wb') as f:
            f.write(b'dummy audio content')
    
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.temp_dir)
    
    @patch('src.services.subtitle_service.WhisperModel')
    def test_generate_subtitle_success(self, mock_whisper_model):
        """Test successful subtitle generation from audio file."""
        # Mock Whisper model and its methods
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance
        
        # Mock transcription result
        mock_segments = [
            {
                'id': 0,
                'start': 0.0,
                'end': 2.5,
                'text': 'Hello world'
            },
            {
                'id': 1,
                'start': 3.0,
                'end': 5.2,
                'text': 'This is a test'
            }
        ]
        
        mock_transcription = {
            'segments': mock_segments,
            'language': 'en',
            'text': 'Hello world This is a test'
        }
        
        mock_model_instance.transcribe.return_value = mock_transcription
        
        result = self.service.generate_subtitle(
            self.sample_audio_path,
            'test-task-123',
            language='en',
            beam_size=5,
            best_of=5,
            temperature=0.0
        )
        
        # Verify Whisper model was called correctly
        mock_whisper_model.assert_called_once_with('base')
        mock_model_instance.transcribe.assert_called_once_with(
            self.sample_audio_path,
            language='en',
            beam_size=5,
            best_of=5,
            temperature=0.0,
            word_timestamps=False
        )
        
        # Verify result structure
        self.assertEqual(result['task_id'], 'test-task-123')
        self.assertEqual(result['language'], 'en')
        self.assertEqual(result['segments_count'], 2)
        self.assertIn('subtitle_content', result)
        self.assertIn('processing_time', result)
    
    @patch('src.services.subtitle_service.WhisperModel')
    def test_generate_subtitle_auto_language_detection(self, mock_whisper_model):
        """Test subtitle generation with automatic language detection."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance
        
        mock_segments = [
            {
                'id': 0,
                'start': 0.0,
                'end': 2.5,
                'text': '你好世界'
            }
        ]
        
        mock_transcription = {
            'segments': mock_segments,
            'language': 'zh',
            'text': '你好世界'
        }
        
        mock_model_instance.transcribe.return_value = mock_transcription
        
        result = self.service.generate_subtitle(
            self.sample_audio_path,
            'test-task-123',
            language=None,  # Auto-detect
            beam_size=5,
            best_of=5,
            temperature=0.0
        )
        
        # Verify language was auto-detected
        mock_model_instance.transcribe.assert_called_once_with(
            self.sample_audio_path,
            language=None,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            word_timestamps=False
        )
        
        self.assertEqual(result['language'], 'zh')
    
    @patch('src.services.subtitle_service.WhisperModel')
    def test_generate_subtitle_different_model_size(self, mock_whisper_model):
        """Test subtitle generation with different model sizes."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance
        
        mock_transcription = {
            'segments': [],
            'language': 'en',
            'text': ''
        }
        
        mock_model_instance.transcribe.return_value = mock_transcription
        
        # Test with different model sizes
        for model_size in ['tiny', 'base', 'small', 'medium', 'large']:
            mock_whisper_model.reset_mock()
            mock_model_instance.transcribe.reset_mock()
            
            self.service.model_size = model_size
            result = self.service.generate_subtitle(
                self.sample_audio_path,
                'test-task-123'
            )
            
            mock_whisper_model.assert_called_once_with(model_size)
            self.assertEqual(result['task_id'], 'test-task-123')
    
    @patch('src.services.subtitle_service.WhisperModel')
    def test_generate_subtitle_whisper_error(self, mock_whisper_model):
        """Test subtitle generation when Whisper model fails."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance
        
        mock_model_instance.transcribe.side_effect = Exception('Whisper error')
        
        with self.assertRaises(Exception) as context:
            self.service.generate_subtitle(
                self.sample_audio_path,
                'test-task-123'
            )
        
        self.assertIn('Whisper error', str(context.exception))
    
    def test_generate_subtitle_invalid_audio_file(self):
        """Test subtitle generation with non-existent audio file."""
        non_existent_audio = '/path/to/nonexistent/audio.wav'
        
        with self.assertRaises(FileNotFoundError):
            self.service.generate_subtitle(
                non_existent_audio,
                'test-task-123'
            )
    
    def test_convert_to_srt_format(self):
        """Test conversion of transcription segments to SRT format."""
        segments = [
            {
                'id': 0,
                'start': 0.0,
                'end': 2.5,
                'text': 'Hello world'
            },
            {
                'id': 1,
                'start': 3.0,
                'end': 5.2,
                'text': 'This is a test'
            },
            {
                'id': 2,
                'start': 6.0,
                'end': 8.75,
                'text': 'Final segment'
            }
        ]
        
        srt_content = self.service.convert_to_srt_format(segments)
        
        # Verify SRT format
        expected_lines = [
            '1',
            '00:00:00,000 --> 00:00:02,500',
            'Hello world',
            '',
            '2',
            '00:00:03,000 --> 00:00:05,200',
            'This is a test',
            '',
            '3',
            '00:00:06,000 --> 00:00:08,750',
            'Final segment',
            ''
        ]
        
        expected_content = '\n'.join(expected_lines)
        self.assertEqual(srt_content, expected_content)
    
    def test_convert_to_srt_format_empty_segments(self):
        """Test conversion of empty segments to SRT format."""
        segments = []
        
        srt_content = self.service.convert_to_srt_format(segments)
        
        self.assertEqual(srt_content, '')
    
    def test_convert_to_srt_format_single_segment(self):
        """Test conversion of single segment to SRT format."""
        segments = [
            {
                'id': 0,
                'start': 0.0,
                'end': 2.5,
                'text': 'Single segment'
            }
        ]
        
        srt_content = self.service.convert_to_srt_format(segments)
        
        expected_lines = [
            '1',
            '00:00:00,000 --> 00:00:02,500',
            'Single segment',
            ''
        ]
        
        expected_content = '\n'.join(expected_lines)
        self.assertEqual(srt_content, expected_content)
    
    def test_format_timestamp(self):
        """Test timestamp formatting for SRT format."""
        # Test various timestamps
        test_cases = [
            (0.0, '00:00:00,000'),
            (1.5, '00:00:01,500'),
            (65.25, '00:01:05,250'),
            (3661.999, '01:01:01,999'),
            (0.001, '00:00:00,001'),
            (3599.999, '00:59:59,999')
        ]
        
        for timestamp, expected in test_cases:
            result = self.service.format_timestamp(timestamp)
            self.assertEqual(result, expected)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_subtitle_file_success(self, mock_file):
        """Test saving subtitle content to file."""
        subtitle_content = '1\n00:00:00,000 --> 00:00:02,500\nHello world\n\n'
        
        result = self.service.save_subtitle_file(
            subtitle_content,
            self.output_srt_path
        )
        
        # Verify file was opened and written correctly
        mock_file.assert_called_once_with(self.output_srt_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(subtitle_content)
        
        self.assertEqual(result, self.output_srt_path)
    
    def test_save_subtitle_file_invalid_path(self):
        """Test saving subtitle file to invalid path."""
        invalid_path = '/invalid/path/subtitle.srt'
        subtitle_content = '1\n00:00:00,000 --> 00:00:02,500\nHello world\n\n'
        
        with self.assertRaises(Exception):
            self.service.save_subtitle_file(subtitle_content, invalid_path)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_subtitle_file_empty_content(self, mock_file):
        """Test saving empty subtitle content to file."""
        subtitle_content = ''
        
        result = self.service.save_subtitle_file(
            subtitle_content,
            self.output_srt_path
        )
        
        mock_file.assert_called_once_with(self.output_srt_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(subtitle_content)
        
        self.assertEqual(result, self.output_srt_path)
    
    @patch('src.services.subtitle_service.WhisperModel')
    def test_generate_subtitle_with_custom_temperature(self, mock_whisper_model):
        """Test subtitle generation with custom temperature parameter."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance
        
        mock_transcription = {
            'segments': [],
            'language': 'en',
            'text': ''
        }
        
        mock_model_instance.transcribe.return_value = mock_transcription
        
        result = self.service.generate_subtitle(
            self.sample_audio_path,
            'test-task-123',
            temperature=0.8
        )
        
        # Verify custom temperature was used
        mock_model_instance.transcribe.assert_called_once_with(
            self.sample_audio_path,
            language=None,
            beam_size=5,
            best_of=5,
            temperature=0.8,
            word_timestamps=False
        )
        
        self.assertEqual(result['task_id'], 'test-task-123')
    
    def test_format_timestamp_edge_cases(self):
        """Test timestamp formatting edge cases."""
        # Test very small and very large timestamps
        edge_cases = [
            (0.0001, '00:00:00,000'),
            (0.0009, '00:00:00,001'),
            (99999.999, '27:46:39,999'),
            (-0.001, '00:00:00,000')  # Negative timestamps should be clamped to 0
        ]
        
        for timestamp, expected in edge_cases:
            result = self.service.format_timestamp(timestamp)
            self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()