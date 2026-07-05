from typing import List, Dict, Any
import json
import re
from sqlalchemy.orm import Session
from .rag_engine import RAGEngine
from ..schemas import CandidateCreate


class InterviewManager:
    def __init__(self, rag_engine: RAGEngine, db: Session, base_difficulty: str = "Mid-Level", question_count: int = 5):
        self.rag_engine = rag_engine
        self.db = db
        self.base_difficulty = base_difficulty
        self.question_count = question_count

    async def generate_question(
        self,
        candidate: CandidateCreate,
        session,
        previous_qa: List[Dict[str, Any]],
        question_number: int,
    ) -> tuple[str, List[Dict[str, Any]]]:
        resume_context = (
            f"Candidate: {candidate.name}, "
            f"Skills: {candidate.skills}, "
            f"Experience: {candidate.experience_years} years, "
            f"Education: {candidate.education}"
        )

        query = f"Interview question for {session.role}, topic adapting to {resume_context}, difficulty {self.base_difficulty}"
        chunks = await self.rag_engine.retrieve(query)

        history_text = "No previous questions."
        if previous_qa:
            history_lines = []
            for i, qa in enumerate(previous_qa):
                history_lines.append(f"Q{i+1}: {qa.get('question', '')}")
                history_lines.append(f"Candidate's Answer: {qa.get('answer', '')}")
            history_text = "\n".join(history_lines)

        if chunks:
            context_section = (
                f"Use the retrieved content below to create a highly specific, context-aware question.\n"
                f"Retrieved content:\n{json.dumps(chunks, indent=2)}\n\n"
            )
        else:
            context_section = (
                f"No retrieved content available. Generate a question based on the candidate's profile and role requirements.\n"
                f"Candidate skills: {candidate.skills}\n"
                f"Candidate experience: {candidate.experience_years} years\n\n"
            )

        prompt = (
            f"You are conducting a fast-paced technical interview for the role of {session.role}.\n"
            f"Base Difficulty: {self.base_difficulty}\n"
            f"Question number: {question_number}/{self.question_count}\n\n"
            f"Interview History:\n{history_text}\n\n"
            f"{context_section}"
            f"CRITICAL GUARDRAIL: Do NOT ask generic trivia or definitions. The question MUST test the candidate's deep conceptual understanding, architectural intuition, or debugging strategy related to their skills.\n"
            f"CRITICAL GUARDRAIL: This is a conceptual interview, NOT a coding round. Do NOT ask the candidate to write code. Ask them to explain how they would solve a complex problem or design a system.\n"
            f"CRITICAL GUARDRAIL (BREVITY): You are in a live, fast-paced technical interview. Ask the question in ONE OR TWO short sentences. Do NOT write a whole page. Be extremely direct and test the candidate's skills.\n"
            f"CRITICAL GUARDRAIL (FLOW): Maintain a realistic conversational flow. Read the Interview History. You MUST either follow up on a gap/weak point in their previous answer, OR smoothly pivot to a related new topic. The interview must feel like a continuous dialogue, not a random quiz.\n\n"
            f"Return ONLY the next question text, nothing else."
        )
        question = await self.rag_engine.generate_answer(prompt, chunks)
        return question, chunks

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        eval_prompt = (
            f"You are a friendly, encouraging, and supportive senior engineering interviewer. You maintain a warm and constructive tone in your feedback, but you still demand technical precision in your grading.\n"
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
            "1. Score (0-100) based strictly on accuracy, depth, and relevance to the question.\n"
            "   - CRITICAL GUARDRAIL (SCORING): Use the FULL 0-100 scale dynamically. Do not default to 50 or 85. If it's perfect, give 100. If it's completely wrong, give 0.\n"
            "   - CRITICAL GUARDRAIL (STRICTNESS): You must be brutally strict. If the answer lacks deep technical detail, uses buzzwords without substance, dodges the question, or is even slightly vague, you MUST severely penalize the score (give below 40). Do NOT give the benefit of the doubt.\n"
            "2. Constructive feedback (CRITICAL: Format this as 2 to 3 very brief bullet points/pointers. Be extremely concise and direct. Stick ONLY to evaluating what was asked. No random talk, no fluff).\n"
            "3. Suggestions for improvement (Format as 1 to 2 short bullet points).\n\n"
            'Return ONLY valid JSON: {"score": <number>, "feedback": "<text>", "suggestions": "<text>"}'
        )

        # pass None to bypass RAG prefix, prompt contains everything
        result = await self.rag_engine.generate_answer(eval_prompt, None)
        try:
            clean_result = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.strip(), flags=re.IGNORECASE).strip()
            parsed = json.loads(clean_result)
            # normalize: ensure score is a float
            parsed["score"] = float(parsed.get("score", 50))
            return parsed
        except (json.JSONDecodeError, KeyError, TypeError):
            return {"score": 50.0, "feedback": result, "suggestions": ""}
