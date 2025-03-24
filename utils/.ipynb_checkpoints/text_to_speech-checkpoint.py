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
    def __init__(self, translator_type="google", google_api_key=None):
        """
        Initialize the TTS service with configurable translator options.
        
        Args:
            translator_type: Type of translator to use ("google", "indicnlp", "argos", "libretranslate", or "fallback")
            google_api_key: API key for Google Translate (if using Google translator)
        """
        self.translator_type = translator_type
        self.google_api_key = google_api_key
        
        # Create cache directory if it doesn't exist
        os.makedirs("data/cache/translations", exist_ok=True)
        
        # Initialize IndianNLP if selected
        if translator_type == "indicnlp":
            try:
                from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator
                self.indic_transliterator = UnicodeIndicTransliterator()
                logging.info("IndianNLP translator initialized")
            except ImportError:
                logging.warning("IndianNLP not installed, falling back to backup translator")
                self.translator_type = "fallback"
        
        # Initialize Argos if selected
        elif translator_type == "argos":
            try:
                from argostranslate import package, translate
                # Download and install Argos packages if not already installed
                if not package.get_installed_packages():
                    package.update_package_index()
                    available_packages = package.get_available_packages()
                    package_to_install = next(
                        (pkg for pkg in available_packages if pkg.from_code == "en" and pkg.to_code == "hi"), 
                        None
                    )
                    if package_to_install:
                        package_to_install.install()
                        self.argos_translator = translate.get_translation_from_codes("en", "hi")
                        logging.info("Argos translator initialized")
                    else:
                        logging.warning("Argos English-Hindi package not available, falling back")
                        self.translator_type = "fallback"
                else:
                    self.argos_translator = translate.get_translation_from_codes("en", "hi")
                    logging.info("Argos translator initialized using existing packages")
            except ImportError:
                logging.warning("Argos not installed, falling back to backup translator")
                self.translator_type = "fallback"
    
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
        Translate English text to Hindi using the configured translator.
        
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
        
        # Break text into smaller chunks to avoid API limits
        max_chunk_size = 4000
        if len(text) > max_chunk_size:
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
            translations = []
            
            for chunk in chunks:
                # Add delay to avoid rate limiting
                time.sleep(1)
                chunk_translation = self._translate_chunk(chunk)
                translations.append(chunk_translation)
            
            full_translation = ''.join(translations)
        else:
            full_translation = self._translate_chunk(text)
        
        # Save to cache
        self._save_translation_to_cache(cache_key, full_translation)
        
        return full_translation
    
    def _translate_chunk(self, text: str) -> str:
        """Translate a chunk of text using the configured translator."""
        try:
            if self.translator_type == "google" and self.google_api_key:
                return self._google_translate(text)
            elif self.translator_type == "indicnlp":
                return self._indicnlp_translate(text)
            elif self.translator_type == "argos":
                return self._argos_translate(text)
            elif self.translator_type == "libretranslate":
                return self._libretranslate(text)
            elif self.translator_type == "gemini" and hasattr(self, 'gemini_service'):
                return self._gemini_translate(text)
            else:
                return self._fallback_translate(text)
        except Exception as e:
            logging.error(f"Translation error with {self.translator_type}: {str(e)}")
            # Try fallback if primary method fails
            return self._fallback_translate(text)
    
    def _google_translate(self, text: str) -> str:
        """Use Google Translate API."""
        url = "https://translation.googleapis.com/language/translate/v2"
        params = {
            "q": text,
            "target": "hi",
            "source": "en",
            "key": self.google_api_key
        }
        
        response = requests.post(url, params=params)
        if response.status_code == 200:
            result = response.json()
            return result["data"]["translations"][0]["translatedText"]
        else:
            logging.error(f"Google Translate API error: {response.text}")
            raise Exception(f"Translation failed with status {response.status_code}")
    
    def _indicnlp_translate(self, text: str) -> str:
        """Use IndianNLP for translation/transliteration."""
        # Note: This is a simplistic implementation and might need improvement
        # for actual translation rather than just transliteration
        return self.indic_transliterator.transliterate(text, "en", "hi")
    
    def _argos_translate(self, text: str) -> str:
        """Use Argos Translate (offline translation)."""
        return self.argos_translator.translate(text)
    
    def _libretranslate(self, text: str) -> str:
        """Use LibreTranslate API."""
        url = "https://libretranslate.com/translate"
        payload = {
            "q": text,
            "source": "en",
            "target": "hi",
            "format": "text"
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result["translatedText"]
        else:
            logging.error(f"LibreTranslate API error: {response.text}")
            raise Exception(f"Translation failed with status {response.status_code}")
    
    def _gemini_translate(self, text: str) -> str:
        """Use Gemini API for translation."""
        try:
            prompt = f"Translate the following English text to Hindi. Return ONLY the Hindi translation, no additional comments:\n\n{text}"
            response = self.gemini_service._call_api_with_retry(prompt)
            return response.strip()
        except Exception as e:
            logging.error(f"Gemini translation error: {str(e)}")
            raise e
    
    def _fallback_translate(self, text: str) -> str:
        """Fallback translator using MyMemory API with delay handling."""
        from translate import Translator
        try:
            # Use MyMemory but with better error handling
            translator = Translator(to_lang="hi")
            return translator.translate(text)
        except Exception as e:
            error_str = str(e)
            if "MYMEMORY WARNING" in error_str:
                logging.warning("MyMemory rate limit reached, using simplified backup")
                # Simple backup "translation" - just keep the original text
                # In a production app, you might want to display an error message instead
                return text
            else:
                logging.error(f"Fallback translation error: {error_str}")
                return text
    
    def configure_gemini_service(self, gemini_service):
        """Configure the Gemini service for translation."""
        self.gemini_service = gemini_service
        self.translator_type = "gemini"
        logging.info("Using Gemini for translation")
    
    def generate_audio(self, text: str, output_path: str) -> bool:
        """
        Generate speech from text and save it to the specified path.
        
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
        # Translate to Hindi
        hindi_text = self.translate_to_hindi(text)
        
        # Generate speech
        success = self.generate_audio(hindi_text, save_path)
        
        if success:
            return save_path, hindi_text
        else:
            return None, hindi_text