import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.tools import DuckDuckGoSearchResults
from dotenv import load_dotenv

# --- 1. STATE DEFINITION ---
class MarketingState(TypedDict):
    scout_report: str
    kb_context: str
    past_topics: List[str]
    proposed_calendar: str  
    user_approval: bool
    user_feedback: str  
    errors: List[str]

load_dotenv()

# --- 2. CONFIG & TOOLS ---
GROQ_KEY = os.getenv("GROQ_API_KEY")
# Using llama-3.3-70b is excellent for this task; it handles CSV structures well
llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=GROQ_KEY)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_rag_context(query: str):
    """Fetches specialized context from your 27-competitor index"""
    try:
        db = FAISS.load_local("/nuvodata/User_data/shiva/Market_carousal/faiss_index", 
                             embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(query, k=3)
        return "\n".join([d.page_content for d in docs])
    except Exception as e:
        print(f"⚠️ RAG Load Error: {e}")
        return "Nueralogic: Expert AI Agency focusing on Logistics and Healthcare workflows."

def web_scout(topic: str):
    """Gathers real-time market trends"""
    print(f"🌐 [Scout] Searching for {topic}...")
    try:
        search = DuckDuckGoSearchResults()
        return search.run(f"{topic} AI trends 2026")
    except Exception as e:
        print(f"⚠️ Search Timeout: {e}")
        return "Network restricted. Rely on Knowledge Base."

# --- 3. NODES ---

def scout_node(state: MarketingState):
    print("📍 Node: Scout starting...")
    feedback = state.get("user_feedback", "").lower()
    
    # Check if user specifically asked for competitor intel
    if "competitor" in feedback or "compare" in feedback:
        print("🕵️‍♂️ Force-Scouting Competitors based on feedback...")
        intel = web_scout("Nueralogic vs AI Competitors 2026")
        return {"scout_report": intel}

    # If refining other things (dates, topics), bypass search to speed up
    if feedback:
        return {"scout_report": state.get("scout_report", "Refining previous plan.")}
    
    # Default initial search
    intel = web_scout("Logistics and Healthcare AI Agentic Workflows")
    return {"scout_report": intel}

def strategist_node(state: MarketingState):
    print("📍 Node: Strategist starting...")
    kb_facts = get_rag_context("Nueralogic core services and case studies")
    
    # Use encoding='utf-8' to prevent issues with special characters in prompts
    prompt_path = "/nuvodata/User_data/shiva/Market_carousal/prompts/pro_strategist_v1.txt"
    try:
        with open(prompt_path, "r", encoding='utf-8') as f:
            pro_prompt = f.read()
    except FileNotFoundError:
        return {"errors": ["Prompt file missing"]}

    # Safe Formatting: Replaces placeholders with real data
    system_msg = pro_prompt.replace("{kb_context}", kb_facts)
    system_msg = system_msg.replace("{scout_report}", state.get("scout_report", ""))
    system_msg = system_msg.replace("{past_topics}", ", ".join(state.get("past_topics", [])))

    # Handle Feedback Logic
    feedback = state.get("user_feedback", "")
    user_instruction = "Generate the 5-day professional plan in CSV format."
    if feedback:
        user_instruction = f"REVISE the previous plan based on this feedback: {feedback}. Prioritize these changes while keeping the CSV structure identical."

    # Phase 1: Generation
    response = llm.invoke([
        SystemMessage(content=system_msg), 
        HumanMessage(content=user_instruction)
    ])
    
    # Phase 2: Critique (The 'Rubbish' Filter)
    # We explicitly tell it to preserve headers so the CSV parser doesn't break
    critic_prompt = (
        f"Review this plan. Remove any 'fluff' words like unleash/revolutionary. "
        f"Return ONLY the updated CSV data starting with 'Day,'. \n\nPlan:\n{response.content}"
    )
    final_response = llm.invoke([HumanMessage(content=critic_prompt)])
    
    # Cleaning Logic
    content = final_response.content.strip()
    # This is the "Magic Clip": it cuts off any conversational chatter before the actual CSV
    if "Day," in content:
        content = content[content.find("Day,"):]
    
    clean_csv = content.replace('```csv', '').replace('```', '').strip()
    
    print("✅ Strategy Finalized.")
    # Return the keys we want to update in the state
    return {
        "proposed_calendar": clean_csv, 
        "kb_context": kb_facts
    }

# --- 4. GRAPH CONSTRUCTION ---
workflow = StateGraph(MarketingState)

workflow.add_node("scout", scout_node)
workflow.add_node("strategist", strategist_node)

workflow.add_edge(START, "scout")
workflow.add_edge("scout", "strategist")
workflow.add_edge("strategist", END)

orchestrator = workflow.compile()