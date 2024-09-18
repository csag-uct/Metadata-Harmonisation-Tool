from openai import OpenAI # type: ignore

def init_llm_models(config):
    openai_client = None
    if 'OpenAI_api_key' in list(config):
        openai_client = OpenAI(api_key=config['OpenAI_api_key'])
    else:
        raise ValueError("No OpenAI API key found. Please provide an API key to proceed.")
    return openai_client