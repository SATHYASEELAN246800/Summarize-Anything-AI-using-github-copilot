import pytest
from fastapi.testclient import TestClient
from main import app
import os
import json

client = TestClient(app)

def test_submit_job_url():
    response = client.post(
        "/api/v1/submit",
        json={
            "url": "https://www.youtube.com/watch?v=test",
            "type": "video"
        }
    )
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_submit_job_text():
    response = client.post(
        "/api/v1/submit",
        json={
            "text": "Test content for summarization",
            "type": "text"
        }
    )
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_get_job_status():
    # First create a job
    submit_response = client.post(
        "/api/v1/submit",
        json={
            "text": "Test content",
            "type": "text"
        }
    )
    job_id = submit_response.json()["job_id"]

    # Then check its status
    response = client.get(f"/api/v1/status/{job_id}")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "progress" in response.json()

def test_translate():
    response = client.post(
        "/api/v1/translate",
        json={
            "text": "Hello world",
            "target_lang": "ta"
        }
    )
    assert response.status_code == 200
    assert "translated_text" in response.json()