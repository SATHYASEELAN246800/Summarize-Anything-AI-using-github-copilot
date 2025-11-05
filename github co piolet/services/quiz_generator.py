from typing import List, Dict
import httpx
from transformers import pipeline

class QuizGenerator:
    def __init__(self, hf_api_key: str = None):
        self.hf_api_key = hf_api_key
        # Fallback model for local processing
        self.local_generator = pipeline(
            "text2text-generation",
            model="google/flan-t5-base",
            device="cpu"
        )

    async def generate_quiz(self, text: str, num_questions: int = 5) -> Dict:
        """Generate MCQ and True/False questions from text"""
        try:
            if self.hf_api_key:
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}
                prompt = f"""Generate {num_questions} multiple choice questions and 
                {num_questions} true/false questions from this text: {text}
                Format as JSON with 'mcq' and 'true_false' lists."""

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct",
                        headers=headers,
                        json={"inputs": prompt}
                    )

                if response.status_code == 200:
                    result = response.json()
                    return self._format_quiz(result[0]["generated_text"])

            # Fallback to local generation
            return await self._generate_quiz_locally(text, num_questions)

        except Exception as e:
            raise Exception(f"Quiz generation failed: {str(e)}")

    async def _generate_quiz_locally(self, text: str, num_questions: int) -> Dict:
        """Generate quiz using local model"""
        mcq_questions = []
        tf_questions = []

        # Generate MCQ
        for i in range(num_questions):
            prompt = f"Generate a multiple choice question from: {text}"
            response = self.local_generator(prompt, max_length=200)
            mcq_questions.append(self._parse_mcq(response[0]["generated_text"]))

        # Generate True/False
        for i in range(num_questions):
            prompt = f"Generate a true/false question from: {text}"
            response = self.local_generator(prompt, max_length=100)
            tf_questions.append(self._parse_tf(response[0]["generated_text"]))

        return {
            "mcq": mcq_questions,
            "true_false": tf_questions
        }

    def _parse_mcq(self, text: str) -> Dict:
        """Parse MCQ from generated text"""
        # Basic parsing logic - enhance based on actual output format
        lines = text.split("\n")
        return {
            "question": lines[0],
            "options": lines[1:5] if len(lines) >= 5 else [],
            "correct_answer": lines[5] if len(lines) > 5 else lines[1]
        }

    def _parse_tf(self, text: str) -> Dict:
        """Parse True/False question from generated text"""
        lines = text.split("\n")
        return {
            "question": lines[0],
            "correct_answer": "True" in lines[-1]
        }

    def _format_quiz(self, raw_json: str) -> Dict:
        """Format quiz data into structured format"""
        try:
            import json
            quiz_data = json.loads(raw_json)
            return {
                "mcq": quiz_data.get("mcq", []),
                "true_false": quiz_data.get("true_false", [])
            }
        except:
            return {
                "mcq": [],
                "true_false": []
            }