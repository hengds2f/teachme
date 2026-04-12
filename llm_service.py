import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-flash-latest" 

INSTRUCTIONAL_DESIGNER_PERSONA = r"""
You are an expert Instructional Designer, Subject-Matter Tutor, and Curriculum Architect for a high-end online learning portal. 
Your tone is professional, encouraging, and pedagogically sound. 
You specialize in "Mastery Learning": building deep understanding from zero knowledge to advanced application.

TEACHING PRINCIPLES:
1. Begin with intuition: Use plain language and analogies to explain the "Why".
2. Microlearning: Chunk information into small, digestible sections.
3. Worked Examples: Show fully solved examples before asking the learner to solve.
4. Retrieval Practice: Frequently ask questions to reinforce memory.
5. Scaffolded Difficulty: Progress from absolute beginner (Level 1) to university-level (Level 4) and expert (Level 5).
6. Immediate Feedback: Explain corrections and give hints before solutions.

FORMATTING PROTOCOLS:
- CONDITIONAL LANGUAGES: Only use non-English terms (e.g., Chinese) if the subject specifically involves language learning. If used, follow the format: Characters [Pinyin] - English (e.g., 学习 [xuéxí] - To study).
- CONDITIONAL MATHEMATICS: Use LaTeX ($...$ or $$...$$) ONLY for subjects involving Math, Science, Engineering, or formal logic. Do not force mathematical formulas into non-technical subjects like humanities or basic software tutorials unless relevant.
- CODING: Use fenced code blocks with language tags. Provide "runnable" logic and explain output.
- AESTHETICS: Use Markdown headings, tables, and lists to make content readable and "premium". Do not include irrelevant multi-lingual or mathematical columns unless pertinent to the topic.
"""

def get_api_key():
    raw_key = os.environ.get("GEMINI_API_KEY")
    if not raw_key or "your_gemini" in raw_key:
        return None
    return raw_key

# Define the strict schemas
CURRICULUM_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING", "description": "ID from 01 to 17"},
            "title": {"type": "STRING", "description": "Academic topic name"},
            "tier": {
                "type": "STRING", 
                "description": "Must be one of the specified tiers",
                "enum": ["Foundations", "Intermediate", "Advanced", "Use Case Guides"]
            },
            "description": {"type": "STRING", "description": "1-sentence academic overview"}
        },
        "required": ["id", "title", "tier", "description"]
    }
}

QUIZ_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "question": {"type": "STRING", "description": "Instructional choice question"},
            "options": {
                "type": "ARRAY", 
                "items": {"type": "STRING", "description": "Distractor or correct option"}
            },
            "answer_index": {"type": "INTEGER", "description": "Index (0-3) of the correct option"},
            "explanation": {"type": "STRING", "description": "Pedagogical explanation of why the answer is correct"}
        },
        "required": ["question", "options", "answer_index", "explanation"]
    }
}

def generate_curriculum(subject, level, goal, user_context=""):
    api_key = get_api_key()
    if not api_key:
        return generate_mock_curriculum(subject)
    
    genai.configure(api_key=api_key)
    model_obj = genai.GenerativeModel(MODEL_NAME)
        
    prompt = f"""
    {INSTRUCTIONAL_DESIGNER_PERSONA}

    Generate a 17-topic masterclass syllabus for: "{subject}".
    Current Level: {level}
    Goal: {goal}
    Context: {user_context}

    Tiered structure:
    - Tier 1: Foundations (01-05)
    - Tier 2: Intermediate (06-09)
    - Tier 3: Advanced (10-11)
    - Tier 4: Use Case Guides (12-17)

    Return a JSON array of 17 objects.
    """
    
    try:
        config = {
            "response_mime_type": "application/json",
            "response_schema": CURRICULUM_SCHEMA,
            "temperature": 0.2
        }
        response = model_obj.generate_content(prompt, generation_config=config)
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Curriculum generation failed: {e}")
        return generate_demo_curriculum(subject)

def generate_topic_chunk(subject, topic_title, chunk_type, current_context=""):
    api_key = get_api_key()
    if not api_key:
        return "### API Missing\nDemo content only."
    
    genai.configure(api_key=api_key)

    section_prompts = {
        "intro": "Generate Sections 1-5: Title, Learning Goals, Intro, Prerequisites, and Big Picture.",
        "level1": "Generate Level 1 (Absolute Beginner): Intuition and core concepts.",
        "level2": "Generate Level 2 (Beginner-Intermediate): Building structural knowledge.",
        "level3": "Generate Level 3 (Intermediate-Advanced): Rigorous theory.",
        "level4": "Generate Level 4 (University level): Deep analytical frameworks.",
        "level5": "Generate Level 5 (Mastery): Insight, edge cases, and research extension.",
        "examples": "Generate Section 7: Complex Worked Examples with step-by-step logic.",
        "practice_guided": "Generate Section 8: Guided Practice questions with hints in collapsible blocks.",
        "practice_independent": "Generate Section 9: Independent Practice (Advanced application).",
        "checkpoints": "Generate Section 10: Checkpoints (Active retrieval questions).",
        "mini_project": "Generate Section 11: Real-world Capstone/Case Study.",
        "mistakes": "Generate Section 13: Common Pitfalls & Debugging Tips.",
        "summary": "Generate Sections 14-15: Summary and Personalized Next Steps."
    }

    instruction = section_prompts.get(chunk_type, "Provide the next pedagogical section.")

    prompt = f"""
    {INSTRUCTIONAL_DESIGNER_PERSONA}
    
    Topic: {topic_title} (in {subject})
    Current Section: {chunk_type.upper()}
    Context: {current_context}

    REQUISITE: {instruction}
    
    Ensure depth, scaffolding, and premium Markdown formatting.
    """

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Pedagogical engine error: {str(e)}"

def generate_quiz_json(subject, topic_title, context):
    api_key = get_api_key()
    if not api_key: return "[]"
    
    genai.configure(api_key=api_key)
    model_obj = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
    {INSTRUCTIONAL_DESIGNER_PERSONA}
    
    Generate a 5-question mastery assessment for: {topic_title}.
    Ensure questions require synthesis and application.
    """

    try:
        response = model_obj.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": QUIZ_SCHEMA
            }
        )
        return response.text.strip()
    except Exception as e:
        return json.dumps({"error": str(e)})

def re_explain_concept(concept_text, learner_feedback, user_context=""):
    api_key = get_api_key()
    if not api_key: return "Explanation unavailable."
    
    genai.configure(api_key=api_key)
    prompt = f"""
    {INSTRUCTIONAL_DESIGNER_PERSONA}
    
    The learner is struggling with: "{concept_text}"
    Their feedback: "{learner_feedback}"
    Provide a supportive, clarifying re-explanation using a different analogy or simpler mental model.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def generate_session_summary(topics_info):
    api_key = get_api_key()
    if not api_key: return "Great job today!"
    genai.configure(api_key=api_key)
    prompt = f"As an Instructional Designer, summarize these achievements: {topics_info}"
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except:
        return "You made great progress!"

def generate_demo_curriculum(subject):
    return [{"id": "01", "title": f"Intro to {subject}", "tier": "Foundations", "description": "Orientation."}]

def generate_mock_curriculum(subject):
    return generate_demo_curriculum(subject)
