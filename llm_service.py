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

    Please design a progressive, formal academic syllabus strictly structured into four tiers, totaling exactly 17 topics:
    - Tier 1: Foundations (Topics 01-05) - Core concepts, no prerequisites, build the mental model.
    - Tier 2: Intermediate (Topics 06-09) - Practical application, patterns, real-world integration.
    - Tier 3: Advanced (Topics 10-11) - Complex patterns, optimisation, architectural trade-offs.
    - Tier 4: Use Case Guides (Topics 12-17) - Scenario-based walkthroughs tied to real problems.

    Respond ONLY in valid JSON format. The JSON should be a list of objects with the following keys:
    - "id": a string from "01" to "17"
    - "title": technical academic topic name
    - "tier": the tier name (Foundations, Intermediate, Advanced, Use Case Guides)
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
        {"id": "01", "title": f"Axiomatic Foundations of {subject}", "tier": "Foundations", "description": "A comprehensive ontological deep-dive into the fundamental building blocks and theoretical mental models of the field."},
        {"id": "02", "title": "Epistemological Evolution", "tier": "Foundations", "description": "Analyzing the historical development and academic shift in paradigms over the last century."},
        {"id": "03", "title": "Core Theoretical Pillars", "tier": "Foundations", "description": "Establishing the fundamental axioms and structural frameworks required for specialized research."},
        {"id": "04", "title": "Conceptual Synthesis", "tier": "Foundations", "description": "Bridging initial knowledge with complex theoretical intersections and preliminary research methods."},
        {"id": "05", "title": "Prerequisite Review", "tier": "Foundations", "description": "Ensuring all foundational concepts are synthesized before transitioning to analytical methodologies."},
        
        {"id": "06", "title": "Methodological Frameworks", "tier": "Intermediate", "description": "Establishing the analytical tools and research environments necessary for formal study."},
        {"id": "07", "title": "Empirical Pattern Recognition", "tier": "Intermediate", "description": "Synthesizing professional standards with rigorous academic efficiency principles and real-world data patterns."},
        {"id": "08", "title": "Practical Application Models", "tier": "Intermediate", "description": "Implementing theoretical models in controlled research environments or simulated industrial scenarios."},
        {"id": "09", "title": "Systemic Integration", "tier": "Intermediate", "description": "Evaluating the integration of core modules within larger systemic or organizational structures."},
        
        {"id": "10", "title": "Advanced Theoretical Synthesis", "tier": "Advanced", "description": "Evaluating complex scaling patterns and high-level architectural trade-offs in modern research."},
        {"id": "11", "title": "Strategic Optimization Design", "tier": "Advanced", "description": "Refining complex frameworks for maximum efficiency while adhering to strict academic and technical constraints."},
        
        {"id": "12", "title": "Empirical Research Design A", "tier": "Use Case Guides", "description": "Constructing formal research scenarios tied to real-world industrial and academic problem-solving."},
        {"id": "13", "title": "Case Study Analysis: Resilience", "tier": "Use Case Guides", "description": "Analyzing historical data and failure points through a sophisticated academic lens to build resilient systems."},
        {"id": "14", "title": "Strategic Implementation Walkthrough", "tier": "Use Case Guides", "description": "A detailed, act-by-act pedagogical guide through a high-complexity real-world deployment scenario."},
        {"id": "15", "title": "Academic Review of Current Trends", "tier": "Use Case Guides", "description": "Synthesizing the latest research papers and empirical evidence into a forward-looking mastery guide."},
        {"id": "16", "title": "Heuristic Peer Review Scenario", "tier": "Use Case Guides", "description": "Critiquing advanced implementations through the dual-lens of academic rigor and industrial applicability."},
        {"id": "17", "title": "Capstone Synthesis Project", "tier": "Use Case Guides", "description": "A final synthesis encompassing all theoretical and empirical modules into one comprehensive academic demonstration."}
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
        MANDATORY: You MUST open the response with a section titled '## 🌍 Real-World Case Study'. 
        This section must present a specific, sophisticated scenario or industrial challenge that illustrates the concept's practical necessity.
        
        Follow this with:
        2. **Theoretical Framework & Axioms**: Deep theoretical explanation with technical rigor.
        3. **Critical Academic Analysis**: Limitations, debates, and trade-offs.
        
        Mandatory: Include in-text APA style citations and a 'References' section.
        """
    elif chunk_type == "example":
        behavior_instructions = """
        Provide a complex, high-level worked example or case study demonstrating the empirical application of the theory.
        Ensure technical depth and use formal academic terminology. 
        Include in-text APA citations.
        """
    elif chunk_type == "exercise":
        behavior_instructions = """
        Provide a demanding academic exercise that requires synthesis or critical analysis. 
        Mandatory: Format the solution at the end using the following collapsible HTML structure:
        <details>
          <summary>Click to reveal solution and academic explanation</summary>
          [Formal solution and technical reasoning here]
        </details>
        """
    elif chunk_type == "check":
        behavior_instructions = """
        Ask a high-level comprehension question targeting critical understanding.
        Use formal language and academic phrasing.
        """
    elif chunk_type == "takeaways":
        behavior_instructions = """
        Provide exactly 3-5 'Key Takeaways' that summarize the most critical technical and theoretical points of this entire topic. 
        Format as a bulleted academic summary.
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
