import os
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# load .env file
load_dotenv()

class Settings(BaseSettings):
    # base config
    PROJECT_NAME: str = "SapiensAgent"
    VERSION: str = "0.1.0"
    ENV: str = "dev"

    # log config
    LOG_LEVEL: str

    # ComfyUI   
    COMFYUI_BASE_API_URL: str
    COMFYUI_WEBSOCKET_API_URL: str

    # Azure OpenAI
    AZURE_OPENAI_MODEL: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str
    
    # default batch task use one prompt
    DEFAULT_BATCHSIZE_USE_ONE_PROMPT: int

    # image to poster
    IMAGE2POSTER_BATCHSIZE_USE_ONE_PROMPT: int
    IMAGE2POSTER_OUTPUT_SIZE_WIDTH: int
    IMAGE2POSTER_OUTPUT_SIZE_HEIGHT: int
    IMAGE2POSTER_SCALE_MIN: float
    IMAGE2POSTER_SCALE_MAX: float

settings = Settings()
