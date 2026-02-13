import os
import sys
from typing import List, Annotated, TypedDict, Literal
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from tools.carousel_renderer import generate_and_render_carousel# --- 1. CONFIG ---
load_dotenv()
sys.path.append(os.getcwd())

# --- 2. THE FINAL OUTPUT SCHEMA ---
class CarouselSlide(BaseModel):
    topic: str = Field(description="The main heading for the slide")
    content: str = Field(description="Body text for the slide")
    image_prompt: str = Field(description="AI image generation prompt for the background/visual")

class FinalStrategy(BaseModel):
    strategy_summary: str
    slides: List[CarouselSlide]

# --- 3. TOOLS ---
from langchain_core.tools import tool

@tool
def submit_final_strategy(strategy: FinalStrategy):
    """Call this ONLY when the user explicitly says 'Finalize' or 'Submit'."""
    # Here you could save to a JSON file
    import json
    with open("final_plan.json", "w") as f:
        json.dump(strategy.dict(), f, indent=4)
    return "SUCCESS: Strategy saved to final_plan.json"

# Placeholders for your specific logic (Import your real ones here)
@tool
def research_competitors(query: str):
    """Scouts competitors and trend analysis."""
    return f"Found 3 trending topics in {query}: RAG Optimizations, Agentic Workflows, and Local LLMs."

tools = [research_competitors, submit_final_strategy,generate_and_render_carousel]
tool_node = ToolNode(tools)

# --- 4. THE AGENT LOGIC ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def call_model(state: AgentState):
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)
    
    prompt = SystemMessage(content="""
    You are a Lead Marketing Strategist for Nueralogic which is an AI solutions company that designs and deploys custom automation, machine learning models, and intelligent systems to help businesses operate smarter and scale faster. 
    Your goal is to CO-CREATE a carousel with the user and help them with marketing strategies.
    
    1. Use tools to research trends/competitors when asked.
    2. Propose slide content (Topic, Content, Image Prompt).
    3. If the user suggests changes, update the content immediately.
    4. ONLY call `submit_final_strategy` when the user is 100% happy with the plan.
    5.Once the user says 'Generate' or 'Render', first ensure final_plan.json is updated, then only call `render_carousel_slides` with a unique batch name.
    6. In the final_plan.json mark the important keywords in the content with <b>keyword</b> tags. Don't use any other tags.
    """)
    
    response = llm.bind_tools(tools).invoke([prompt] + state["messages"])
    return {"messages": [response]}

def router(state: AgentState):
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return END

# --- 5. BUILD THE GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

# MemorySaver allows the "Chat" aspect to work via thread_id
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- 6. INTERACTIVE CHAT SIMULATION ---
def chat_with_agent(user_text, thread_id="123"):
    config = {"configurable": {"thread_id": thread_id}}
    input_message = HumanMessage(content=user_text)
    
    for event in app.stream({"messages": [input_message]}, config, stream_mode="values"):
        # Just print the last message from the agent
        last_msg = event["messages"][-1]
        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
            print(f"\n[Agent]: {last_msg.content}")
        elif isinstance(last_msg, ToolMessage):
            print(f"\n[Tool Result]: {last_msg.content}")

# --- TEST IT IN IPYNB ---
# 1. Start the conversation

# 2. Suggest a change (Simulating a second cell execution)
# chat_with_agent("Make slide 2 more technical and change the image prompt to a futuristic server room.")

# 3. Finalize
# chat_with_agent("This looks great, submit the final strategy now.")