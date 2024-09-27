import streamlit as st
import fsspec
from dotenv import dotenv_values
from .get_recommendations import get_embeddings, get_recommendations, get_PID_date_recommendations
from .generate_descriptions import generate_descriptions, convert_pdf_to_txt
from .util import modify_env, delete_files_and_folders

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

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

    if 'auto_transform_available' not in list(config):
        modify_env('auto_transform_available', 'no')
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
            st.cache_data.clear()
            st.rerun()