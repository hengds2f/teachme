import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure the API key using the environment variable
raw_key = os.environ.get("GEMINI_API_KEY")

# Check if the key is missing or still the placeholder string
if not raw_key or "your_gemini" in raw_key:
    api_key = None
else:
    api_key = raw_key
    genai.configure(api_key=api_key)

# We use gemini-1.5-flash as it is fast and versatile. If you want, you can use gemini-1.5-pro for higher reasoning.
MODEL_NAME = "gemini-1.5-flash" 

def generate_curriculum(subject, level, goal, user_context=""):
    """
    Generates a 17-topic structured curriculum organized into 4 tiers.
    """
    if not api_key:
        # Mock for local dev without key
        return generate_mock_curriculum(subject)
        
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
        if len(data) != 17:
            # Re-pad or fix if not exactly 17, but usually LLM follows instructions.
            pass
        return data
    except Exception as e:
        print(f"Error generating curriculum: {e}")
        return generate_mock_curriculum(subject)


def generate_topic_chunk(subject, topic_title, chunk_type, current_context=""):
    """
    Generates a specific learning chunk (Concept, Example, Exercise, Check Question).
    Follows Knowles' need-to-know, Bloom's Taxonomy, and retrieval practice.
    """
    if not api_key:
        return f"<p>Mock content for {topic_title} - {chunk_type}</p>"

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
    if not api_key:
        return f"<p>Mock re-explanation for: {concept_text[:50]}...</p>"

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

def generate_mock_curriculum(subject):
    data = []
    tiers = ["Foundations"]*5 + ["Intermediate"]*4 + ["Advanced"]*2 + ["Use Case Guides"]*6
    for i, tier in enumerate(tiers):
        data.append({
            "id": f"{i+1:02d}",
            "title": f"Mock Topic {i+1} for {subject}",
            "tier": tier,
            "description": "This is a placeholder description since no API key was provided."
        })
    return data
