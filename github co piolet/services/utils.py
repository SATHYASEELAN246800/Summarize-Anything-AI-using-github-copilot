import re
from typing import Optional
import httpx
from fastapi import HTTPException
import ffmpeg
from PIL import Image
import io
from fpdf import FPDF
import json

async def validate_url(url: str) -> bool:
    """Validate URL format and accessibility"""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise HTTPException(400, "Invalid URL format")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            return response.status_code < 400
    except Exception:
        raise HTTPException(400, "URL is not accessible")

async def extract_audio(video_path: str) -> str:
    """Extract audio from video file"""
    try:
        output_path = video_path.rsplit(".", 1)[0] + ".wav"
        
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, output_path, acodec='pcm_s16le', ac=1, ar='16k')
        ffmpeg.run(stream, overwrite_output=True)
        
        return output_path
    except Exception as e:
        raise Exception(f"Audio extraction failed: {str(e)}")

async def generate_thumbnail(video_path: str) -> bytes:
    """Generate thumbnail from video"""
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['streams'][0]['duration'])
        time = duration / 2  # Take thumbnail from middle of video
        
        out, _ = (
            ffmpeg
            .input(video_path, ss=time)
            .filter('scale', 480, -1)
            .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
            .run(capture_stdout=True)
        )
        
        return out
    except Exception as e:
        raise Exception(f"Thumbnail generation failed: {str(e)}")

def create_pdf_report(job_data: dict) -> bytes:
    """Generate PDF report from job results"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Add title
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Summary Report", ln=True, align="C")
        
        # Add timestamp
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f"Generated: {job_data['created_at']}", ln=True)
        
        # Add transcript
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Transcript:", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 10, job_data["result"]["transcript"])
        
        # Add summaries
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Summaries:", ln=True)
        
        for model, summary in job_data["result"]["summaries"]["models"].items():
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, f"Model: {model}", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 10, summary)
            pdf.ln()
        
        return pdf.output(dest='S').encode('latin-1')
        
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")