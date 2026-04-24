import os
import litellm

def generate(prompt: str, model: str = None) -> str:
    """
    Generates a response using the specified LLM.
    Can be configured to use Ollama by setting the model to 'ollama/llama2' (or similar)
    and setting the OLLAMA_API_BASE environment variable if needed.
    """
    if model is None:
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
