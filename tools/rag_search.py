
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.tools import tool
import os

# Initialize embeddings once to avoid reloading overhead if possible, 
# but for a tool, it might be re-initialized. 
# Better to lazy load or load at module level.
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
INDEX_PATH = "/nuvodata/User_data/shiva/Market_carousal/faiss_index"

@tool
def retrieve_internal_knowledge(query: str) -> str:
    """
    Searches the internal knowledge base (RAG) for company case studies, specific capabilities, and past success stories.
    Use this to ground the content in Nueralogic's actual achievements.
    """
    try:
        if not os.path.exists(INDEX_PATH):
            return "Error: FAISS index not found at configured path."
            
        db = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(query, k=3)
        
        if not docs:
            return "No relevant internal case studies found."
            
        return "\n\n".join([f"Case Study snippet: {d.page_content}" for d in docs])
        
    except Exception as e:
        return f"RAG Error: {str(e)}"
