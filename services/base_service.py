import yaml
import json
import os
import httpx
from typing import Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import mimetypes

from schemas.process_schema import ProcessResponse
from utils.logger import logger
from utils.setting import settings
from utils.prompt_engineer import GeneratePrompt
from utils.websocket_api import WebsocketAPI

class BaseTaskProcessor(ABC):
    """ Task processor that supports asynchronous task execution """
    def __init__(self, task_type, model_client, model_name):
        """
        Initialize task processor
        Args:
            task_type: Type of task
            model_client: Model client
            model_name: Model name
        """
        # Store ongoing tasks
        self.task_type = task_type

        self.model_client = model_client
        self.model_name = model_name

        # Generate prompt
        self.prompt_generator = GeneratePrompt(self.model_client, self.model_name)

    @staticmethod
    def group_task(batchsize, group_size=5):
        "Split a batchsize into N groups, each group has group_size tasks sharing the same prompt"
        arr = [ i for i in range(batchsize)]
        return [arr[i:i + group_size] for i in range(0, len(arr), group_size)]

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> ProcessResponse:
        pass


class ComfyuiTaskProcessor(BaseTaskProcessor):
    def __init__(self, task_type, model_client, model_name):
        super().__init__(task_type, model_client, model_name)

        comfyui_base_api_url = settings.COMFYUI_BASE_API_URL        # ComfyUI address
        self.comfyui_upload_image_url = comfyui_base_api_url + "/api/upload/image"

        # Configure websocket service
        self.websocket_api = WebsocketAPI(comfyui_base_url=comfyui_base_api_url)

    @staticmethod 
    def load_template_prompt(prompt_template_path, template_key):
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as file:
                yaml_data = yaml.safe_load(file)
                system_prompt = yaml_data[template_key]
            return system_prompt
        except Exception as e:
            raise ValueError(f"Failed to load template: {str(e)}")

    @staticmethod
    def load_system_prompt(prompt_template_path, template_key):
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as file:
                yaml_data = yaml.safe_load(file)
                system_prompt = yaml_data[template_key]['system_prompt']
            return system_prompt
        except Exception as e:
            raise ValueError(f"Failed to load template: {str(e)}")
        
    @staticmethod
    def change_workflow_output_to_websocket(workflow_data: dict) -> dict:
        """Change SaveImage and PreviewImage nodes to SaveImageWebsocket in workflow
        Args:
            workflow_data: Workflow data dictionary
        Returns:
            dict: Modified workflow data
        """
        for node in workflow_data.values():
            if node.get('class_type') in ['SaveImage', 'PreviewImage']:
                node['class_type'] = 'SaveImageWebsocket'
        return workflow_data

    @staticmethod
    def get_content_type(image_path: str):
        content_type, _ = mimetypes.guess_type(image_path)
        if content_type is None:
            content_type = 'application/octet-stream'  # Use default if cannot be inferred
        return content_type

    async def upload_local_image_to_comfyui(self, image_path: str) -> str:
        """
        Upload local image to ComfyUI server
        
        Args:
            image_path: Local image path
            subfolder: Target subdirectory in ComfyUI input folder
        Returns:
            str: Image name after successful upload
            
        Raises:
            Exception: When upload fails or response parsing fails
        """
        subfolder = self.task_type
        try:
            # Prepare upload data
            image_name = Path(image_path).name
            new_image_name = f"{datetime.now():%Y%m%d%H%M%S}-{image_name}"
            content_type = self.get_content_type(image_path)
            
            upload_data = {
                'files': [('image', (new_image_name, open(image_path, 'rb'), content_type)),],
                'data': {'subfolder': subfolder},
                'headers': {'Accept': 'image/png,image/jpeg,image/jpg'},
                'url': self.comfyui_upload_image_url 
            }
            
            # Execute upload
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=upload_data['url'],
                    headers=upload_data['headers'],
                    files=upload_data['files'],
                    data=upload_data['data']  # Add data parameter here
                )
                
            # Handle response
            if response.status_code != 200:
                raise Exception(f'Image upload failed: {response.text}')
                
            response_data = response.json()
            if subfolder:
                return os.path.join(subfolder, response_data.get('name'))
            else:
                return response_data.get('name')
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse response JSON: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Error occurred while uploading image: {str(e)}")
            raise
        finally:
            # Ensure files are properly closed
            for _, file_tuple in upload_data['files']:
                file_tuple[1].close()

    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> ProcessResponse:
        pass