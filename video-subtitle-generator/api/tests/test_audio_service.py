import unittest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import ffmpeg

from src.services.audio_service import AudioService


class TestAudioService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = AudioService()
        self.sample_video_path = os.path.join(self.temp_dir, 'sample.mp4')
        self.output_audio_path = os.path.join(self.temp_dir, 'output.wav')
        
        # Create a dummy video file for testing
        with open(self.sample_video_path, 'wb') as f:
            f.write(b'dummy video content')
    
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.temp_dir)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_extract_audio_success(self, mock_ffmpeg):
        """Test successful audio extraction from video file."""
        # Mock ffmpeg chain
        mock_input = Mock()
        mock_output = Mock()
        mock_run = Mock()
        
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.return_value = mock_run
        
        result = self.service.extract_audio(
            self.sample_video_path,
            self.output_audio_path,
            sample_rate=16000,
            channels=1
        )
        
        # Verify ffmpeg was called correctly
        mock_ffmpeg.input.assert_called_once_with(self.sample_video_path)
        mock_input.output.assert_called_once_with(
            self.output_audio_path,
            vn=None,
            acodec='pcm_s16le',
            ar=16000,
            ac=1,
            loglevel='error'
        )
        mock_output.overwrite_output.assert_called_once()
        mock_output.run.assert_called_once()
        
        self.assertEqual(result, self.output_audio_path)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_extract_audio_with_custom_params(self, mock_ffmpeg):
        """Test audio extraction with custom parameters."""
        mock_input = Mock()
        mock_output = Mock()
        mock_run = Mock()
        
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.return_value = mock_run
        
        result = self.service.extract_audio(
            self.sample_video_path,
            self.output_audio_path,
            sample_rate=44100,
            channels=2
        )
        
        # Verify custom parameters were used
        mock_input.output.assert_called_once_with(
            self.output_audio_path,
            vn=None,
            acodec='pcm_s16le',
            ar=44100,
            ac=2,
            loglevel='error'
        )
        
        self.assertEqual(result, self.output_audio_path)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_extract_audio_ffmpeg_error(self, mock_ffmpeg):
        """Test audio extraction when ffmpeg fails."""
        # Mock ffmpeg to raise an error
        mock_input = Mock()
        mock_output = Mock()
        
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.side_effect = ffmpeg.Error('ffmpeg error', 'stdout', 'stderr')
        
        with self.assertRaises(Exception) as context:
            self.service.extract_audio(
                self.sample_video_path,
                self.output_audio_path
            )
        
        self.assertIn('ffmpeg error', str(context.exception))
    
    def test_extract_audio_invalid_input_file(self):
        """Test audio extraction with non-existent input file."""
        non_existent_file = '/path/to/nonexistent/file.mp4'
        
        with self.assertRaises(FileNotFoundError):
            self.service.extract_audio(
                non_existent_file,
                self.output_audio_path
            )
    
    def test_extract_audio_invalid_output_path(self):
        """Test audio extraction with invalid output path."""
        invalid_output_path = '/invalid/path/output.wav'
        
        with self.assertRaises(Exception):
            self.service.extract_audio(
                self.sample_video_path,
                invalid_output_path
            )
    
    def test_validate_audio_file_exists(self):
        """Test audio file validation with existing file."""
        # Create a dummy audio file
        audio_file = os.path.join(self.temp_dir, 'audio.wav')
        with open(audio_file, 'wb') as f:
            f.write(b'dummy audio content')
        
        result = self.service.validate_audio_file(audio_file)
        self.assertTrue(result)
    
    def test_validate_audio_file_not_exists(self):
        """Test audio file validation with non-existent file."""
        non_existent_audio = '/path/to/nonexistent/audio.wav'
        
        result = self.service.validate_audio_file(non_existent_audio)
        self.assertFalse(result)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_get_audio_info_success(self, mock_ffmpeg):
        """Test getting audio information from video file."""
        # Mock probe result
        mock_probe_result = {
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'aac',
                'sample_rate': '44100',
                'channels': 2,
                'duration': '120.5'
            }],
            'format': {
                'duration': '120.5',
                'size': '1048576'
            }
        }
        
        mock_ffmpeg.probe.return_value = mock_probe_result
        
        result = self.service.get_audio_info(self.sample_video_path)
        
        mock_ffmpeg.probe.assert_called_once_with(self.sample_video_path)
        
        self.assertEqual(result['duration'], 120.5)
        self.assertEqual(result['sample_rate'], 44100)
        self.assertEqual(result['channels'], 2)
        self.assertEqual(result['codec'], 'aac')
        self.assertEqual(result['size'], 1048576)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_get_audio_info_no_audio_stream(self, mock_ffmpeg):
        """Test getting audio information when no audio stream exists."""
        # Mock probe result with no audio streams
        mock_probe_result = {
            'streams': [{
                'codec_type': 'video',
                'codec_name': 'h264'
            }],
            'format': {
                'duration': '120.5',
                'size': '1048576'
            }
        }
        
        mock_ffmpeg.probe.return_value = mock_probe_result
        
        result = self.service.get_audio_info(self.sample_video_path)
        
        self.assertEqual(result['duration'], 120.5)
        self.assertEqual(result['sample_rate'], 0)
        self.assertEqual(result['channels'], 0)
        self.assertEqual(result['codec'], '')
        self.assertEqual(result['size'], 1048576)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_get_audio_info_probe_error(self, mock_ffmpeg):
        """Test getting audio information when ffmpeg probe fails."""
        mock_ffmpeg.probe.side_effect = ffmpeg.Error('probe error', 'stdout', 'stderr')
        
        with self.assertRaises(Exception) as context:
            self.service.get_audio_info(self.sample_video_path)
        
        self.assertIn('probe error', str(context.exception))
    
    def test_get_audio_info_invalid_file(self):
        """Test getting audio information from non-existent file."""
        non_existent_file = '/path/to/nonexistent/file.mp4'
        
        with self.assertRaises(FileNotFoundError):
            self.service.get_audio_info(non_existent_file)
    
    @patch('src.services.audio_service.ffmpeg')
    def test_extract_audio_default_parameters(self, mock_ffmpeg):
        """Test audio extraction uses default parameters correctly."""
        mock_input = Mock()
        mock_output = Mock()
        mock_run = Mock()
        
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.return_value = mock_run
        
        result = self.service.extract_audio(
            self.sample_video_path,
            self.output_audio_path
        )
        
        # Verify default parameters were used
        mock_input.output.assert_called_once_with(
            self.output_audio_path,
            vn=None,
            acodec='pcm_s16le',
            ar=16000,
            ac=1,
            loglevel='error'
        )
        
        self.assertEqual(result, self.output_audio_path)


if __name__ == '__main__':
    unittest.main()