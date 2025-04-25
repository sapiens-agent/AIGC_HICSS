from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ProcessResponse(BaseModel):
    """Response data format for process functions"""
    status: bool = Field(..., description="Process status, True for success, False for failure")
    message: str = Field(..., description="Process message") 
    data: Optional[List[Dict[str, Any]]] = Field(None, description="List of process result data")

