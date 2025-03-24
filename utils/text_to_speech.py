import os
import logging
import time
from gtts import gTTS
from typing import Tuple, Optional
import json
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TextToSpeechService:
    def __init__(self, gemini_service):
        """
        Initialize the TTS service with Gemini as the primary translator.
        
        Args:
            gemini_service: An instance of the GeminiService for translation.
        """
        self.gemini_service = gemini_service
        
        # Create cache directory if it doesn't exist
        os.makedirs("data/cache/translations", exist_ok=True)
        logging.info("TTS service initialized with Gemini as the primary translator")

    def _get_cache_key(self, text: str) -> str:
        """Generate a simple cache key from text."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()

    def _check_translation_cache(self, cache_key: str) -> Optional[str]:
        """Check if translation exists in cache."""
        cache_path = f"data/cache/translations/{cache_key}.json"
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('translation')
            except:
                return None
        return None

    def _save_translation_to_cache(self, cache_key: str, translation: str) -> None:
        """Save translation to cache."""
        cache_path = f"data/cache/translations/{cache_key}.json"
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({'translation': translation}, f, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving translation to cache: {str(e)}")

    def translate_to_hindi(self, text: str) -> str:
        """
        Translate English text to Hindi using Gemini.
        
        Args:
            text: English text to translate
            
        Returns:
            Hindi translation of the text
        """
        # Check cache first
        cache_key = self._get_cache_key(text[:1000])  # Use first 1000 chars for key
        cached_translation = self._check_translation_cache(cache_key)
        if cached_translation:
            logging.info("Using cached translation")
            return cached_translation

        # Translate using Gemini
        try:
            prompt = f"Translate the following English text to Hindi. Return ONLY the Hindi translation, no additional comments:\n\n{text}"
            hindi_text = self.gemini_service._call_api_with_retry(prompt).strip()
            
            # Save to cache
            self._save_translation_to_cache(cache_key, hindi_text)
            return hindi_text
        except Exception as e:
            logging.error(f"Gemini translation failed: {str(e)}")
            raise Exception("Translation failed. Please check the Gemini API key and configuration.")

    def generate_audio(self, text: str, output_path: str) -> bool:
        """
        Generate speech from text using gTTS and save it to the specified path.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # gTTS has character limits, so break text into chunks if needed
            max_chunk_size = 3000
            if len(text) > max_chunk_size:
                # For long text, create temporary files and then combine them
                temp_files = []
                chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
                
                for i, chunk in enumerate(chunks):
                    temp_path = f"{output_path}.part{i}.mp3"
                    tts = gTTS(text=chunk, lang='hi', slow=False)
                    tts.save(temp_path)
                    temp_files.append(temp_path)
                    time.sleep(1)  # Prevent rate limiting
                
                # Combine audio files (requires ffmpeg)
                try:
                    import subprocess
                    with open("file_list.txt", "w") as f:
                        for temp_file in temp_files:
                            f.write(f"file '{temp_file}'\n")
                    
                    cmd = [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
                        "-i", "file_list.txt", "-c", "copy", output_path
                    ]
                    subprocess.run(cmd, check=True)
                    
                    # Clean up temp files
                    os.remove("file_list.txt")
                    for temp_file in temp_files:
                        os.remove(temp_file)
                except Exception as ffmpeg_error:
                    logging.error(f"Error combining audio files: {str(ffmpeg_error)}")
                    # If ffmpeg fails, just use the first chunk as fallback
                    if temp_files:
                        import shutil
                        shutil.copy(temp_files[0], output_path)
                        logging.warning("Using only first audio chunk due to ffmpeg error")
                        # Clean up temp files
                        for temp_file in temp_files:
                            os.remove(temp_file)
            else:
                # For short text, generate directly
                tts = gTTS(text=text, lang='hi', slow=False)
                tts.save(output_path)
            
            logging.info(f"Speech generated and saved to {output_path}")
            return True
        except Exception as e:
            logging.error(f"TTS error: {str(e)}")
            return False

    def generate_hindi_speech_from_english(self, text: str, save_path: str) -> Tuple[Optional[str], str]:
        """
        Translate English text to Hindi and generate speech.
        
        Args:
            text: English text to translate and convert to speech
            save_path: Path to save the audio file
            
        Returns:
            Tuple of (audio_path, hindi_text)
        """
        logging.info(f"Starting translation and TTS for text: {text[:100]}...")  # Log first 100 chars
        
        # Translate to Hindi
        try:
            hindi_text = self.translate_to_hindi(text)
            logging.info(f"Translation successful. Hindi text: {hindi_text[:100]}...")  # Log first 100 chars
        except Exception as e:
            logging.error(f"Translation failed: {str(e)}")
            return None, ""
        
        # Generate speech
        try:
            success = self.generate_audio(hindi_text, save_path)
            if success:
                logging.info(f"Speech generated and saved to: {save_path}")
                return save_path, hindi_text
            else:
                logging.error("Speech generation failed")
                return None, hindi_text
        except Exception as e:
            logging.error(f"Speech generation failed: {str(e)}")
            return None, hindi_text