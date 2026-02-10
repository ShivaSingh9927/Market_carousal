import os
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchResults

# 1. Setup Environment and Memory
load_dotenv()
memory = MemorySaver()
config = {"configurable": {"thread_id": "scout_001"}}

# 2. Initialize Model (Llama 3.3 via Groq)
model = init_chat_model("llama-3.3-70b-versatile", model_provider="groq", max_tokens=4000)

# 3. Define the Search Tool
# We use DuckDuckGo to find latest competitor/product news
web_search_tool = DuckDuckGoSearchResults(output_format="list")
tools = [web_search_tool]

# 4. Create the React Agent (The Scout)
# This agent can now "Think" and then "Search" if it lacks info
agent_executor = create_react_agent(model, tools, checkpointer=memory)

# 5. Execute the Scout Query
# We ask it to find technical truths to avoid "rubbish" content
scout_query = """
Search for the latest technical capabilities of 'Claude Coworker' by Anthropic. 
Identify 3 specific things it can do with a local filesystem that a standard chatbot cannot.
Then, identify a 'Marketing Gap'—something it doesn't handle well (like privacy concerns or specific industries).
"""

print("🕵️‍♂️ Scout Agent is searching for technical truths...")
for event in agent_executor.stream(
    {"messages": [HumanMessage(content=scout_query)]}, config
):
    for value in event.values():
        # This will print the steps (Thought, Action, Observation)
        if "messages" in value:
            last_msg = value["messages"][-1]
            if hasattr(last_msg, 'content') and last_msg.content:
                print(f"\n--- Scout Progress ---\n{last_msg.content}")