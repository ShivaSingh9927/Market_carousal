
from langchain.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import os

@tool
def analyze_market_gap(topic: str, search_results: str) -> str:
    """
    Analyzes raw search results to identify a 'Market Gap' or 'Blue Ocean' opportunity.
    Useful for finding what competitors are MISSING.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    Act as a category-creation marketing team analyzing the topic "{topic}".

    Your job is NOT to summarize trends.
    From the search results:

    - Identify repetitive themes (red ocean signals)
    - Identify underserved micro-segments
    - Identify contradictions between promise and reality
    - Identify latent emotional or operational pain etc.

    Search Data:
    {search_results}

    Return:

    Underserved Segment:
    <who exactly>

    Core Frustration:
    <what they struggle with that isn't solved>

    Positioning Opportunity:
    <one precise strategic angle, max 2 sentences>

    Avoid generic advice. Avoid buzzwords. Be specific.
    """

    
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content
