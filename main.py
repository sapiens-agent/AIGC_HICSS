import uuid
from models.azure_openai import azure_openai, azure_model
from services.image2poster import Image2PosterProcessor

def main(data: dict):
    image2poster_processor = Image2PosterProcessor(task_type="image2poster", model_client=azure_openai, model_name=azure_model)
    task_id = str(uuid.uuid4())
    result = image2poster_processor.process(task_id=task_id, data=data)
    return result

if __name__ == "__main__":
    import asyncio

    data={"image_path": "images/example_images/1.jpg", 
          "input_prompt": 'A high-end advertising photo of a Perrier green glass bottle, standing elegantly on a wet reflective surface with sparkling water droplets. Fresh lemon slices and mint leaves are flying dynamically around the bottle. A soft, bright backlight emphasizes the transparent green color and cool texture. Water splashes subtly in the background, creating a lively and refreshing atmosphere. The “Perrier” label is clearly visible. Ultra-detailed, cinematic lighting, clean and vibrant color grading, hyper-realistic photography style.', 
          "batchsize": 1, 
          "show_middle_result": True, 
          "prompt_optimizer": True, 
          "height": 1024, 
          "width": 1024, 
          "output_path": "images/outputs"}

    asyncio.run(main(data))