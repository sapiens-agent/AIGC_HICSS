import os 
import json 
import asyncio
from dotenv import load_dotenv
from openai import AzureOpenAI
from typing import Dict, Union, List
import sys
from pathlib import Path

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


class PositionGenerator():
    def __init__(self, model_client, model_name) -> None:
        self.model_client = model_client
        self.model_name = model_name
        
    @staticmethod
    def render_template(raw_str_data: str, vars: Dict) -> str:
        """Directly render template by replacing placeholders"""
        try:
            # Iterate through dictionary to replace placeholders
            for key, value in vars.items():
                placeholder = f"{{{{ {key} }}}}"  # Construct placeholder string
                raw_str_data = raw_str_data.replace(placeholder, str(value))
            
            # Check if any placeholders remain unreplaced
            if '{{' in raw_str_data or '}}' in raw_str_data:
                raise ValueError("Some placeholders were not replaced. Ensure all variables are passed.")
            
            return raw_str_data
        
        except KeyError as e:
            raise KeyError(f"Missing value for placeholder: {e}")
        except Exception as e:
            raise Exception(f"Error during template rendering: {e}")

    def _prepare_messages(self, system_prompt: str, user_prompt: str, image_urls: Union[None, str, List[str]] = None) -> List[dict]:
        """
        Prepare chat messages including system prompt, user prompt and image URLs.

        Args:
        - system_prompt: System prompt (str)
        - user_prompt: User prompt (str) 
        - image_urls: Optional image URLs (None, str, List[str])

        Returns:
        - List of messages (List[dict])
        """
        messages = [{"role": "system", "content": system_prompt}]
        user_message = {"role": "user", "content": user_prompt}

        if image_urls:
            user_message = {
                "role": "user",
                "content": {
                    "type": "text", 
                    "text": user_prompt
                }
            }
            image_contents = self._prepare_image_urls(image_urls)
            user_message["content"] = [user_message["content"], *image_contents]

        messages.append(user_message)
        return messages

    @staticmethod
    def _prepare_image_urls(image_urls: Union[str, List[str]]) -> List[dict]:
        """
        Convert image URLs to message format.

        Args:
        - image_urls: Image URLs, single string or list (Union[str, List[str]])

        Returns:
        - List of image message formats (List[dict])
        """
        if isinstance(image_urls, str):
            image_urls = [image_urls]
        return [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]

    def generator_position(self, image_url, system_prompt, user_prompt, user_template_prompt, scale_min, scale_max):

        data = {
            'flux_prompt': user_prompt,
            "scale_min": scale_min,
            "scale_max": scale_max
            }

        real_user_template_prompt = self.render_template(user_template_prompt,data)

        message = self._prepare_messages(system_prompt=system_prompt, user_prompt= real_user_template_prompt, image_urls=image_url)

        # Call Azure OpenAI API
        response = self.model_client.chat.completions.create(
            model=self.model_name,
            response_format={ "type": "json_object" },     # Response types: 'text', 'json_object' and 'json_schema'
            messages=message
            # temperature=0.7,
            # max_tokens=300
        )

        position_dict = response.choices[0].message.content.strip()
        position_dict = json.loads(position_dict)
        return position_dict


# Modify the final running part
async def main():

    # Image description prompt
    # image_url = "https://s3.cn-northwest-1.amazonaws.com.cn/kiwi-aigc-images/tmp/remove_bg_cropped/tmp_9mw0m4o-cropped.png"  # Replace with your image URL
    image_url = None

    system_prompt = """
    You are a professional graphic designer, skilled at determining the optimal position and size of product images in posters.  
    Based on the provided product image and the creative prompt, your task is to recommend the most effective position and size for the product image in the poster.  
    The position is expressed using `x_percent` and `y_percent` (integers from 0 to 100), representing the relative position of the image's center point on the canvas.  
    The size is expressed using `scale` (a decimal between 0.1 and 1.0), representing the scaling ratio of the product image relative to the poster canvas size.
"""

    user_template_prompt = """    Creative Prompt (Flux Prompt): {{ flux_prompt }}  
        I have uploaded the product image. Please analyze the uploaded product image along with the creative prompt and recommend the optimal position and size of the product image for the poster.

        Return the following details:

        1. **x_percent**: Integer between 0 and 100, indicating the relative horizontal position of the image center on the canvas.
        2. **y_percent**: Integer between 0 and 100, indicating the relative vertical position of the image center on the canvas.
        3. **scale**: Decimal between {{ scale_min }} and {{ scale_max }}, indicating the scaling of the product image relative to the canvas.  
        *Note*: Based on the prompt, the scaling ratio should ensure that the product image is neither too large nor too small, maintaining an effective balance without negatively impacting the poster's advertising effect.

        Please return the result in JSON format, for example:
        ```json
        {
            "x_percent": 0-100,
            "y_percent": 0-100,
            "scale": {{ scale_min }}-{{ scale_max }}
        }"""

    user_prompt = "Generate a poster for a plush pillow"
    scale_min = 0.3
    scale_max = 0.7

    from models.azure_openai import azure_openai, azure_model
    
    position_generator = PositionGenerator(model_client=azure_openai, model_name=azure_model)

    position_dict = position_generator.generator_position(image_url=image_url, system_prompt=system_prompt, user_prompt=user_prompt, 
                                       user_template_prompt=user_template_prompt, 
                                       scale_min=scale_min, scale_max=scale_max)

    print(position_dict)

# Use asyncio.run to run the main function
if __name__ == "__main__":
    asyncio.run(main())

