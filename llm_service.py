import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.0-flash" 

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
    You are an expert curriculum designer and educator. The learner wants to learn about: "{subject}".
    Current level: "{level if level else 'Beginner'}".
    Goal: "{goal if goal else 'General knowledge'}".
    User Background Context: "{user_context}"

    Please design a progressive learning curriculum strictly structured into four tiers, totaling exactly 17 topics:
    - Tier 1: Foundations (Topics 01-05) - Core concepts, no prerequisites, build the mental model.
    - Tier 2: Intermediate (Topics 06-09) - Practical application, patterns, real-world integration.
    - Tier 3: Advanced (Topics 10-11) - Complex patterns, optimization, architectural trade-offs.
    - Tier 4: Use Case Guides (Topics 12-17) - Scenario-based walkthroughs tied to real problems.

    Respond ONLY in valid JSON format. The JSON should be a list of objects with the following keys:
    - "id": a string from "01" to "17"
    - "title": concise topic name
    - "tier": the tier name (Foundations, Intermediate, Advanced, Use Case Guides)
    - "description": a brief 1-2 sentence description of what will be learned

    Do not use markdown blocks like ```json ... ```, just pure JSON output.
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        text_output = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text_output)
        return data
    except Exception as e:
        logger.error(f"Error generating curriculum: {str(e)}")
        # Provide real error back to UI for diagnostic clarity
        return generate_mock_curriculum(subject, str(e))


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
        behavior_instructions = "Open with a real-world scenario before explaining the theory. Keep it clear, concise, and focused on building a mental model."
    elif chunk_type == "example":
        behavior_instructions = "Provide a concrete, step-by-step worked example demonstrating the concept in action."
    elif chunk_type == "exercise":
        behavior_instructions = "Give the user a short task or code/logic exercise to practice what was just learned. Provide the solution distinctly at the end."
    elif chunk_type == "check":
        behavior_instructions = "Ask a single multiple-choice or short-answer comprehension question to activate retrieval practice."

    prompt = f"""
    You are an expert personalized tutor teaching the subject "{subject}".
    The current topic is: "{topic_title}".
    We are generating a specific type of educational chunk: [{chunk_type.upper()}].

    Instructions for this chunk:
    {behavior_instructions}

    User current context/background (adapt your explanation to these):
    {current_context}

    Please output the content in formatted Markdown. Make it engaging, visually structured, and easy to read.
    """

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating chunk: {e}")
        return f"<p>Error generating {chunk_type} for {topic_title}.</p>"


def re_explain_concept(concept_text, learner_feedback, user_context=""):
    api_key = get_api_key()
    if not api_key:
        return f"<p>Mock re-explanation for: {concept_text[:50]}...</p>"
    
    genai.configure(api_key=api_key)

    prompt = f"""
    You are an expert personalized tutor. The learner didn't quite understand the following concept:
    "{concept_text[:500]}..."

    The learner's specific feedback or state: "{learner_feedback}"
    User profile: "{user_context}"

    Please re-explain the core idea using a completely DIFFERENT framing, a new analogy, or a simpler worked example. 
    Output in formatted Markdown.
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
