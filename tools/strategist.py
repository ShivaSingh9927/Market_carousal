
from langchain.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import os

@tool
def apply_marketing_framework(topic: str, framework: str) -> str:
    """
    Generates a strategic content piece based on a specific marketing framework.
    
    Args:
        topic (str): The specific topic or angle for the content (e.g., "AI in Healthcare").
        framework (str): The framework to apply. Options:
            - "PAS": Problem-Agitation-Solution (Good for Day 1/Problems)
            - "AIDA": Attention-Interest-Desire-Action (Good for Day 2/Launch)
            - "BAB": Before-After-Bridge (Good for Case Studies)
            - "FAB": Features-Advantages-Benefits (Good for Product Deep Dives)
            - "4Ps": Promise-Picture-Proof-Push (Good for Closing)
            
    Returns:
        str: A structured draft following the requested framework.
    """
    
    # Initialize a fast model for this specific task
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))
    
    system_prompt = f"""
    You are a Master Copywriter. 
    Your task is to write a short, punchy LinkedIn post structure using the '{framework}' framework.
    
    RULES:
    1. STRICTLY follow the {framework} structure.
    2. No fluff words ("Unleash", "Elevate", "Game-changer").
    3. Be technical and specific.
    """
    
    user_prompt = f"Topic: {topic}\n\nDraft the content now."
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return response.content
