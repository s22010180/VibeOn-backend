import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <-- For solving your CORS error
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv
from schemas import JournalEntryRequest, JournalEntryResponse

# 1. Setup Environment and Logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MindJournal")

# 2. Initialize API Clients
# Make sure your .env has GEMINI_API_KEY, SUPABASE_URL, and SUPABASE_KEY
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Logic to run when server starts
    logger.info("Server is starting up...")
    yield
    # Shutdown: Logic to run when server stops
    logger.info("Server is shutting down...")

app = FastAPI(title="Mind Journal API - Sprint 1", lifespan=lifespan)

# 3. FIX: CORS Middleware 
# This allows your Expo app to talk to this Python server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your phone/emulator to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def analyze_with_ai(text: str):
    """
    Sends the journal text to Gemini 2.5 Flash-Lite and returns structured JSON.
    """
    prompt = f"Analyze this journal entry for mood and provide a short supportive tip: {text}"
    
    # 2026 Standard: Enforce JSON response using a schema
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "mood": {"type": "STRING"},
            "score": {"type": "NUMBER"},
            "tip": {"type": "STRING"}
        },
        "required": ["mood", "score", "tip"]
    }

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash-lite", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )
        )
        return response.parsed
    except Exception as e:
        logger.error(f"AI Analysis Error: {e}")
        # Fallback if AI is down or quota hit
        return {"mood": "Neutral", "score": 0.5, "tip": "I'm listening. Tell me more about your day."}

# 4. API Endpoints

@app.post("/add-entry", response_model=JournalEntryResponse)
async def add_entry(request: JournalEntryRequest):
    """
    Endpoint to receive text, get AI analysis, and save to Supabase.
    """
    # Step A: Get AI Analysis
    ai_data = await analyze_with_ai(request.content)
    
    # Step B: Insert into Supabase 'entries' table
    try:
        response = supabase.table("entries").insert({
            "content": request.content,
            "mood_label": ai_data["mood"],
            "sentiment_score": ai_data["score"],
            "supportive_tip": ai_data["tip"]
        }).execute()
        
        # Supabase return format: data[1] contains the list of inserted records
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Supabase Insert Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save entry to database.")

@app.get("/history")
async def get_history():
    """
    Fetch all entries from Supabase to show in the app later (Sprint 2).
    """
    try:
        response = supabase.table("entries").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Supabase Fetch Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history.")

@app.get("/")
def read_root():
    return {"status": "Mind Journal API is Online"}