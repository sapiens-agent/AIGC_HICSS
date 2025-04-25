
class GeneratePrompt():
    def __init__(self, model_client, model_name, max_retry_time=5) -> None:
        self.max_retry_time = max_retry_time     # Maximum retry attempts (5) when the large language model returns an exception
        self.model_client = model_client
        self.model_name = model_name
        
    async def generate_prompt(self, system_prompt: str, input_prompt: str) -> str:
        raw_input_prompt = input_prompt
        for i in range(self.max_retry_time):
            prompt_message = await self._generate_prompt(system_prompt, input_prompt)
            status, message = self.validate_prompt_format(prompt_message)
            if status:
                return message
            if "The content you generated does not comply with content review standards, please use appropriate prompts" in message:
                return message
            if "Error validating prompt format" in message:   
                print(message)
                return None
            input_prompt = raw_input_prompt + ", " + message
            print(f"error_prompt is: {prompt_message}")
            print("Regenerating prompt...")
        print(f"Attempted more than the maximum number of times ({self.max_retry_time}), unable to obtain the corresponding prompt from openai.")
        return None

    async def _generate_prompt(self, system_prompt: str, input_prompt: str) -> str:
        """
        Use Azure OpenAI to convert the system prompt and user input prompt to English and generate a prompt for the ComfyUI model
        
        Args:
            system_prompt: System prompt, can be any language
            input_prompt: User input prompt, can be any language
            
        Returns:
            str: Optimized English prompt string
        """
        try:
            # Build prompt information
            messages = [
                {
                    "role": "system",   
                    "content": "You are a professional prompt engineer. Please translate and optimize the following prompts for ComfyUI models (like Flux). The output should be in English, well-structured, and effective for image generation. Only return prompt result directly. The format is str format."
                },
                {
                    "role": "user",
                    "content": f"System prompt: {system_prompt}\nUser input: {input_prompt}\nPlease combine these prompts, translate to English if needed, and optimize for best results with ComfyUI."
                }
            ]
            
            # Call Azure OpenAI API
            response = self.model_client.chat.completions.create(
                model=self.model_name,
                response_format={ "type": "text" },     # There are 3 types of return types: 'text' 'json_object' and 'json_schema'
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            
            # Get the optimized prompt
            optimized_prompt = response.choices[0].message.content.strip()
            
            # Ensure the prompt format is correct
            optimized_prompt = optimized_prompt.replace("\n", ", ")
            optimized_prompt = ", ".join(filter(None, [x.strip() for x in optimized_prompt.split(",")]))
            return optimized_prompt
        except Exception as e:
            # Check if it is a content review error
            error_str = str(response.choices[0])
            if "content_filter" in error_str:
                return "The content you generated does not comply with content review standards, please use appropriate prompts"
            print(f"Error generating prompt: {str(e)}")
            # If other API calls fail, return a simple combined prompt
            return f"{system_prompt}, {input_prompt}"

    @staticmethod
    def validate_prompt_format(prompt: str) -> tuple[bool, str]:
        """
        Validate the format of the generated prompt to ensure it meets the requirements
        
        Args:
            prompt: The prompt string to validate
            
        Returns:
            bool: Whether the format validation passes
            str: The information returned
        """
        try:
            # Check if the prompt contains braces or brackets
            if '{' in prompt or '}' in prompt or '[' in prompt or ']' in prompt or '`' in prompt:
                return False, "The prompt contains illegal characters {} or [] or `, please return a pure text str format prompt information"
            if "prompt" in prompt.lower():
                return False, "The prompt contains non-essential keywords 'prompt', please return a pure text prompt information directly, without any prompt keyword structure information"
            # Check if it contains specific keywords
            if "The content you generated does not comply with content review standards, please use appropriate prompts" in prompt:
                return False, "The content you generated does not comply with content review standards, please use appropriate prompts"
            # Check if the prompt contains Chinese characters
            if any('\u4e00' <= char <= '\u9fff' for char in prompt):
                return False, "The prompt contains Chinese characters"
                
            return True, prompt
            
        except Exception as e:
            return False, f"Error validating prompt format: {str(e)}"


async def main(system_prompt, input_prompt):
    import sys
    from pathlib import Path

    # If the file is run directly, add the project root directory to the path
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[1]  # The upper level is the project root directory
    sys.path.insert(0, str(project_root))  # Use insert(0,...) to ensure the project path has the highest priority

    from models.azure_openai import azure_openai, azure_model    

    generate_prompt = GeneratePrompt(model_client=azure_openai, model_name=azure_model)
    result = await generate_prompt.generate_prompt(system_prompt=system_prompt, input_prompt=input_prompt)
    return result


if __name__ == "__main__":

    # Unit test: Call the openai api interface to generate a prompt
    import asyncio

    system_prompt = "You are a professional prompt engineer. Please translate and optimize the following prompts for ComfyUI models (like Flux). The output should be in English, well-structured, and effective for image generation. Only return prompt result directly. The format is str format."
    input_prompt = "A beautiful girl"
    result = asyncio.run(main(system_prompt, input_prompt))
    print(result)