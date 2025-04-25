import sys
from pathlib import Path
from openai import AzureOpenAI

# Add project root directory to path if running this file directly
if __name__ == "__main__" or not __package__:
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[1]  # Go up one level to project root directory
    sys.path.insert(0, str(project_root))  # Use insert(0,...) to ensure project path has highest priority

try:
    from utils.setting import settings
except ModuleNotFoundError as e:
    print(f"Import error: {e}")
    print("Please ensure this file is run from the project root directory")
    sys.exit(1)

# OpenAI API interface for generating prompts
api_key=settings.AZURE_OPENAI_API_KEY
api_version=settings.AZURE_OPENAI_API_VERSION
azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
azure_model = settings.AZURE_OPENAI_MODEL

azure_openai = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=azure_endpoint)


def main():

    # Test OpenAI API interface
    response = azure_openai.chat.completions.create(
        model=azure_model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of the China?"}
        ]
    )   
    print(response)


if __name__ == "__main__":
    main()
