from openai import OpenAI # type: ignore
from llama_cpp import Llama

def init_llm_models(config):
    openai_client = None
    local_model = None
    if 'OpenAI_api_key' in list(config):
        openai_client = OpenAI(api_key=config['OpenAI_api_key'])
    elif 'local_model' in list(config):
        model_path = config['local_model']
        try:
            local_model = Llama(model_path=model_path, embedding=True)
        except Exception as e:
            print(f"Error loading local model: {str(e)}")
    else:
        raise ValueError("No OpenAI API key found and no local model available. Please provide one of these to proceed.")
    return openai_client, local_model