import streamlit as st
import fsspec
from dotenv import dotenv_values
from .get_recommendations import get_embeddings, get_recommendations, get_PID_date_recommendations
from .generate_descriptions import generate_descriptions, convert_pdf_to_txt

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

def delete_files_and_folders(directory_path):
    """
    Delete all files and folders in the specified directory.

    Args:
        directory_path (str): Path to the directory to be cleared.
    """
    files_and_dirs = fs.ls(directory_path)
    for item in files_and_dirs:
        if fs.isdir(item):
            fs.rm(item, recursive=True)
        else:
            fs.rm(item)

def modify_env(key, value=None, delete=False):
    """
    Modify the .env file to add, update, or delete a key-value pair.

    Args:
        key (str): The environment variable key.
        value (str, optional): The value to set for the key. Defaults to None.
        delete (bool, optional): If True, delete the key from the .env file. Defaults to False.
    """
    if not fs.exists(".env"):
        with open(".env", 'w'):
            pass 
    with open(".env", 'r') as file:
        lines = file.readlines()
    if not delete:
        line_replaced = False
        for i in range(len(lines)):
            if lines[i].startswith(key):
                lines[i] = key + '=' + value + '\n'
                line_replaced = True
                break
        if not line_replaced:
            lines.append(key + '=' + value + '\n')
    else:
        for i in range(len(lines)):
            if lines[i].startswith(key):
                lines[i] = ""
    with open(".env", 'w') as file:
        file.writelines(lines)

def initialise_mapping_recommendations():
    """
    Initialise the mapping recommendations by setting up the environment and checking for necessary files.
    """
    config = dotenv_values(".env")

    if 'OpenAI_api_key' not in config:
        st.write(":red[No OpenAI key detected, please insert a key below]")
        OpenAI_api_key = st.text_input("OpenAI_api_key", value="", type="password")
        if st.button("Add Key", key='submit'):
            modify_env('OpenAI_api_key', OpenAI_api_key)
            del st.session_state['submit']
            st.rerun()
    else:
        st.write(f":green[OpenAI_api_key detected :white_check_mark:]")

    reset = st.button(":red[Reset LLM Configuration]", key='reset')
    if reset:
        modify_env('OpenAI_api_key', delete=True)
        del st.session_state['reset']
        st.rerun()
    
    st.divider()

    defailt_init_prompt = "As an AI, you're given the task of translating short variable names from a public health study into the most likely full variable name."

    init_prompt = st.text_input('Initialisation Prompt', value="As an AI, you're given the task of translating short variable names from a public health study into the most likely full variable name.")
    
    if 'init_prompt' not in list(config):
        modify_env('init_prompt',init_prompt)
    elif list(config) != defailt_init_prompt:
        modify_env('init_prompt',init_prompt)
    else:
        pass
    
    st.divider()
    
    ready_to_run = False
    if fs.exists(f'{input_path}/target_variables.csv'):
        ready_to_run = True
        if fs.exists(f'{input_path}/target_variables_with_embeddings.csv'):
            st.write(":green[Codebook Uploaded and Embeddings Fetched :white_check_mark:]")
        else:
            st.write(":green[Codebook Uploaded, ] :red[Embeddings Not Fetched]")
    else:
        st.write(":red[Please upload a codebook and study to map]")

    if ready_to_run:
        avail_studies = []
        avail_studies = [f for f in fs.ls(f"{input_path}/") if fs.isdir(f)]
        avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.']
        uploaded = [x for x in avail_studies if fs.exists(f"{input_path}/{x}/dataset_variables.csv")]
        mapped = [x for x in avail_studies if fs.exists(f'{input_path}/{x}/dataset_variables_with_recommendations.csv')]

        if len(uploaded) > 0 :
            if len(uploaded) == len(mapped):
                st.write(f":green[{len(uploaded)} studies have been uploaded and recommendations created for all of them. :white_check_mark:]")
            else:
                st.write(f":green[{len(uploaded)} studies have been uploaded.] :red[{len(mapped)} studies have had recommendations created for them.]")
        else:
            st.write(":red[Please upload a study to map]")

        run = st.button("Run Recommendation Engine", key = 'run')
        if run:
            with st.spinner('Phoning a friend :coffee:...'):
                convert_pdf_to_txt()
                generate_descriptions()
                get_embeddings()
                get_recommendations()
                get_PID_date_recommendations()
                del st.session_state['run'] 
                # I need to use session states the above is a hack to fix death looping 
                # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
                st.rerun()

        st.divider()

        clear = st.button(":red[Clear Workspace]", key = 'clear')
        if clear:
            delete_files_and_folders("input/")
            delete_files_and_folders("results/")
            del st.session_state['clear'] 
            # I need to use session states the above is a hack to fix death looping 
            # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
            st.rerun()