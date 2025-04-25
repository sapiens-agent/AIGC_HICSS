import yaml
import json
import random
import time
import io
from PIL import Image
from typing import Dict, Any
import sys
from pathlib import Path

# Add project root directory to path if running this file directly
if __name__ == "__main__" or not __package__:
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[1]  # Go up one level to project root directory
    sys.path.insert(0, str(project_root))  # Use insert(0,...) to ensure project path has highest priority

try:
    from utils.position_generator import PositionGenerator
    from schemas.process_schema import ProcessResponse
    from utils.logger import logger
    from utils.setting import settings
    from services.base_service import ComfyuiTaskProcessor
except ModuleNotFoundError as e:
    print(f"Import error: {e}")
    print("Please ensure this file is run from the project root directory")
    sys.exit(1)


class Image2PosterProcessor(ComfyuiTaskProcessor):
    def __init__(self, task_type, model_client, model_name):
        super().__init__(task_type, model_client, model_name)
        self.output_size_width = settings.IMAGE2POSTER_OUTPUT_SIZE_WIDTH
        self.output_size_height = settings.IMAGE2POSTER_OUTPUT_SIZE_HEIGHT
        self.scale_min = settings.IMAGE2POSTER_SCALE_MIN
        self.scale_max = settings.IMAGE2POSTER_SCALE_MAX
        self.batchsize_use_one_prompt = settings.IMAGE2POSTER_BATCHSIZE_USE_ONE_PROMPT

        # 提示词工程
        prompts_template_path = 'templates/prompt_templates.yml'    # 用户提示词模板
        template_key = "image_generate_poster"     # prompt的模板key
        self.system_prompt = self.load_system_prompt(prompts_template_path, template_key)
        # 图片生成坐标 
        image2position_key = "product_image_position"
        image2position_prompt = self.load_template_prompt(prompts_template_path, image2position_key)
        self.image2position_system_prompt = image2position_prompt['system_prompt']  # 系统提示词
        self.image2position_user_template_prompt = image2position_prompt['user_prompt_template']    # 用户案例

        # 位置生成器
        self.position_generator = PositionGenerator(model_client=self.model_client, model_name=self.model_name)

        self.workflow_data = None
        with open('templates/comfyui_workflows/image2poster.json', 'r', encoding='utf-8') as file:
            self.workflow_data = json.load(file)

        # 定义工作流节点ID常量
        self.input_node_ids = {
            'input_image': '1',
            'text_prompt': '355',
            'noise_seed': '478',
            'x_position': '9',
            'y_position': '10',
            'scale': '11',
            'output_size': '584',
            'input_size': '3'
        }

        # 输出中间结果
        self.output_node_ids_show_middle_result = {
            '172': 'step1_image_url',  # 位置图片
            '551': 'step2_image_url',  # Flux生成背景图（含主体）
            '353': 'step3_image_url',  # 背景图去除主体
            '588': 'step4_image_url',  # 合成图
            '585': 'final_image_url'   # 最终生成图
        }
        # 直接输出最终结果
        self.output_node_ids = {
            '585': 'final_image_url'   # 最终生成图
        }

        # 将原workflow里面的 'SaveImage', 'PreviewImage' 改为 'SaveImageWebsocket'，目的是使用websocket的方式获取图片。
        self.change_workflow_output_to_websocket(self.workflow_data)

    def _set_workflow_params(self, workflow_data: dict, params: dict) -> None:
        """
        设置工作流参数

        Args:
            workflow_data: 工作流数据
            params: 参数字典，包含所有需要设置的参数
        Returns:
            result: 设置好参数的工作流数据
        """
        node_params = {
            self.input_node_ids['input_image']: {'image': params['input_image']},
            self.input_node_ids['text_prompt']: {'text': params['flux_prompt']},
            self.input_node_ids['noise_seed']: {'noise_seed': params['seed']},
            self.input_node_ids['x_position']: {'number': params['x_percent']},
            self.input_node_ids['y_position']: {'number': params['y_percent']},
            self.input_node_ids['scale']: {'number': params['scale']},
            self.input_node_ids['output_size']: {
                'width': params['width'],
                'height': params['height']
            },
            self.input_node_ids['input_size']: {
                'width': params['width'],
                'height': params['height']
            }
        }

        for node_id, inputs in node_params.items():
            workflow_data[node_id]['inputs'].update(inputs)

    async def process(self, task_id: str, data: Dict[str, Any]) -> ProcessResponse:
        try:
            # Parameter parsing
            image_path = data["image_path"]
            input_prompt = data["input_prompt"]
            batchsize = int(data.get("batchsize", 1))   # Determine if it is a batch task by checking if there is a batchsize
            show_middle_result = bool(data.get("show_middle_result", False))    # Whether to display intermediate results, default is not displayed
            prompt_optimizer = bool(data.get("prompt_optimizer", True))    # Whether to use prompt optimizer
            seed = int(data.get("seed", random.randint(1, 886185987922208)))
            height = int(data.get("height", self.output_size_height))
            width = int(data.get("width", self.output_size_width))
            output_path = data.get("output_path", "output")

        except Exception as e:
            logger.error(f"tasktype-{self.task_type} ERROR INFO: Missing required input parameters, ERROR INFO:{e}")
            return {"status": False, "message": f"Missing required input parameters, error_info: {e}", "data": None}

        if show_middle_result:  # Specify the node for output results, two modes: one shows intermediate results, one doesn't show intermediate results
            output_node_ids = self.output_node_ids_show_middle_result
        else:
            output_node_ids = self.output_node_ids

        # Download the image to comfyui
        try:
            input_image = await self.upload_local_image_to_comfyui(image_path)
            logger.info(f'input_image: {input_image}')
        except Exception as e: 
            logger.error(f"tasktype-{self.task_type} ERROR INFO: cannot upload image to comfyui, ERROR INFO:{e}")
            return {"status": False, "message": "process run failed. ", "data": None}

        grouptasks_list = self.group_task(batchsize=batchsize, group_size=self.batchsize_use_one_prompt)
        
        result_list = []

        for group_task in grouptasks_list:
            # Share the same prompt within the same group
            if prompt_optimizer:
                time_start = time.time()
                flux_prompt = await self.prompt_generator.generate_prompt(self.system_prompt, input_prompt)
            else:
                flux_prompt = input_prompt
            if "内容不符合内容审查的规范" in flux_prompt:
                logger.error(f"tasktype-{self.task_type} ERROR INFO: The content does not conform to the content review standard, input_prompt: {input_prompt}")
                return {"status": False, "message": flux_prompt, "data": None}
            if not flux_prompt: 
                logger.error(f"tasktype-{self.task_type} ERROR INFO: flux_prompt is None")
                return {"status": False, "message": "flux_prompt is None", "data": None}
            logger.info(f"tasktype-{self.task_type} flux_prompt: {flux_prompt}")
            # Input data
            try: 
                position_dict = self.position_generator.generator_position(
                    image_url=None, system_prompt=self.image2position_system_prompt, 
                    user_prompt=flux_prompt, user_template_prompt=self.image2position_user_template_prompt,
                    scale_min=self.scale_min, scale_max=self.scale_max)
                x_percent = position_dict['x_percent']
                y_percent = position_dict['y_percent']
                scale = position_dict["scale"]
            except Exception as e:
                logger.error(f"tasktype-{self.task_type} error when get position info. ERROR INFO:{e}")
                return {"status": False, "message": "process run failed. ", "data": None}

            for one_task_index in group_task:
                one_result_dict = {}
                # Prepare parameters
                params = {
                    'input_image': input_image,
                    'flux_prompt': flux_prompt,
                    'seed': seed,
                    'x_percent': x_percent,
                    'y_percent': y_percent,
                    'scale': scale,
                    'width': width,
                    'height': height
                } 
                # Set workflow parameters
                self._set_workflow_params(self.workflow_data, params)
                status, message, prompt_id = self.websocket_api.submit_task_to_comfyui(self.workflow_data)

                if status:
                    logger.info(f"tasktype-{self.task_type} task_id:{task_id} get prompt_id: {prompt_id}")
                    # Wait for the service to complete
                    image_data = self.websocket_api.get_images(prompt_id, output_node_ids.keys())

                    for key in image_data:
                        result_name = output_node_ids[key]
                        image = image_data[key][0]  # Image data
                        image_name = f"{task_id}-{result_name}_{one_task_index+1}.png"
                        save_path = f'{output_path}/{image_name}'
                        image = Image.open(io.BytesIO(image))
                        image.save(f"{save_path}")
                        one_result_dict[result_name] = save_path

                    result_list.append(one_result_dict)
                else:
                    logger.error(f"tasktype-{self.task_type} cannot get result from websocket_api, ERROR INFO:{message}")
                    return {# Return error message when program fails
                            "status": False,
                            "message": "process run failed. ",
                            "data": None}
        logger.info(f"tasktype-{self.task_type} task_id:{task_id} task done.")
        return {    # Return normal when program runs successfully
                "status": True,
                "message": "success",
                "data": result_list}



async def main():

    import uuid
    from models.azure_openai import azure_openai, azure_model
    model_client = azure_openai
    model_name = azure_model
    
    task_type = "image2poster"
    image2poster_processor = Image2PosterProcessor(task_type=task_type, model_client=model_client, model_name=model_name)
    
    task_id = str(uuid.uuid4())
    result = await image2poster_processor.process(task_id=task_id, data={"image_path": "images/example_images/1.jpg", 
                                         "input_prompt": 'A high-end advertising photo of a Perrier green glass bottle, standing elegantly on a wet reflective surface with sparkling water droplets. Fresh lemon slices and mint leaves are flying dynamically around the bottle. A soft, bright backlight emphasizes the transparent green color and cool texture. Water splashes subtly in the background, creating a lively and refreshing atmosphere. The “Perrier” label is clearly visible. Ultra-detailed, cinematic lighting, clean and vibrant color grading, hyper-realistic photography style.', 
                                         "batchsize": 1, 
                                         "show_middle_result": True, 
                                         "prompt_optimizer": True, 
                                         "seed": 123456, 
                                         "height": 1024, 
                                         "width": 1024, 
                                         "output_path": "images/outputs"})
    return result

if __name__ == "__main__":

    import asyncio

    result = asyncio.run(main())
    print(result)
