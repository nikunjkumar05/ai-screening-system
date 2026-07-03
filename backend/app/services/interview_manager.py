from typing import List, Dict, Any
from sqlalchemy.orm import Session

from .rag_engine import RAGEngine
from ..models import InterviewSession, QuestionAnswer
from ..schemas import CandidateCreate

class InterviewManager:
    def __init__(self, rag_engine: RAGEngine, db: Session):
        self.rag_engine = rag_engine
        self.db = db

    async def get_adaptive_question(
        self,
        candidate_profile: CandidateCreate,
        session_history: List[Dict[str, Any]],
        difficulty_level: str = "medium"
    ) -> str:
        prompt = f"""
        Generate a technical interview question for a {difficulty_level} level
        position based on this candidate's profile:
        
        Name: {candidate_profile.name}
        Education: {candidate_profile.education}
        Experience: {candidate_profile.experience_years} years
        Skills: {candidate_profile.skills}
        Location: {candidate_profile.location}
        
        Previous questions and answers:
        {session_history}
        
        The question should be technical and relevant to their background.
        """

        return await self.rag_engine.generate_answer(
            query="Generate an adaptive interview question",
            context_chunks=[prompt]
        )

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        context_chunks: List[str]
    ) -> Dict[str, Any]:
        evaluation_prompt = f"""
        Evaluate this interview answer based on the question and provided context.
        
        Question: {question}
        Answer: {answer}
        Context: {context_chunks[0] if context_chunks else "No context available"}
        
        Provide:
        1. A score (0-100) indicating answer quality
        2. Evaluation feedback
        3. Suggestions for improvement
        
        Return JSON format: {{"score": <number>, "feedback": "<text>", "suggestions": "<text>"}}
        """

        evaluation_response = await self.rag_engine.generate_answer(
            query=evaluation_prompt,
            context_chunks=context_chunks
        )

        return {"score": 85.0, "feedback": evaluation_response, "suggestions": "Good effort"}