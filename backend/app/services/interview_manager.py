from typing import List, Dict, Any
import json
from sqlalchemy.orm import Session
from .rag_engine import RAGEngine
from ..schemas import CandidateCreate


class InterviewManager:
    def __init__(self, rag_engine: RAGEngine, db: Session):
        self.rag_engine = rag_engine
        self.db = db

    async def generate_question(
        self,
        candidate: CandidateCreate,
        session,
        previous_qa: List[Dict[str, Any]],
        question_number: int,
        total_questions: int = 5,
    ) -> tuple[str, List[Dict[str, Any]]]:
        resume_context = (
            f"Candidate: {candidate.name}, "
            f"Skills: {candidate.skills}, "
            f"Experience: {candidate.experience_years} years, "
            f"Education: {candidate.education}"
        )

        # --- difficulty adaptation ---
        avg_score = 50.0
        scores = [qa["score"] for qa in previous_qa if "score" in qa]
        if scores:
            avg_score = sum(scores) / len(scores)

        if avg_score >= 80:
            difficulty = "hard"
        elif avg_score >= 50:
            difficulty = "medium"
        else:
            difficulty = "easy"

        # --- topic deduplication ---
        topics_covered = set()
        for qa in previous_qa:
            for chunk in qa.get("chunks", []):
                if isinstance(chunk, dict) and chunk.get("source"):
                    topics_covered.add(chunk["source"])

        query = f"{session.role}: {resume_context}. Generate a {difficulty}-level question."
        if topics_covered:
            query += f" Avoid these topics already covered: {', '.join(topics_covered)}."

        # --- RAG retrieval ---
        chunks = await self.rag_engine.retrieve(query, top_k=3)

        gen_prompt = (
            f"Generate a technical interview question for {session.role} role.\n"
            f"Candidate background: {resume_context}\n"
            f"Difficulty: {difficulty}\n"
            f"Question number: {question_number}/{total_questions}\n\n"
            f"Use the retrieved content below to create a context-aware question.\n"
            f"The question must reflect depth, relevance to the role, and awareness "
            f"of the candidate's background.\n\n"
            f"Retrieved content:\n{json.dumps(chunks, indent=2)}\n\n"
            f"Return ONLY the question text, nothing else."
        )
        question = await self.rag_engine.generate_answer(gen_prompt, chunks)
        return question, chunks

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        eval_prompt = (
            f"Evaluate this interview answer.\n\n"
            f"Question: {question}\n"
            f"Candidate Answer: {answer}\n\n"
            f"Reference context from knowledge base:\n"
        )
        # build reference context inline so the LLM has it
        if context_chunks:
            for i, c in enumerate(context_chunks):
                eval_prompt += f"[Chunk {i+1}] {c.get('text', '')}\n"
        else:
            eval_prompt += "No reference context available.\n"

        eval_prompt += (
            "\nProvide:\n"
            "1. Score (0-100) based on accuracy, depth, and relevance\n"
            "2. Constructive feedback\n"
            "3. Suggestions for improvement\n\n"
            'Return ONLY valid JSON: {"score": <number>, "feedback": "<text>", "suggestions": "<text>"}'
        )

        # pass empty context_chunks — the prompt itself contains everything
        result = await self.rag_engine.generate_answer(eval_prompt, [])
        try:
            parsed = json.loads(result)
            # normalize: ensure score is a float
            parsed["score"] = float(parsed.get("score", 50))
            return parsed
        except (json.JSONDecodeError, KeyError, TypeError):
            return {"score": 50.0, "feedback": result, "suggestions": ""}
