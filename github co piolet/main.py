from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
from datetime import datetime

from services.downloader import download_media
from services.transcriber import transcribe_audio
from services.summarizer import generate_summaries
from services.quiz_generator import QuizGenerator
from services.sentiment_analyzer import SentimentAnalyzer
from services.translator import Translator
from services.chapter_extractor import ChapterExtractor
from services.utils import (
    validate_url,
    extract_audio,
    generate_thumbnail,
    create_pdf_report
)

# Initialize services
quiz_generator = QuizGenerator(os.getenv("HF_API_KEY"))
sentiment_analyzer = SentimentAnalyzer(os.getenv("HF_API_KEY"))
translator = Translator(os.getenv("HF_API_KEY"))
chapter_extractor = ChapterExtractor()

app = FastAPI(
    title="Summarize Anything AI",
    description="Multi-modal summarization platform using Hugging Face models",
    version="1.0.0"
)

# Configure CORS and static files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Enhanced job processing
async def process_job(job_id: str, request_data: dict, file: Optional[UploadFile] = None):
    try:
        jobs[job_id]["status"] = "downloading"
        if request_data.get("url"):
            media_path = await download_media(request_data["url"])
        else:
            media_path = await save_upload(file)
        jobs[job_id]["progress"] = 0.2

        # Extract audio if needed
        jobs[job_id]["status"] = "extracting"
        if request_data["type"] == "video":
            audio_path = await extract_audio(media_path)
        else:
            audio_path = media_path
        jobs[job_id]["progress"] = 0.4

        # Transcribe
        jobs[job_id]["status"] = "transcribing"
        transcript_data = await transcribe_audio(audio_path)
        jobs[job_id]["progress"] = 0.6

        # Extract chapters
        chapters = await chapter_extractor.extract_chapters(
            transcript_data["text"],
            transcript_data["segments"]
        )

        # Generate summaries
        jobs[job_id]["status"] = "summarizing"
        summaries = await generate_summaries(
            transcript_data["text"],
            request_data.get("options", {}).get("models", ["facebook/bart-large-cnn"])
        )
        jobs[job_id]["progress"] = 0.7

        # Generate quiz
        quiz = await quiz_generator.generate_quiz(transcript_data["text"])
        jobs[job_id]["progress"] = 0.8

        # Analyze sentiment
        sentiment = await sentiment_analyzer.analyze_sentiment(transcript_data["text"])
        jobs[job_id]["progress"] = 0.9

        # Detect language and translate if needed
        source_lang = await translator.detect_language(transcript_data["text"])
        translations = {}
        
        if source_lang != "en":
            translations["en"] = await translator.translate(transcript_data["text"], "en")
        else:
            for lang in ["ta", "hi"]:
                translations[lang] = await translator.translate(transcript_data["text"], lang)

        # Store results
        jobs[job_id].update({
            "status": "completed",
            "progress": 1.0,
            "result": {
                "transcript": transcript_data["text"],
                "segments": transcript_data["segments"],
                "chapters": chapters,
                "summaries": summaries,
                "quiz": quiz,
                "sentiment": sentiment,
                "translations": translations,
                "language": source_lang
            }
        })

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        raise

# Update API endpoints to support new features
@app.get("/api/v1/result/{job_id}/quiz")
async def get_job_quiz(job_id: str):
    """Get quiz questions for a specific job"""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Job is not completed (status: {job['status']})")
    
    return job["result"]["quiz"]

@app.get("/api/v1/result/{job_id}/sentiment")
async def get_job_sentiment(job_id: str):
    """Get sentiment analysis for a specific job"""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Job is not completed (status: {job['status']})")
    
    return job["result"]["sentiment"]

@app.get("/api/v1/result/{job_id}/chapters")
async def get_job_chapters(job_id: str):
    """Get chapters for a specific job"""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Job is not completed (status: {job['status']})")
    
    return job["result"]["chapters"]

@app.post("/api/v1/translate")
async def translate_text(text: str, target_lang: str):
    """Translate text to target language"""
    try:
        result = await translator.translate(text, target_lang)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

# Add more endpoints as needed...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)