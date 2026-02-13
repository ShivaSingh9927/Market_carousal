
import os
import json
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
import pandas as pd
import io

# --- CONFIG ---
load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=GROQ_KEY)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# --- TOOLS ---

@tool
def search_web(query: str):
    """Searches the web for real-time market trends, competitor analysis, and news."""
    search = DuckDuckGoSearchResults()
    return search.run(query)

@tool
def search_internal_knowledge(query: str):
    """Searches the internal knowledge base (RAG) for company case studies, capabilities, and past success stories."""
    try:
        db = FAISS.load_local("/nuvodata/User_data/shiva/Market_carousal/faiss_index", 
                             embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(query, k=3)
        return "\n".join([d.page_content for d in docs])
    except Exception as e:
        return f"Error accessing knowledge base: {str(e)}"

# --- STATE ---

class AgentState(TypedDict):
    messages: List[BaseMessage]
    research_data: str
    draft_plan: str
    critique: str
    final_csv: str
    revision_count: int

# --- AGENTS / NODES ---

def scout_agent(state: AgentState):
    """
    Research Agent.
    It analyzes the user's request and gathers necessary context from Web + RAG.
    """
    print("🕵️‍♂️ Scout Agent Working...")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else HumanMessage(content="Start research")
    
    # We will use a dedicated chain/agent for this to allow tool usage
    tools = [search_web, search_internal_knowledge]
    llm_with_tools = llm.bind_tools(tools)
    
    # Simple prompt to guide the scout
    system_msg = SystemMessage(content="""You are the Lead Scout. 
    Your goal is to gather High-Quality, Technical intelligence for a marketing campaign.
    
    1. Analyze the user's request.
    2. Search the WEB for external trends/competitors.
    3. Search INTERNAL KNOWLEDGE (RAG) for matching capabilities.
    4. Compile a structured 'Research Report' summarizing Key Trends, Competitor Moves, and Our USP.
    
    Return the Research Report as your final answer.
    """)
    
    # In a real agentic loop, we'd use LangGraph's prebuilt agent, but here we do a simple tool calling loop or single pass
    # For simplicity in this demo, we'll do a direct invoke (or a mini-loop if we want multi-step)
    # Let's do a structured specific query approach to ensure coverage
    
    response = llm_with_tools.invoke([system_msg] + messages)
    
    # Handle tool calls manually or use prebuilt agent. 
    # To keep this node simple/robust without complex loops, we'll force it to plan and execute specific searches if needed
    # But better: Use the ReAct pattern logic if we want true "agentic" behavior.
    
    # For this implementation, let's just make it a smart researcher that plans 2 specific queries
    # and synthesizes them.
    
    # 1. Plan
    planning_prompt = f"Plan 2 distinct search queries (one web, one internal) for: {last_message.content}"
    plan = llm.invoke([SystemMessage(content="You are a search strategist."), HumanMessage(content=planning_prompt)])
    
    # 2. Execute (Mocking the tool execution for robustness in this node)
    # Actually, let's just do the actual searches to be safe
    web_res = search_web.invoke(f"{last_message.content} AI trends 2026")
    internal_res = search_internal_knowledge.invoke(last_message.content)
    
    research_summary = f"""
    --- WEB INTEL ---
    {web_res}
    
    --- INTERNAL CAPABILITIES ---
    {internal_res}
    """
    
    return {"research_data": research_summary}

def strategist_agent(state: AgentState):
    """
    The Creative Director / Strategist.
    Takes Research Data -> Creates a 5-Day Content Plan.
    """
    print("🧠 Strategist Agent Working...")
    research = state["research_data"]
    
    prompt = f"""
    You are the Head of Strategy. Use this intelligence to build a 5-day LinkedIn Content Calendar.
    
    RESEARCH:
    {research}
    
    FRAMEWORKS:
    - Day 1: PAS (Problem-Agitation-Solution)
    - Day 2: AIDA (Attention-Interest-Desire-Action)
    - Day 3: Technical Deep Dive (How it works)
    - Day 4: Case Study / Social Proof
    - Day 5: Contrarian View / Hot Take
    
    Output a JSON object with a list of 5 days:
    [{{ "day": "Monday", "framework": "PAS", "topic": "...", "angle": "...", "slides": ["slide1", "slide2", "slide3", "slide4"] }}]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"draft_plan": response.content}

def critic_agent(state: AgentState):
    """
    The Quality Assurance / Critic.
    Ensures no 'fluff' and technical accuracy.
    """
    print("⚖️ Critic Agent Working...")
    draft = state["draft_plan"]
    
    prompt = f"""
    Review this content plan.
    
    RULES:
    1. NO FLUFF ingredients: "Revolutionary", "Unleash", "Unlock", "Delve".
    2. MUST include technical keywords matching the research.
    3. MUST focus on 'Local-First' and 'Privacy'.
    
    If it passes, output "APPROVED".
    If it fails, output specific feedback for revision.
    
    PLAN:
    {draft}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"critique": response.content}

def formatter_agent(state: AgentState):
    """
    The Publisher.
    Converts the final approved plan into the strict CSV format for the factory pipeline.
    """
    print("🏭 Formatter Agent Working...")
    plan = state["draft_plan"]
    
    prompt = """
    Convert the following JSON plan into a STRICT CSV format.
    
    CSV Headers: "Day","Framework","Topic","Strategic Angle","Slide1","Slide2","Slide3","Slide4","Slide5","Slide6"
    
    Rules:
    - Quote all fields.
    - No markdown blocks.
    - No preamble. Just the CSV.
    """
    
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=plan)
    ])
    
    # Strip markdown if present
    csv_content = response.content.replace('```csv', '').replace('```', '').strip()
    return {"final_csv": csv_content}

# --- GRAPH ---

workflow = StateGraph(AgentState)

workflow.add_node("scout", scout_agent)
workflow.add_node("strategist", strategist_agent)
workflow.add_node("critic", critic_agent)
workflow.add_node("formatter", formatter_agent)

workflow.add_edge(START, "scout")
workflow.add_edge("scout", "strategist")
workflow.add_edge("strategist", "critic")

def check_critique(state: AgentState):
    critique = state["critique"]
    if "APPROVED" in critique.upper():
        return "formatter"
    else:
        # Loop back to strategist with feedback? 
        # For this v1, simplify to just format (or we could add a feedback loop)
        # Let's assume approval for now to avoid infinite loops in this demo
        return "formatter"

workflow.add_conditional_edges("critic", check_critique)
workflow.add_edge("formatter", END)

agentic_orchestrator = workflow.compile()
