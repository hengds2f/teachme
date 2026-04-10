import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-flash-latest" 

def get_api_key():
    raw_key = os.environ.get("GEMINI_API_KEY")
    if not raw_key or "your_gemini" in raw_key:
        return None
    return raw_key

def generate_curriculum(subject, level, goal, user_context=""):
    """
    Generates a 17-topic structured curriculum organized into 4 tiers.
    """
    api_key = get_api_key()
    if not api_key:
        logger.warning(f"No valid Gemini API key found. Using mock data for: {subject}")
        return generate_mock_curriculum(subject)
    
    logger.info(f"Initiating live AI curriculum generation for: {subject}")
    genai.configure(api_key=api_key)
        
    prompt = f"""
    You are a Distinguished University Professor and Senior Academic Researcher tasked with designing a high-rigor academic curriculum. 
    The learner wants to master: "{subject}".
    Current level: "{level if level else 'University Freshman'}".
    Goal: "{goal if goal else 'Comprehensive Academic Mastery'}".
    User Background Context: "{user_context}"

    Please design a progressive, formal academic syllabus strictly structured into four undergraduate/graduate level tiers, totaling exactly 17 topics:
    - Tier 1: Theoretical Foundations (Topics 01-05) - Fundamental axioms, ontological frameworks, and core theoretical pillars.
    - Tier 2: Analytical Methodologies (Topics 06-09) - Schools of thought, research methods, and technical frameworks.
    - Tier 3: Advanced Synthesis (Topics 10-11) - Critical analysis, complex intersections, and dialectical review of the field.
    - Tier 4: Empirical Applications & Research (Topics 12-17) - Detailed case studies, research design, and real-world industrial or academic application.

    Respond ONLY in valid JSON format. The JSON should be a list of objects with the following keys:
    - "id": a string from "01" to "17"
    - "title": technical academic topic name
    - "tier": the tier name (Theoretical Foundations, Analytical Methodologies, Advanced Synthesis, Empirical Applications & Research)
    - "description": a highly detailed academic overview of the module context (at least 3-4 sentences), including the intended learning outcomes and theoretical intersections.

    Do not use markdown blocks like ```json ... ```, just pure JSON output. Ensure the tone is strictly formal and academic.
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        text_output = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text_output)
        return data
    except Exception as e:
        err_str = str(e)
        if "429" in err_str and "quota" in err_str.lower():
            logger.warning("Daily AI Quota reached. Switching to Pro Demo Mode.")
            return generate_demo_curriculum(subject)
        
        logger.error(f"Error generating curriculum: {err_str}")
        return generate_mock_curriculum(subject, err_str)

def generate_demo_curriculum(subject):
    """
    Returns a high-quality, structured curriculum for when the AI is on cooldown.
    """
    return [
        {"id": "01", "title": f"The Core Principles of {subject}", "tier": "Foundations", "description": "A comprehensive deep-dive into the fundamental building blocks and mental models."},
        {"id": "02", "title": "History and Evolution", "tier": "Foundations", "description": "Understanding how this field evolved and where it is heading next."},
        {"id": "03", "title": "Tools and Environment", "tier": "Foundations", "description": "Setting up your workspace and mastering the essential tools of the trade."},
        {"id": "04", "title": "Best Practices & Patterns", "tier": "Intermediate", "description": "Moving from basics to professional-grade standards and efficiency."},
        {"id": "05", "title": "Real-world Case Studies", "tier": "Intermediate", "description": "Analyzing successful implementations and learning from mistakes."},
        {"id": "06", "title": "Advanced Performance Optimization", "tier": "Advanced", "description": "Fine-tuning for scale, speed, and long-term sustainability."},
        {"id": "07", "title": "The Future of the Field", "tier": "Use Case Guides", "description": "Emerging trends and how to stay ahead of the curve."}
    ]


def generate_topic_chunk(subject, topic_title, chunk_type, current_context=""):
    """
    Generates a specific learning chunk (Concept, Example, Exercise, Check Question).
    Follows Knowles' need-to-know, Bloom's Taxonomy, and retrieval practice.
    """
    api_key = get_api_key()
    if not api_key:
        return f"<p>Mock content for {topic_title} - {chunk_type}</p>"
    
    genai.configure(api_key=api_key)

    # Ensure chunk type behavior
    behavior_instructions = ""
    if chunk_type == "concept":
        behavior_instructions = """
        Provide an academically rigorous and technically detailed explanation of the theoretical framework.
        Structure the response with the following sections in Markdown:
        1. **Theoretical Background**: Situate the concept within its historical and academic context.
        2. **Core Mechanics & Axioms**: Explain the underlying principles with specific technical detail.
        3. **Critical Analysis**: Discuss limitations, academic debates, or theoretical trade-offs.
        
        Mandatory: Include in-text APA style citations for any theoretical claims. 
        Add a 'References' section at the end if citations are made.
        """
    elif chunk_type == "example":
        behavior_instructions = """
        Provide a complex, high-level worked example or case study demonstrating the empirical application of the theory.
        Ensure technical depth and use formal academic terminology. 
        Include in-text APA citations for methodology or data sources referenced.
        """
    elif chunk_type == "exercise":
        behavior_instructions = """
        Provide a demanding academic exercise that requires synthesis or critical analysis of the concept. 
        Move beyond simple recall; ask for the evaluation of a hypothetical research scenario or complex logic problem.
        Provide the formal solution clearly at the end.
        """
    elif chunk_type == "check":
        behavior_instructions = """
        Ask a high-level comprehension question targeting critical understanding of the core theoretical mechanics.
        Use formal language and academic phrasing.
        """

    prompt = f"""
    You are a Distinguished University Professor and Senior Academic Researcher teaching the subject "{subject}".
    The current topic is: "{topic_title}".
    We are generating a specific type of educational module: [{chunk_type.upper()}].

    Instructions for this module:
    {behavior_instructions}

    User current context/background (integrate these into the formal academic explanation):
    {current_context}

    Please output the content in formal, academic Markdown. Prioritize depth, rigor, and technical accuracy over brevity. 
    Ensure all formatting is consistent with a university-level textbook or research paper.
    """

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        err_str = str(e)
        logger.error(f"Error generating topic chunk: {err_str}")
        
        # Friendly Fallback for Quota or other errors
        if "429" in err_str:
            return f"### Demo Content: {topic_title}\n\n*Note: The AI is currently at its daily limit. Enjoy this pre-designed learning material.* \n\n**Overview:** {topic_title} is a critical component of {subject}. In this section, we focus on the fundamental theories and practical implementations that define professional standards in this area."
        
        return f"Error: The learning engine hit a hitch ({err_str}). Please try again."


def re_explain_concept(concept_text, learner_feedback, user_context=""):
    api_key = get_api_key()
    if not api_key:
        return f"<p>Mock re-explanation for: {concept_text[:50]}...</p>"
    
    genai.configure(api_key=api_key)

    prompt = f"""
    You are a Distinguished University Professor. The learner requires a clarifying academic review of the following concept:
    "{concept_text[:500]}..."

    The learner's inquiry or specific cognitive dissonance: "{learner_feedback}"
    Academic context: "{user_context}"

    Please provide a sophisticated academic re-explanation. Use a different theoretical lens, a more detailed analogy, or a deeper analytical framework. 
    Maintain high technical rigor and formal tone in Markdown.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error re-explaining: {e}")
        return "<p>Error trying to re-explain.</p>"

def generate_session_summary(topics_covered_info):
    if not api_key:
        return "Session Summary: Great job studying!"

    prompt = f"""
    Based on the following topics and activities covered today:
    {topics_covered_info}

    Please generate an encouraging end-of-session report in Markdown.
    Show what was covered, what was completed, and recommend next steps.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "You made great progress today. Keep it up!"

def generate_mock_curriculum(subject, error_msg="No API key provided."):
    data = []
    tiers = ["Foundations"]*5 + ["Intermediate"]*4 + ["Advanced"]*2 + ["Use Case Guides"]*6
    for i, tier in enumerate(tiers):
        data.append({
            "id": f"{i+1:02d}",
            "title": f"Wait! (Error encountered)",
            "tier": tier,
            "description": f"The AI encountered an issue: {error_msg}. Please check logs or try again."
        })
    return data
