from typing import Dict
import httpx
from transformers import pipeline
import json

class Translator:
    def __init__(self, hf_api_key: str = None):
        self.hf_api_key = hf_api_key
        self.language_models = {
            "ta": "Helsinki-NLP/opus-mt-en-ta",  # English to Tamil
            "hi": "Helsinki-NLP/opus-mt-en-hi",  # English to Hindi
            "en": "Helsinki-NLP/opus-mt-mul-en"  # Multiple languages to English
        }
        
        # Initialize local fallback models
        self.local_translators = {}

    async def translate(self, text: str, target_lang: str) -> Dict:
        """Translate text to target language"""
        try:
            if self.hf_api_key:
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}
                model_id = self.language_models.get(target_lang)
                
                if not model_id:
                    raise ValueError(f"Unsupported target language: {target_lang}")

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://api-inference.huggingface.co/models/{model_id}",
                        headers=headers,
                        json={"inputs": text}
                    )

                if response.status_code == 200:
                    translation = response.json()[0]["translation_text"]
                    return {
                        "translated_text": translation,
                        "source_lang": "en",
                        "target_lang": target_lang
                    }

            # Fallback to local translation
            return await self._translate_locally(text, target_lang)

        except Exception as e:
            raise Exception(f"Translation failed: {str(e)}")

    async def _translate_locally(self, text: str, target_lang: str) -> Dict:
        """Translate using local models"""
        try:
            model_id = self.language_models.get(target_lang)
            
            if model_id not in self.local_translators:
                self.local_translators[model_id] = pipeline(
                    "translation",
                    model=model_id,
                    device="cpu"
                )

            result = self.local_translators[model_id](text)
            
            return {
                "translated_text": result[0]["translation_text"],
                "source_lang": "en",
                "target_lang": target_lang
            }

        except Exception as e:
            raise Exception(f"Local translation failed: {str(e)}")

    async def detect_language(self, text: str) -> str:
        """Detect the language of the input text"""
        try:
            if self.hf_api_key:
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api-inference.huggingface.co/models/papluca/xlm-roberta-base-language-detection",
                        headers=headers,
                        json={"inputs": text}
                    )

                if response.status_code == 200:
                    result = response.json()[0]
                    return result[0]["label"]

            # Fallback to basic detection
            return self._detect_language_locally(text)

        except Exception:
            return "en"  # Default to English on failure

    def _detect_language_locally(self, text: str) -> str:
        """Basic language detection using character analysis"""
        # Simple heuristic based on character sets
        devanagari = len([c for c in text if '\u0900' <= c <= '\u097F']) > 0
        tamil = len([c for c in text if '\u0B80' <= c <= '\u0BFF']) > 0
        
        if devanagari:
            return "hi"
        elif tamil:
            return "ta"
        return "en"