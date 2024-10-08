import pandas as pd
import math
import fsspec
import time
from pdfminer.high_level import extract_text
import re
from scipy import spatial
from dotenv import dotenv_values
from .util import init_llm_models

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def get_index(list_in, n, by):
    """
    Get the indices of the top 3 minimum or maximum values in a list.

    Args:
        list_in (list): The list of values.
        n (int): The number of indices to get.
        by (str): 'min' to get indices of the smallest values, 'max' for the largest.

    Returns:
        list: Indices of the top 3 minimum or maximum values.
    """
    indexed_values = list(enumerate(list_in)) # create tuple with og index
    sorted_values = sorted(indexed_values, key=lambda x: x[1]) # sort tuples by values (2nd values in tuple)
    if by == 'min':
        return [index for index, _ in sorted_values[:n]] # return index
    elif by == 'max':
        return [index for index, _ in sorted_values[-n:]]

def return_prompt(init_prompt, variable, context='Not available', example_dict=None):
    """
    Create a prompt for the LLM based on the initial prompt, variable, context, and examples.

    Args:
        init_prompt (str): The initial prompt to be used.
        variable (str): The variable name.
        context (str, optional): The context for the variable. Defaults to 'Not available'.
        example_dict (dict, optional): Dictionary of example contexts and descriptions. Defaults to None.

    Returns:
        list: A list of messages forming the prompt.
    """
    prompts = [{"role": "system", "content": f"""{init_prompt}"""},
                {"role": "user", "content": f"variable name:  Patient ID, context: 'Not available'"}, 
                {"role": "assistant", "content": "Patient Identifier (?)"},
                {"role": "user", "content": f"variable name:  matdiag, context: 'Not available'"}, 
                {"role": "assistant", "content": "maternal diagnosis (?)"}]
    if example_dict:
        for example in example_dict:
            example_context = example_dict[example][0]
            example_description = example_dict[example][1]
            prompts.append({"role": "user", "content": f"variable name:  {example}, context: {example_context}"})
            prompts.append({"role": "assistant", "content": f"{example_description}"})
    prompts.append({"role": "user", "content": f"variable name:  {variable}, context: {context}"})
    return prompts

def convert_pdf_to_txt():
    """
    Convert PDF files to text files for all available studies.
    """
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    avail_studies = [study for study in avail_studies if fs.exists(f"{input_path}/{study}/context.pdf")]
    for study in avail_studies:
        # create plain text
        if not fs.exists(f"{input_path}/{study}/context.txt"):
            output_file = f"{input_path}/{study}/context.txt"
            text = extract_text(f"{input_path}/{study}/context.pdf")
            with fs.open(output_file, 'w') as of:
                of.write(text)

def get_embedding(openai_client, text, model="text-embedding-ada-002"):
    """
    Get the embedding for a given text using OpenAI's API.

    Args:
        openai_client (object): The OpenAI client.
        text (str): The text to be embedded.
        model (str, optional): The model to be used for embedding. Defaults to "text-embedding-ada-002".

    Returns:
        list: The embedding vector for the text.
    """
    text = str(text).replace("\n", " ")
    if openai_client:
        try:
            response = openai_client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating OpenAI embedding: {str(e)}")
    else:
        raise ValueError("No OpenAI client available. Please provide an OpenAI API key.")
    return None

def split_text_recursively(text, chunk_size=1000, chunk_overlap=20, separators=None, is_separator_regex=False):
    """
    Split text by recursively looking at characters. Sourced from Langchain. Included directly to avoid adding extra dependencies. https://api.python.langchain.com/en/latest/_modules/langchain_text_splitters/character.html#RecursiveCharacterTextSplitter

    Args:
        text (str): The text to be split.
        chunk_size (int, optional): The maximum size of each chunk. Defaults to 1000.
        chunk_overlap (int, optional): The number of characters to overlap between chunks. Defaults to 20.
        separators (list, optional): List of separators to use for splitting. Defaults to ["\n\n", "\n", " ", ""].
        is_separator_regex (bool, optional): Whether the separators are regex patterns. Defaults to False.

    Returns:
        list: A list of text chunks.
    """
    if separators is None:
        separators = ["\n\n", "\n", " ", ""]

    def _split_text(text, separators):
        final_chunks = []
        separator = separators[-1]
        new_separators = []
        for i, _s in enumerate(separators):
            _separator = _s if is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1:]
                break

        _separator = separator if is_separator_regex else re.escape(separator)
        splits = re.split(_separator, text)

        _good_splits = []
        for s in splits:
            if len(s) < chunk_size:
                _good_splits.append(s)
            else:
                if _good_splits:
                    merged_text = _separator.join(_good_splits)
                    final_chunks.append(merged_text)
                    _good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    other_info = _split_text(s, new_separators)
                    final_chunks.extend(other_info)
        if _good_splits:
            merged_text = _separator.join(_good_splits)
            final_chunks.append(merged_text)
        return final_chunks

    chunks = _split_text(text, separators)
    # Add overlap
    final_chunks = []
    for i in range(0, len(chunks)):
        start = max(0, i * chunk_size - i * chunk_overlap)
        end = start + chunk_size
        final_chunks.append(chunks[i][start:end])
    return final_chunks

def embed_documents(openai_client, input_path, study):
    """
    Embed the documents for a given study.

    Args:
        openai_client (object): The OpenAI client.
        input_path (str): The input path for the study.
        study (str): The study name.

    Returns:
        tuple: A tuple containing the text chunks and their embeddings.
    """
    with fs.open(f"{input_path}/{study}/context.txt", 'r', encoding='utf-8') as file:
        doc_text = file.read()
    text_chunks = split_text_recursively(doc_text, chunk_size=1000, chunk_overlap=20)
    text_chunks = [chunk for chunk in text_chunks if chunk.strip()]  # Drop empty chunks
    embeddings = []
    for chunk in text_chunks:
        embeddings.append(get_embedding(openai_client, chunk))
    return text_chunks, embeddings

def get_relevent_context(openai_client, varname, text_chunks, embeddings, relevance_dist='min'):
    """
    Get the relevant context for a variable name based on embeddings.

    Args:
        openai_client (object): The OpenAI client.
        varname (str): The variable name.
        text_chunks (list): The list of text chunks.
        embeddings (list): The list of embeddings.
        relevance_dist (str, optional): 'min' for minimum distance, 'max' for maximum. Defaults to 'min'.

    Returns:
        str: The relevant context for the variable.
    """
    embedded_query = get_embedding(openai_client, f"variable name:  {varname}, label or description: ")
    dists = [spatial.distance.cosine(embedded_query, x) for x in embeddings]
    idx = get_index(dists, 3, by = relevance_dist)
    example_context = [text_chunks[i] for i in idx] # type: ignore
    return '\n'.join([x for x in example_context])

def get_example_dict(openai_client, described, variables_df, text_chunks=None, embeddings=None):
    """
    Create a dictionary of example contexts and descriptions.

    Args:
        openai_client (object): The OpenAI client.
        described (list): List of described variables.
        variables_df (DataFrame): DataFrame containing variable information.
        text_chunks (list, optional): List of text chunks. Defaults to None.
        embeddings (list, optional): List of embeddings. Defaults to None.

    Returns:
        dict: Dictionary of example contexts and descriptions.
    """
    # create a maximum of 5 examples (Thanks Pierre Kloppers!)
    example_dict = {}
    example_limitor = len(described)
    if len(described)>5:
        example_limitor = 5
    for num in range(0,example_limitor):
        example = described[num]
        example_description = variables_df.loc[variables_df['variable_name'] == example]['description'].values[0]
        if embeddings is not None and text_chunks is not None:
            example_context = get_relevent_context(openai_client, example, text_chunks, embeddings)
        else:
            example_context = 'Not available'
        example_dict[example] = [example_description, example_context]
    return example_dict

def get_openai_llm_response(openai_client, prompt):
    """
    Get the response from OpenAI's LLM for a given prompt.

    Args:
        openai_client (object): The OpenAI client.
        prompt (list): The prompt messages.

    Returns:
        str: The response from the LLM.
    """
    llm_response = None
    try:
        llm_response = openai_client.chat.completions.create(model="gpt-4o-mini", messages=prompt)
    except:
        time.sleep(1)
        print('retry')
        try:
            llm_response = openai_client.chat.completions.create(model="gpt-4o-mini", messages=prompt)
        except:
            llm_response = None
            print('openai fail') # if all fail good chance the context length is too long
    if llm_response:
        label = llm_response.choices[0].message.content # type: ignore
        return ''.join(['*',label]) # add a * to indicate this description is AI generated
    else: 
        return None
    
def get_llm_response(openai_client, prompt):
    """
    Get the response from the LLM for a given prompt.

    Args:
        openai_client (object): The OpenAI client.
        prompt (list): The prompt messages.

    Returns:
        str: The response from the LLM.
    """
    if openai_client:
        return get_openai_llm_response(openai_client, prompt)
    else:
        raise ValueError("No OpenAI API client found. Please provide an API key to proceed.")

def generate_descriptions():
    """
    Generate descriptions for variables in datasets.
    """
    config = dotenv_values(".env")
    openai_client = init_llm_models(config)
    init_prompt = config['init_prompt']
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    done = [x for x in avail_studies if fs.exists(f'{input_path}/{x}/dataset_variables_auto_completed.csv')] # skip already done
    avail_studies = [x for x in avail_studies if x not in done]
    for study in avail_studies:
        print(study)
        variables_df = pd.read_csv(f'{input_path}/{study}/dataset_variables.csv')
        # get variables to describe
        to_do = []
        described = []
        for i in range(len(variables_df)):
            if not type(variables_df.iloc[i]['description']) == str:
                if math.isnan(variables_df.iloc[i]['description']):
                    to_do.append(variables_df.iloc[i]['variable_name'])
            else:
                described.append(variables_df.iloc[i]['variable_name'])

        if len(to_do) == 0: # if all variables are described no need to do anything
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv')
        else:
            # check if context is available
            context_available = False
            text_chunks, embeddings = None, None
            if fs.exists(f"{input_path}/{study}/context.txt"):
                text_chunks, embeddings = embed_documents(openai_client, input_path, study) 
                context_available = True

            # check if examples are available
            example_dict = None
            if not len(described) == 0:
                example_dict = get_example_dict(openai_client, described, variables_df, text_chunks,embeddings)
            
            # create descriptions
            codebook = {}
            for var in to_do:
                # get context for variable if available
                context = 'Not available'
                if context_available:
                    context = get_relevent_context(openai_client, var, text_chunks, embeddings)

                # create prompt
                prompt = return_prompt(init_prompt, var, context, example_dict)

                # get LLM response
                llm_response = get_llm_response(openai_client, prompt)
                if llm_response:
                    codebook[var] = llm_response
            
            # update variables_df
            variables_df['description'] = variables_df['description'].astype(str)
            for var in list(codebook):
                variables_df.loc[variables_df['variable_name'] == var,'description'] = codebook[var]
            
            # write to file
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index = False)

if __name__ == '__main__':
    generate_descriptions()
