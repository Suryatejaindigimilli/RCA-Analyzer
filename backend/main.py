"""Main FastAPI application."""
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from core.chatbot import chatbot
from data.sample_repo_data import load_demo_repo

load_dotenv()

app = FastAPI(
    title="Codebase-Aware AI Chatbot",
    description="Chat with any GitHub/Bitbucket repository",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoadRepoRequest(BaseModel):
    repo_url: str


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def root():
    return {
        "name": "Codebase-Aware AI Chatbot",
        "version": "1.0.0",
        "status": "operational",
        "llm_provider": os.getenv('LLM_PROVIDER', 'mock')
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chatbot_loaded": chatbot.current_repo is not None
    }


@app.post("/api/load-repo")
async def load_repository(request: LoadRepoRequest):
    try:
        result = await chatbot.load_repository(request.repo_url)
        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['message'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load repo: {str(e)}")


@app.post("/api/demo")
async def demo_mode():
    try:
        chatbot.clear()
        demo_data = await load_demo_repo()

        if demo_data['status'] == 'error':
            raise HTTPException(status_code=500, detail=demo_data['message'])

        # Set chatbot state with REAL indexed data
        chatbot.current_repo = {'platform': 'github', 'owner': 'pallets', 'repo': 'click'}
        chatbot.repo_info = demo_data['repo_info']
        chatbot.indexed_files = demo_data['stats']['files_indexed']
        chatbot.total_chunks = demo_data['stats']['total_chunks']
        chatbot.languages = demo_data['stats']['languages']
        chatbot.chat_history = []

        return demo_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")



@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Empty message")
        result = chatbot.chat(request.message)
        result['timestamp'] = datetime.now().isoformat()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/api/status")
async def get_status():
    return chatbot.get_status()


@app.post("/api/clear")
async def clear_state():
    chatbot.clear()
    return {"status": "cleared"}


@app.get("/api/suggested-questions")
async def get_suggested_questions():
    return {
        "questions": [
            "What does this project do? Give me an overview.",
            "Explain the main architecture and design patterns.",
            "What are the key functions and classes?",
            "Show me how authentication is implemented.",
            "Find potential bugs or security issues.",
            "What are the main dependencies?",
            "How is the database structured?",
            "Explain the API endpoints.",
            "Show me how to set up and run this project.",
            "What testing frameworks are used?"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
