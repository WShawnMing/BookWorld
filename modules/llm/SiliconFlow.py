import requests
import os
from .BaseLLM import BaseLLM

class SiliconFlow(BaseLLM):

    def __init__(self, model="Qwen/Qwen2-7B-Instruct"):
        super(SiliconFlow, self).__init__()
        self.model_name = model
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.messages = []

    def initialize_message(self):
        self.messages = []

    def ai_message(self, payload):
        self.messages.append({"role": "assistant", "content": payload})

    def system_message(self, payload):
        # SiliconFlow API seems to handle system messages as the first user message
        # or within the user message, so we'll prepend it.
        # This is a common pattern for models that don't have a distinct system role.
        if self.messages and self.messages[0]["role"] == "user":
            self.messages[0]["content"] = f"System Prompt: {payload}\n\nUser: {self.messages[0]['content']}"
        else:
            # If no user message exists yet, we can't just add a system message.
            # We will handle it in the user_message method.
            # For now, we will just add it as a placeholder.
            self.messages.append({"role": "system", "content": payload})


    def user_message(self, payload):
        # Handle prepending system message if it exists
        system_prompt = ""
        if self.messages and self.messages[0]["role"] == "system":
            system_prompt = self.messages.pop(0)["content"] + "\n\n"

        self.messages.append({"role": "user", "content": system_prompt + payload})

    def get_response(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": self.messages
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()  # Raise an exception for bad status codes
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return f"Error: {e}"
        except (KeyError, IndexError) as e:
            print(f"Error parsing response: {response.text}")
            return f"Error parsing response: {e}"

    def chat(self, text):
        self.initialize_message()
        if isinstance(text, str):
            self.user_message(text)
            response = self.get_response()
        else:
            # Assuming `text` is a list of messages
            self.messages = text
            response = self.get_response()
            
        return response

    def print_prompt(self):
        for message in self.messages:
            print(message)

if __name__ == '__main__':
    # Make sure to set the SILICONFLOW_API_KEY environment variable
    # export SILICONFLOW_API_KEY='your_api_key'
    llm = SiliconFlow(model="Qwen/Qwen-32B-Chat")
    response = llm.chat("Say this is a test.")
    print(response)
