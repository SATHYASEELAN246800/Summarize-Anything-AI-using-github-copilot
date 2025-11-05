from faster_whisper import WhisperModel
import os
from typing import Dict, Optional
import httpx

# Initialize Whisper model (local fallback)
model_size = "base"
local_model = WhisperModel(model_size, device="cpu", compute_type="int8")

async def transcribe_audio(
    audio_path: str,
    use_hf_api: bool = True,
    hf_api_key: Optional[str] = None
) -> Dict:
    """
    Transcribe audio using Hugging Face Whisper API or local model
    """
    try:
        if use_hf_api and hf_api_key:
            # Try Hugging Face API first
            headers = {"Authorization": f"Bearer {hf_api_key}"}
            
            with open(audio_path, "rb") as f:
                files = {
                    "audio": (os.path.basename(audio_path), f, "audio/wav")
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api-inference.huggingface.co/models/openai/whisper-large-v3",
                        headers=headers,
                        files=files
                    )
                    
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "text": result.get("text", ""),
                        "segments": result.get("segments", []),
                        "language": result.get("language", "en")
                    }
        
        # Fallback to local model
        segments, info = local_model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Combine segments
        text = " ".join(segment.text for segment in segments)
        
        return {
            "text": text,
            "segments": [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                }
                for segment in segments
            ],
            "language": info.language
        }
        
    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")