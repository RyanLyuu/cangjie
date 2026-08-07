import openai
import requests
import tiktoken
from openai import OpenAI


class Model:
    def __init__(self, model_info):
        self.model_name = model_info['model_id']
        self.max_new_tokens = model_info['max_new_tokens']
        self.context_window = model_info['total']
        self.model_info = model_info
        self.total_tokens = 4096
        self.client = OpenAI(**{k: v for k, v in model_info.items() if k in ['api_key', 'base_url', 'default_headers']})


    def prompt_model(self, messages):
        print(f'Total tokens before generation: {self.total_tokens}', flush=True)
        max_new_tokens = self.context_window - self.total_tokens
        max_new_tokens = min(max_new_tokens, self.max_new_tokens)
        token_threshold = 7000
        generation = ''

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=0.0,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stream=True if self.total_tokens > token_threshold else False,
            )

            if self.total_tokens > token_threshold:
                for chunk in completion:
                    generation += chunk.choices[0].delta.content
            else:
                if isinstance(completion, str):
                    return False, f"API returned string instead of response: {completion}"
                generation = completion.choices[0].message.content

        except openai.BadRequestError as e:
            return False, e.message
        except openai.APITimeoutError as e:
            return False, e.message
        except openai.APIConnectionError as e:
            return False, e.message
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

        return True, generation

    def tokenize(self, messages):
        prompt = ''
        for message in messages:
            prompt += f"{message['role']}: {message['content']}\n"

        if self.model_name == 'gpt-4o-2024-11-20':
            encoding = tiktoken.encoding_for_model('gpt-4o')
            self.total_tokens = len(encoding.encode(prompt))
            return self.total_tokens

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        headers.update(self.model_info['default_headers'])

        data = {
            "model": self.model_name,
            "prompt": prompt,
            "add_special_tokens": True
        }

        response = requests.post(self.model_info['base_url'].replace('/v1', '/tokenize'), json=data, headers=headers)
        self.total_tokens = response.json()['count']
        return self.total_tokens

    def get_messages(self, interaction_history):
        messages = []
        for interaction in interaction_history:
            messages.append({
                'role': interaction.role,
                'content': interaction.content
            })

        return messages
