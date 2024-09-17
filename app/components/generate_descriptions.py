import pandas as pd
import math
import fsspec
import time
from pdfminer.high_level import extract_text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from scipy import spatial
from dotenv import dotenv_values
from .util import init_llm_models

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def calculate_cosine_similarity(embedding1, embedding2):
    similarity = spatial.distance.cosine(embedding1, embedding2)
    return similarity

def get_index(list_in, by):
    indexed_values = list(enumerate(list_in)) # create tuple with og index
    sorted_values = sorted(indexed_values, key=lambda x: x[1]) # sort tuples by values (2nd values in tuple)
    if by == 'min':
        return [index for index, _ in sorted_values[:3]] # return index
    elif by == 'max':
        return [index for index, _ in sorted_values[-3:]]

def return_prompt(init_prompt, variable, context = 'Not available', example_dict = None):
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

def embed_documents(openai_client, input_path, study):
    with fs.open(f"{input_path}/{study}/context.txt", 'r', encoding='utf-8') as file:
        doc_text = file.read()
    text_splitter = RecursiveCharacterTextSplitter(
        #separators = ["\n\n", "\n"," ", ""],
        chunk_size = 1000,
        chunk_overlap  = 20,
        length_function = len,
        is_separator_regex = True,
    )
    text_chunks = text_splitter.create_documents([doc_text])
    embeddings = []
    for chunk in text_chunks:
        embeddings.append(get_embedding(openai_client, chunk.page_content))
    return text_chunks, embeddings

def get_relevent_context(varname, text_chunks, embeddings, relevance_dist = 'min'):
    config = dotenv_values(".env")
    embeddings_model = OpenAIEmbeddings(openai_api_key=config['OpenAI_api_key'])
    embedded_query = embeddings_model.embed_query(f"variable name:  {varname}, label or description: ")
    dists = [calculate_cosine_similarity(embedded_query,x) for x in embeddings]
    idx = get_index(dists, by = relevance_dist)
    example_context = [text_chunks[i] for i in idx] # type: ignore
    return '\n'.join([x.page_content for x in example_context])

def get_example_dict(described, variables_df, text_chunks = None, embeddings = None):
    # create a maximum of 5 examples (Thanks Pierre Kloppers!)
    example_dict = {}
    example_limitor = len(described)
    if len(described)>5:
        example_limitor = 5
    for num in range(0,example_limitor):
        example = described[num]
        example_description = variables_df.loc[variables_df['var'] == example]['description'].values[0]
        if embeddings is not None and text_chunks is not None:
            example_context = get_relevent_context(example, text_chunks, embeddings)
        else:
            example_context = 'Not available'
        example_dict[example] = [example_description, example_context]
    return example_dict

def get_openai_llm_response(openai_client, prompt):
    llm_response = None
    try:
        llm_response = openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=prompt)
    except:
        time.sleep(1)
        print('retry')
        try:
            llm_response = openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=prompt)
        except:
            llm_response = None
            print('openai fail') # if all fail good chance the context length is too long
    if llm_response:
        label = llm_response.choices[0].message.content # type: ignore
        return ''.join(['*',label]) # add a * to indicate this description is AI generated
    else: 
        return None
    
def get_llm_response(openai_client, prompt):
    if openai_client:
        return get_openai_llm_response(openai_client, prompt)
    else:
        raise ValueError("No OpenAI API client found. Please provide an API key to proceed.")


def generate_descriptions():
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
                example_dict = get_example_dict(described, variables_df, text_chunks,embeddings)
            
            # create descriptions
            codebook = {}
            for var in to_do:
                # get context for variable if available
                context = 'Not available'
                if context_available:
                    context = get_relevent_context(var, text_chunks, embeddings)

                # create prompt
                prompt = return_prompt(init_prompt, var, context, example_dict)

                # get LLM response
                llm_response = get_llm_response(openai_client, prompt)
                if llm_response:
                    codebook[var] = llm_response
            
            # update variables_df
            for var in list(codebook):
                variables_df.loc[variables_df['variable_name'] == var,'description'] = codebook[var]
            
            # write to file
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index = False)

if __name__ == '__main__':
    generate_descriptions()
