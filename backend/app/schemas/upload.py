from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UploadResponse(BaseModel):
    session_id: int
    filename: str
    status: str
    total_rows: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionDetail(UploadResponse):
    processed_rows: int = 0
