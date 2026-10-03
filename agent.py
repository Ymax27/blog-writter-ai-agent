# agent.py
import os
import sys
from pathlib import Path
import datetime

from dotenv import load_dotenv
from google.adk.agents import Agent, LoopAgent
from google.adk.tools import agent_tool

# --- env/config ---------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
MODEL = os.getenv("MODEL", "gemini-flash-latest")

# --- Sous-Agent: Plannificateur de blog ---------------------

blog_planner = Agent(
    name = "BlopPlanner",
    model = MODEL,
    description = "Creates a practical, skimmable outline in Markdown.",
    instruction = """
    You are a technical content strategist. Produce a clear Markdown outline with : 
        - Title
        - Short Intro
        - 4-6 main sections (each with 2-3 bullets)
        - Conclusion 
        
    If `codebase_context` exists in state, weave in specific sections/snippets.
    Return only the outline in Markdown.
    """,
    output_key = "blog_outline",
)

# --- Sous-Agent: Verificateur de validation du plan --------

class OutlineValidationChecker(Agent):
    def __init__(self):
        super().__init__(
            name = "OutlineValidationChecker",
            model = MODEL,
            description = "Validates that the outline is usable.",
            instruction = """
            Check the outline in state `blog_outline`. If it has a title, intro, 4-6 sections and a conclusion, respond exactly ok. 
            Otherwise respond exactly "retry" and list missing pieces.
            """,
            output_key = "validation_result",
        )

# --- Agent de bloucle: Connecter plannificateur et verificateur -   
robust_blog_planner = LoopAgent(
    name = "RobustBlogPlanner",
    description = "Retries planning if validation fails.",
    sub_agents = [blog_planner, OutlineValidationChecker()],
    max_iterations = 3,
)


# --- Sous-Agent: Redacteur de blog ----------------------------
blog_writer = Agent(
    name = "BlogWriter",
    model = MODEL,
    description = "Writes a technical blog post from the outline.",
    instruction = """
    Write a complete MarkDown article from the outline in `blog_outline`.
    
    Guidelines:
        - Audience : software Engineers; skip basics and focus on pratical insight.
        - Explain both de "how" and "why".
        - Include consise code snippets and helpfull.
        - Follow the outline's structure (H2/H3).
        - Output only the final article in Markdown (no fence around the whole post).
        """,
        output_key = "blog_post",
)

# --- Sous-Agent: Verificateur de validation de l'article ---------
class BlogPostValidationChecker(Agent):
    def __init__(self):
        super().__init__(
            name = "BlogPostValidationChecker",
            model = MODEL,
            description = "Validates the final post.",
            instruction = """
            Check `blog_post` for : intro, clear sections matching the outline, conclusion and technical clarity/
            If passes, respond "ok". Else respond "retry" with the specific fixes.
            """,
            output_key="validation_result",
        )
        
        
# --- Agent de bloucle: Connecter redacteur et verificateur ------   
robust_blog_writer = LoopAgent(
    name = "RobustBlogWriter",
    description = "Retries writing if validation fails.",
    sub_agents = [blog_writer, BlogPostValidationChecker()],
    max_iterations = 3,
)

# --- Sous-agent : Encapsuler chaque boucle ---------------------

planner_tool = agent_tool.AgentTool(agent=robust_blog_planner)
writer_tool = agent_tool.AgentTool(agent=robust_blog_writer)


# --- Agent principal : Rassemble le tous ----------------------
root_agent = Agent(
    name = "Blogger",
    model = MODEL,
    description = "Minimal multi-agent blogger that plans and writes.",
    instruction = f"""
    If the user give a topic : 
    1) Call the planner tool to generate the outline.
    2) Call the writer tool to generate de full draft.
    3) End with 3 alternate titles and 2 tweet-length hooks.
    
    If the trends tool fails or time out, continue with a sensible outline and draft anyway.
    
    Date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    tools = [
        planner_tool, 
        writer_tool,
    ],
)