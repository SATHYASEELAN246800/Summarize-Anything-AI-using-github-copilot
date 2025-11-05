from typing import List, Dict
import re
from datetime import timedelta

class ChapterExtractor:
    def __init__(self):
        self.timestamp_pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2})|(\d{2}):(\d{2})')

    async def extract_chapters(self, transcript: str, segments: List[Dict]) -> List[Dict]:
        """Extract chapters from transcript with timestamps"""
        chapters = []
        current_chapter = {"title": "Introduction", "start": 0.0, "end": 0.0, "content": ""}
        
        for segment in segments:
            text = segment["text"]
            start_time = segment["start"]
            end_time = segment["end"]

            # Update current chapter end time
            current_chapter["end"] = end_time
            
            # Check for potential chapter markers
            if self._is_chapter_marker(text):
                # Save previous chapter
                if current_chapter["content"]:
                    chapters.append(current_chapter)
                
                # Start new chapter
                current_chapter = {
                    "title": self._extract_chapter_title(text),
                    "start": start_time,
                    "end": end_time,
                    "content": text
                }
            else:
                current_chapter["content"] += " " + text

        # Add final chapter
        if current_chapter["content"]:
            chapters.append(current_chapter)

        return self._format_chapters(chapters)

    def _is_chapter_marker(self, text: str) -> bool:
        """Detect if text segment is likely a chapter marker"""
        # Check for common chapter indicators
        chapter_indicators = [
            r"chapter \d+",
            r"section \d+",
            r"part \d+",
            r"topic \d*:?",
            r"\d+\.",
            r"introduction",
            r"conclusion"
        ]
        
        pattern = "|".join(chapter_indicators)
        return bool(re.search(pattern, text.lower()))

    def _extract_chapter_title(self, text: str) -> str:
        """Extract chapter title from text"""
        # Remove timestamps
        text = self.timestamp_pattern.sub("", text)
        
        # Extract first line or sentence
        lines = text.split("\n")
        sentences = text.split(". ")
        
        title = lines[0] if len(lines[0]) < 100 else sentences[0]
        return title.strip()

    def _format_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """Format chapters with proper timestamps and durations"""
        formatted_chapters = []
        
        for chapter in chapters:
            start_time = chapter["start"]
            end_time = chapter["end"]
            duration = end_time - start_time
            
            formatted_chapters.append({
                "title": chapter["title"],
                "start_time": str(timedelta(seconds=int(start_time))),
                "end_time": str(timedelta(seconds=int(end_time))),
                "duration": str(timedelta(seconds=int(duration))),
                "content": chapter["content"].strip(),
                "start_seconds": start_time,
                "end_seconds": end_time
            })
        
        return formatted_chapters