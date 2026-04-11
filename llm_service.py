import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-flash-latest" 

PROFESSOR_PERSONA = r"""
You are a Distinguished University Professor and Senior Academic Researcher. Your tone is formal, rigorous, and highly technical. 
Use complex academic terminology. Address the user as a fellow scholar.

FORMATTING PROTOCOLS (Apply ONLY if relevant to the subject or requested):
1. CHINESE TRANSLATION: If (and only if) you are teaching Chinese or providing specific Chinese terminology relevant to the task, use the triple format: Chinese Characters [Pinyin] - English Translation.
   Example: "The concept of five hundred is expressed as 五百 [wǔbǎi] - Five Hundred."
   
2. MATHEMATICAL NOTATION: If (and only if) the topic requires mathematical expression, use LaTeX:
   - Use $ ... $ for inline math.
   - Use $$ ... $$ for block math on its own line.
   Example: The Schrödinger equation is $ i\hbar \frac{\partial}{\partial t} \Psi(\mathbf{r},t) = \hat{H} \Psi(\mathbf{r},t) $.

IMPORTANT: DO NOT insert Chinese phrases or mathematical formulas unless they are directly relevant to the core subject matter being taught.
"""

def get_api_key():
    raw_key = os.environ.get("GEMINI_API_KEY")
    if not raw_key or "your_gemini" in raw_key:
        return None
    return raw_key

# Define the strict schema for curriculum generation
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
            "question": {"type": "STRING", "description": "Sophisticated MCQ question"},
            "options": {
                "type": "ARRAY", 
                "items": {"type": "STRING", "description": "Distractor or correct option"}
            },
            "answer_index": {"type": "INTEGER", "description": "Index (0-3) of the correct option"},
            "explanation": {"type": "STRING", "description": "Academic explanation of why the answer is correct"}
        },
        "required": ["question", "options", "answer_index", "explanation"]
    }
}

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
    # Initialize model once to reuse context and reduce latency
    model_obj = genai.GenerativeModel(MODEL_NAME)
        
    prompt = f"""
    {PROFESSOR_PERSONA}

    The learner wants to master: "{subject}".
    Current level: "{level if level else 'University Freshman'}".
    Goal: "{goal if goal else 'Comprehensive Academic Mastery'}".
    User Background Context: "{user_context}"

    Please design a progressive, formal academic syllabus strictly structured into four tiers, totaling exactly 17 topics:
    - Tier 1: Foundations (Topics 01-05)
    - Tier 2: Intermediate (Topics 06-09)
    - Tier 3: Advanced (Topics 10-11)
    - Tier 4: Use Case Guides (Topics 12-17)

    Return a list of 17 objects. Each description must be exactly 1 academic sentence.
    CRITICAL: Only use Chinese or Math formatting if the subject "{subject}" specifically requires it.
    """
    
    # Combined Safety Settings to prevent truncation on academic topics
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]

    # Robust Curriculum Generation Helper
    def _attempt_generation(p, model, schema=None, temp=0.0):
        config = {
            "response_mime_type": "application/json",
            "temperature": temp,
            "max_output_tokens": 4096
        }
        if schema:
            config["response_schema"] = schema

        response = model.generate_content(
            p,
            generation_config=config,
            safety_settings=safety_settings
        )
        
        t_out = response.text.strip()
        
        # Robust Bracket Search Recovery
        data = None
        try:
            data = json.loads(t_out)
        except json.JSONDecodeError:
            start = t_out.find('[')
            end = t_out.rfind(']')
            if start != -1 and end != -1:
                try:
                    data = json.loads(t_out[start:end+1])
                except:
                    raise
            else:
                raise

        # DATA NORMALIZATION LAYER (Especially for Attempt 3 - Schema-less)
        if isinstance(data, list):
            for i, topic in enumerate(data):
                if not isinstance(topic, dict): continue
                
                # Normalize 'id'
                if 'id' not in topic:
                    topic['id'] = str(topic.get('ID') or topic.get('topic_id') or topic.get('no') or str(i+1).zfill(2))
                
                # Normalize 'tier' (Strictly mapped to dashboard sections)
                if 'tier' not in topic:
                    raw_tier = str(topic.get('section') or topic.get('Section') or topic.get('level') or 'Foundations')
                    # Smart mapping to allowed enums
                    if 'found' in raw_tier.lower(): topic['tier'] = 'Foundations'
                    elif 'inter' in raw_tier.lower(): topic['tier'] = 'Intermediate'
                    elif 'adv' in raw_tier.lower(): topic['tier'] = 'Advanced'
                    elif 'use' in raw_tier.lower() or 'guide' in raw_tier.lower(): topic['tier'] = 'Use Case Guides'
                    else: topic['tier'] = 'Foundations'
                
                # Ensure 'title' and 'description' exist
                if 'title' not in topic: topic['title'] = topic.get('name') or topic.get('Topic') or f"Topic {topic['id']}"
                if 'description' not in topic: topic['description'] = topic.get('overview') or topic.get('summary') or f"Academic overview of {topic['title']}."
                
        return data

    try:
        # ATTEMPT 1: Strict Schema + Deterministic (Accuracy)
        return _attempt_generation(prompt, model_obj, CURRICULUM_SCHEMA, temp=0.0)
    except Exception as e:
        logger.warning(f"Attempt 1 failed for {subject}: {e}. Trying Relaxed Schema...")
        try:
            # ATTEMPT 2: Strict Schema + More Creativity (Fluidity)
            return _attempt_generation(prompt, model_obj, CURRICULUM_SCHEMA, temp=0.5)
        except Exception as e2:
            logger.warning(f"Attempt 2 failed for {subject}: {e2}. Final Fallback: Schema-less Generation...")
            try:
                # ATTEMPT 3: NO SCHEMA.
                p_fallback = prompt + "\n\nCRITICAL: Return ONLY a raw JSON array. Do not use conversational text."
                return _attempt_generation(p_fallback, model_obj, schema=None, temp=0.7)
            except Exception as e3:
                err_str = str(e3)
                if "429" in err_str and "quota" in err_str.lower():
                    logger.warning("Daily AI Quota reached. Switching to Pro Demo Mode.")
                    return generate_demo_curriculum(subject)
                
                logger.error(f"Triple-Stage failure for {subject}: {err_str}")
                return generate_mock_curriculum(subject, f"Final fallback error: {err_str}")

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
        ACTIVATE RETRIEVAL PRACTICE: Ask a sophisticated, technical comprehension question based strictly on the axioms and frameworks covered in the preceding 1-2 modules.
        The goal is immediate active recall. Use formal academic phrasing.
        """
    elif chunk_type == "takeaways":
        behavior_instructions = """
        Provide exactly 3-5 'Key Takeaways' that summarize the most critical technical and theoretical points of this entire topic. 
        Format as a bulleted academic summary.
        """
    elif chunk_type == "quiz":
        # Handled by a specialized generator for JSON output
        return generate_quiz_json(subject, topic_title, current_context)

    prompt = f"""
    {PROFESSOR_PERSONA}
    
    You are teaching the subject "{subject}".
    The current topic is: "{topic_title}".
    We are generating a specific type of educational module: [{chunk_type.upper()}].

    Instructions for this module:
    {behavior_instructions}

    User current context/background (integrate these into the formal academic explanation):
    {current_context}

    Please output the content in formal, academic Markdown. Prioritize depth, rigor, and technical accuracy over brevity. 
    Ensure all formatting is consistent with a university-level textbook or research paper.
    RESTRAINT: Do NOT include Chinese translations or math formulas unless they are essential to explaining "{topic_title}".
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


def generate_quiz_json(subject, topic_title, context):
    """
    Generates a 5-question multiple choice quiz in structured JSON.
    """
    api_key = get_api_key()
    if not api_key:
        return json.dumps([{"question": "Mock Question?", "options": ["A", "B", "C", "D"], "answer_index": 0, "explanation": "Mock."}] * 5)
    
    genai.configure(api_key=api_key)
    model_obj = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
    {PROFESSOR_PERSONA}
    
    Subject: {subject}
    Topic: {topic_title}
    Learner Context: {context}

    Generate a 5-question Multiple Choice Quiz (MCQ) to assess deep theoretical and practical understanding of this specific topic.
    Questions must be challenging, academic, and require synthesis of the concepts taught.
    For each question, provide 4 distinct options, the index of the correct answer, and a rigorous academic explanation.
    
    CRITICAL: Return ONLY a raw JSON array of 5 objects. Do not wrap it in a root object or include conversational text.
    """

    try:
        response = model_obj.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": QUIZ_SCHEMA,
                "temperature": 0.5
            }
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        # Return a structured error that the frontend can parse and display
        return json.dumps({"error": f"The academic engine encountered a service interruption: {str(e)}"})


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
