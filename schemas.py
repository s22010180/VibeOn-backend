from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

# --- REQUEST MODEL ---
# Defines what the mobile app is allowed to send to your server.
class JournalEntryRequest(BaseModel):
    # Field validation prevents "empty" or "too long" entries before they hit the AI
    content: str = Field(
        ..., 
        min_length=1, 
        max_length=10000, 
        description="The text content of the journal entry."
    )

# --- RESPONSE MODEL ---
# Defines the clean data "packet" that goes back to the mobile app.
class JournalEntryResponse(BaseModel):
    id: str
    created_at: datetime
    content: str
    mood_label: str
    sentiment_score: float
    supportive_tip: str

    # Pydantic V2 Configuration
    model_config = ConfigDict(from_attributes=True)