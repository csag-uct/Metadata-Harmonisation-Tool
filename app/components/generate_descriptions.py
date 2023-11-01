import pandas as pd
import math
import fsspec
import time
import openai
from pdfminer.high_level import extract_text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from scipy import spatial

from dotenv import dotenv_values


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

def return_prompt_with_example(init_prompt, variable, context, example, example_context, example_description, bad_context):
    prompts = [{"role": "system", "content": f"""{init_prompt} Some context is provided alongside to help."""},
                {"role": "user", "content": f"variable name:  {example}, context: {example_context}"},
                {"role": "assistant", "content": f"{example_description}"},
                {"role": "user", "content": f"variable name:  matdiag, context: {bad_context}"}, # giving it the least relevent context
                {"role": "assistant", "content": "maternal diagnosis (?)"}, # add (?) to give some context of model confidence
                {"role": "user", "content": f"variable name:  {variable}, context: {context}"}
                ]
    return prompts


def return_prompt(init_prompt, variable, context, bad_context, good_context):
    prompts = [{"role": "system", 
                "content": f"""{init_prompt} Some context is provided alongside to help."""},
                {"role": "user", "content": f"variable name:  Patient ID, context: {good_context}"}, # giving it the least relevent context
                {"role": "assistant", "content": "Patient Identifier"},
                {"role": "user", "content": f"variable name:  matdiag, context: {bad_context}"}, # giving it the least relevent context
                {"role": "assistant", "content": "maternal diagnosis (?)"},
                {"role": "user", "content": f"variable name:  {variable}, context: {context}"}
                ]
    return prompts

def return_prompt_no_context(variable):
    prompts = [{"role": "system", 
                "content": f"""{init_prompt}"""},
                {"role": "user", "content": f"variable name:  Patient ID"}, # giving it the least relevent context
                {"role": "assistant", "content": "Patient Identifier"},
                {"role": "user", "content": f"variable name:  matdiag"}, # giving it the least relevent context
                {"role": "assistant", "content": "maternal diagnosis"},
                {"role": "user", "content": f"variable name:  {variable}"}
                ]
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

# the below two functions should be merged too lazy for the minute

def generate_descriptions_without_context():
    config = dotenv_values(".env")
    OpenAI_api_key = config['OpenAI_api_key']
    openai.api_key = OpenAI_api_key
    init_prompt = config['init_prompt']
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    print(avail_studies)
    # skip already done
    done = [x for x in avail_studies if fs.exists(f'{input_path}/{x}/dataset_variables_auto_completed.csv')]
    avail_studies = [x for x in avail_studies if x not in done]
    # only do if no context
    studies_without_context = [study for study in avail_studies if not fs.exists(f"{input_path}/{study}/context.txt")]
    print(studies_without_context)
    for study in studies_without_context:
        print(study)
        variables_df = pd.read_csv(f'{input_path}/{study}/dataset_variables.csv')

        to_do = []
        described = []
        for i in range(len(variables_df)):
            if not type(variables_df.iloc[i]['description']) == str:
                if math.isnan(variables_df.iloc[i]['description']):
                    to_do.append(variables_df.iloc[i]['variable_name'])
            else:
                described.append(variables_df.iloc[i]['variable_name'])
        
        if not len(to_do) > 0:
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv') # no need to autocomplete
        else:
            # Call openai API
            codebook = {}
            for var in to_do:
                openai_response = None
                prompts = return_prompt_no_context(init_prompt, var)
                try:
                    openai_response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompts)
                except:
                    time.sleep(1)
                    print('retry')
                    try:
                        openai_response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompts)
                    except:
                        openai_response = None
                        print('fail') # if all fail good chance the context length is too long
                if openai_response:
                    label = openai_response.choices[0].message.content # type: ignore
                    codebook[var] = ''.join(['*',label]) #add a * to indicate this description is AI generated
                time.sleep(0.1)

            for var in list(codebook):
                variables_df.loc[variables_df['variable_name'] == var,'description'] = codebook[var]

            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index = False)


def generate_descriptions_with_context():
    config = dotenv_values(".env")
    OpenAI_api_key = config['OpenAI_api_key']
    openai.api_key = OpenAI_api_key
    init_prompt = config['init_prompt']
    print(init_prompt)
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    # skip already done
    done = [x for x in avail_studies if fs.exists(f'{input_path}/{x}/dataset_variables_auto_completed.csv')]
    avail_studies = [x for x in avail_studies if x not in done]
    # only do if context
    studies_with_context = [study for study in avail_studies if fs.exists(f"{input_path}/{study}/context.txt")]
    print(studies_with_context)
    for study in studies_with_context:
        print(study)
        variables_df = pd.read_csv(f'{input_path}/{study}/dataset_variables.csv')
        to_do = []
        described = []
        for i in range(len(variables_df)):
            if not type(variables_df.iloc[i]['description']) == str:
                if math.isnan(variables_df.iloc[i]['description']):
                    to_do.append(variables_df.iloc[i]['variable_name'])
            else:
                described.append(variables_df.iloc[i]['variable_name'])
        
        if not len(to_do) > 0:
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv') # no need to autocomplete
        else:
            #  read plain text
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
            embeddings_model = OpenAIEmbeddings(openai_api_key=OpenAI_api_key)
            embeddings = embeddings_model.embed_documents([x.page_content for x in text_chunks])
            
            # defining function here just reduces complexity of below func not great practice I know - sorry!
            def get_relevent_context(varname, relevance_dist = 'min'):
                embedded_query = embeddings_model.embed_query(f"variable name:  {varname}, label or description: ")
                dists = [calculate_cosine_similarity(embedded_query,x) for x in embeddings]
                idx = get_index(dists, by = relevance_dist)
                example_context = [text_chunks[i] for i in idx] # type: ignore
                return '\n'.join([x.page_content for x in example_context])
            
            if len(described) > 0:
                example = described[0]
                example_description = variables_df.loc[variables_df['variable_name'] == example]['description'].values[0]
                example_context = get_relevent_context(example, relevance_dist = 'min')
            else:
                example = None
                example_description = None
                example_context = None

            bad_context = get_relevent_context('matdiag', relevance_dist = 'max')
            good_context = get_relevent_context('Patient ID', relevance_dist = 'min') # an easy one
            
            # Call openai API
            codebook = {}
            for var in to_do:
                openai_response = None
                context = get_relevent_context(var, relevance_dist = 'min')
                if example:
                    prompts = return_prompt_with_example(init_prompt, var, context, example, example_context, example_description, bad_context)
                else:
                    prompts = return_prompt(init_prompt, var, context, bad_context, good_context)
                # the openai api is a bit unstable this just has two retries 
                try:
                    openai_response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompts)
                except:
                    time.sleep(1)
                    print('retry')
                    try:
                        openai_response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompts)
                    except:
                        openai_response = None
                        print('fail') # if all fail good chance the context length is too long
                if openai_response:
                    label = openai_response.choices[0].message.content # type: ignore
                    codebook[var] = ''.join(['*',label]) #add a * to indicate this description is AI generated
                time.sleep(0.1)

            for var in list(codebook):
                variables_df.loc[variables_df['variable_name'] == var,'description'] = codebook[var]

            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index = False)






        