import traceback
import urllib.request
import urllib.parse
import tempfile
import sys
from pathlib import Path
import json
import uuid
import httpx
import websocket

# Add project root directory to path if running this file directly
if __name__ == "__main__" or not __package__:
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[1]  # Go up one level to project root directory
    sys.path.insert(0, str(project_root))  # Use insert(0,...) to ensure project path has highest priority

try:
    from utils.logger import logger
    from utils.setting import settings
except ModuleNotFoundError as e:
    print(f"Import error: {e}")
    print("Please ensure this file is run from the project root directory")
    sys.exit(1)

class WebsocketAPI:
    def __init__(self, comfyui_base_url = settings.COMFYUI_BASE_API_URL):

        # Parse comfyui_base_url, check if it has http or https prefix, if not, add http to it
        if not comfyui_base_url.startswith(('http://', 'https://')):
            comfyui_base_url = 'http://' + comfyui_base_url
        # Parse comfyui_base_url, replace http with ws, https with wss
        if comfyui_base_url.startswith('http://'):
            comfyui_websocket_api_url = comfyui_base_url.replace('http://', 'ws://') + "/ws"
        elif comfyui_base_url.startswith('https://'):
            comfyui_websocket_api_url = comfyui_base_url.replace('https://', 'wss://') + "/ws"

        self.client_id = str(uuid.uuid4())
        self.comfyui_base_api_url = comfyui_base_url
        self.comfyui_websocket_api_url = comfyui_websocket_api_url
        
        self.ws = websocket.WebSocket()
        self.ws_url = f"{self.comfyui_websocket_api_url}?clientId={self.client_id}"

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        url = f"{self.comfyui_base_api_url}/prompt"
        response = httpx.post(url, data=data)
        return response.json()
    
    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen("{}/view?{}".format(self.comfyui_base_api_url, url_values)) as response:
            return response.read()

    # Get history
    def get_history(self, prompt_id):
        with urllib.request.urlopen("{}/history/{}".format(self.comfyui_base_api_url, prompt_id)) as response:
            return json.loads(response.read())

    def get_queue_status(self):
        """Get current queue status"""
        url = f"{self.comfyui_base_api_url}/queue"
        response = httpx.get(url)
        return response.json()
    
    def submit_task_to_comfyui(self, prompt):
        """
        
        Normal response structure:
        ret= {  'prompt_id': '9c84a7e2-e46b-412d-bf46-525910746444', 
                'number': 10, 
                'node_errors': {}}

        Exception response structure:
            {'error': 
                {'type': 'prompt_outputs_failed_validation', 
                 'message': 'Prompt outputs failed validation', 
                 'details': '', 
                 'extra_info': {}
                 }, 
             'node_errors': 
                {'4': {
                        'errors': 
                            [{  'type': 'value_not_in_list', 
                                'message': 'Value not in list', 
                                'details': "ckpt_name: 'v1-5-pruned-emaonly.safetensors' not in ['Flux/flux1-dev-fp8-with_clip_vae.safetensors', 'epicrealism_naturalSinRC1VAE.safetensors', 'juggernautXL_v9Rdphoto2Lightning.safetensors', 'realisticVisionV51_v51VAE.safetensors']", 
                                'extra_info': 
                                    {   'input_name': 'ckpt_name', 
                                        'input_config':[
                                                            [   'Flux/flux1-dev-fp8-with_clip_vae.safetensors', 
                                                                'epicrealism_naturalSinRC1VAE.safetensors', 
                                                                'juggernautXL_v9Rdphoto2Lightning.safetensors', 
                                                                'realisticVisionV51_v51VAE.safetensors'], 
                                                        {'tooltip': 'The name of the checkpoint (model) to load.'}], 
                                        'received_value': 'v1-5-pruned-emaonly.safetensors'
                                    }
                             }], 
                        'dependent_outputs': ['final_image'], 
                        'class_type': 'CheckpointLoaderSimple'
                        }
                 }
            }
        
        """

        ret = self.queue_prompt(prompt)

        status = True
        ret_message = "success"
        prompt_id = None
        try:
            prompt_id = ret['prompt_id']
            # print("prompt_id= {}".format(prompt_id))
        except KeyError:
            # Handle the case of a returned exception
            if 'error' in ret:
                status = False
                ret_message = f"Error type: {ret['error']['type']}, Error message: {ret['error']['message']}"
                if 'node_errors' in ret:
                    for node_id, error in ret['node_errors'].items():
                        ret_message += f"\nNode {node_id} ({error['class_type']}) error: {error['errors'][0]['details']}"
                return status, ret_message, {}
            else:
                status = False 
                ret_message = "Unknown error"
                return status, ret_message, {}
        return status, ret_message, prompt_id

    def get_images(self, prompt_id, output_node_name):
        """
        Get image output
        
        Parameters:
            prompt: ComfyUI workflow JSON
            output_node_name: List of output node names
        Returns:
            output_images: Dictionary containing output image data, key is node name, value is list of image data
        """
        self.ws.connect(self.ws_url)
        output_images = {}
        current_node = ""
        while True:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data.get('prompt_id') == prompt_id:
                        logger.debug(f"get comfyui message: {message}")
                        if data['node'] is None:
                            break #Execution is done
                        else:
                            current_node = data['node']
            else:
                if current_node in output_node_name:
                    images_output = output_images.get(current_node, [])
                    images_output.append(out[8:])
                    output_images[current_node] = images_output
        self.ws.close()
        return output_images


if __name__ == "__main__":
    from PIL import Image
    import io

    server_address = "127.0.0.1:8188"    # ComfyUI local address
    websocket_api = WebsocketAPI(server_address)

    workflow_data = """
        {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 8,
                    "denoise": 1,
                    "latent_image": [
                        "5",
                        0
                    ],
                    "model": [
                        "4",
                        0
                    ],
                    "negative": [
                        "7",
                        0
                    ],
                    "positive": [
                        "6",
                        0
                    ],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": 8566257,
                    "steps": 20
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": 512,
                    "width": 512
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": [
                        "4",
                        1
                    ],
                    "text": "masterpiece best quality girl"
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": [
                        "4",
                        1
                    ],
                    "text": "bad hands"
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": [
                        "3",
                        0
                    ],
                    "vae": [
                        "4",
                        2
                    ]
                }
            },
            "final_image": {
                "class_type": "SaveImageWebsocket",
                "inputs": {
                    "images": [
                        "8",
                        0
                    ]
                }
            }
        }
        """
    
    workflow_data = json.loads(workflow_data) 
    #set the text prompt for our positive CLIPTextEncode
    workflow_data["6"]["inputs"]["text"] = "masterpiece best quality boy."

    #set the seed for our KSampler node
    import random
    seed = random.randint(1, 886185987922208)
    workflow_data["3"]["inputs"]["seed"] = seed
    
    output_node_ids = {
        "final_image": "final_image"
    }

    try:
        status, message, prompt_id = websocket_api.submit_task_to_comfyui(workflow_data)
        if status:

            # Wait for the service to complete
            image_data = websocket_api.get_images(prompt_id, output_node_ids.keys())

            for key in image_data:
                result_name = output_node_ids[key]
                image = image_data[key][0]  # Image data
                image_name = f"images/outputs/{result_name}.png"

                image = Image.open(io.BytesIO(image))
                image.save(f"{image_name}")
        else:
            print("return status: {}, message: {}".format(status, message))
    except Exception as e:
        traceback.print_exc()


