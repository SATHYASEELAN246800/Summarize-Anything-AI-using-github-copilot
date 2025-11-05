from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./summarize_anything.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    status = Column(String)
    progress = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    options = Column(JSON)
    result = Column(JSON)
    error = Column(String, nullable=True)

class JobRepository:
    def __init__(self):
        self.db = SessionLocal()

    async def create_job(self, job_id: str, options: dict):
        job = Job(
            id=job_id,
            status="initializing",
            progress=0.0,
            options=options
        )
        self.db.add(job)
        await self.db.commit()
        return job

    async def update_job(self, job_id: str, updates: dict):
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            for key, value in updates.items():
                setattr(job, key, value)
            await self.db.commit()
        return job

    async def get_job(self, job_id: str):
        return self.db.query(Job).filter(Job.id == job_id).first()

    async def list_jobs(self, limit: int = 50, offset: int = 0):
        return self.db.query(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    def __del__(self):
        self.db.close()

# Create tables
Base.metadata.create_all(bind=engine)