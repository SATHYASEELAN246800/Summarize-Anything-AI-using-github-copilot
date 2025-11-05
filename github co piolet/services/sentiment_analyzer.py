from typing import Dict
import httpx
from transformers import pipeline
import numpy as np

class SentimentAnalyzer:
    def __init__(self, hf_api_key: str = None):
        self.hf_api_key = hf_api_key
        # Fallback model for local processing
        self.local_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device="cpu"
        )

    async def analyze_sentiment(self, text: str) -> Dict:
        """Analyze text sentiment and emotions"""
        try:
            if self.hf_api_key:
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api-inference.huggingface.co/models/SamLowe/roberta-base-go_emotions",
                        headers=headers,
                        json={"inputs": text}
                    )

                if response.status_code == 200:
                    emotions = response.json()[0]
                    return self._format_sentiment_analysis(emotions)

            # Fallback to local analysis
            return await self._analyze_locally(text)

        except Exception as e:
            raise Exception(f"Sentiment analysis failed: {str(e)}")

    async def _analyze_locally(self, text: str) -> Dict:
        """Perform sentiment analysis using local model"""
        result = self.local_analyzer(text)[0]
        
        return {
            "sentiment": result["label"],
            "confidence": round(float(result["score"]), 3),
            "emotions": {
                "positive": round(float(result["score"] if result["label"] == "POSITIVE" else 1 - result["score"]), 3),
                "negative": round(float(result["score"] if result["label"] == "NEGATIVE" else 1 - result["score"]), 3),
                "neutral": 0.0
            }
        }

    def _format_sentiment_analysis(self, emotions: Dict) -> Dict:
        """Format emotion analysis results"""
        # Group emotions into sentiment categories
        positive_emotions = ["joy", "gratitude", "optimism", "pride", "admiration", "love"]
        negative_emotions = ["anger", "disgust", "fear", "sadness", "disappointment", "grief"]
        neutral_emotions = ["neutral", "surprise", "curiosity", "realization"]

        # Calculate aggregate scores
        positive_score = sum(emotions.get(e, 0) for e in positive_emotions)
        negative_score = sum(emotions.get(e, 0) for e in negative_emotions)
        neutral_score = sum(emotions.get(e, 0) for e in neutral_emotions)

        # Determine overall sentiment
        sentiment_scores = {
            "POSITIVE": positive_score,
            "NEGATIVE": negative_score,
            "NEUTRAL": neutral_score
        }
        overall_sentiment = max(sentiment_scores.items(), key=lambda x: x[1])[0]

        return {
            "sentiment": overall_sentiment,
            "confidence": max(positive_score, negative_score, neutral_score),
            "emotions": {
                "positive": round(positive_score, 3),
                "negative": round(negative_score, 3),
                "neutral": round(neutral_score, 3)
            },
            "detailed_emotions": {k: round(v, 3) for k, v in emotions.items()}
        }