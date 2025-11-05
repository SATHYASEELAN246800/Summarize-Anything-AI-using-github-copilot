import yt_dlp
import os
from typing import Optional
import httpx
from fastapi import HTTPException

async def download_media(url: str) -> str:
    """
    Download media from various sources using yt-dlp
    Returns path to downloaded file
    """
    try:
        output_template = "downloads/%(id)s.%(ext)s"
        os.makedirs("downloads", exist_ok=True)

        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return os.path.join("downloads", f"{info['id']}.{info['ext']}")

    except Exception as e:
        raise HTTPException(400, f"Download failed: {str(e)}")

async def save_upload(file) -> str:
    """Save uploaded file and return path"""
    try:
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return file_path
    except Exception as e:
        raise HTTPException(400, f"Upload failed: {str(e)}")