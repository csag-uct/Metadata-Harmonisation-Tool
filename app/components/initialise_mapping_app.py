import streamlit as st
import fsspec

import time

from .get_recommendations import get_embeddings, get_recommendations, embed_codebook
from .generate_descriptions import generate_descriptions_with_context, generate_descriptions_without_context, convert_pdf_to_txt

from dotenv import dotenv_values

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

def delete_files_and_folders(directory_path):
    files_and_dirs = fs.ls(directory_path)
    for item in files_and_dirs:
        if fs.isdir(item):
            fs.rm(item, recursive=True)
        else:
            fs.rm(item)

def initialise_mapping_recommendations():
    config = dotenv_values(".env")
    if 'OpenAI_api_key' not in list(config):
        st.write(":red[No OpenAI key detected, please insert a key below]")
        OpenAI_api_key = st.text_input("OpenAI_api_key", value="", type = "password")
        submit = st.button("Add Key")
        if submit:
            with open(".env", 'a+') as file:
                lines = file.readlines()
            lines.insert(0, f"OpenAI_api_key={OpenAI_api_key}")
            with open(".env", 'w') as file:
                file.writelines(lines) 
            st.experimental_rerun()
    else:
        st.write(f":green[OpenAI_api_key detected :white_check_mark:]")
    
    if fs.exists(f'{input_path}/target_variables.csv'):
        if fs.exists(f'{input_path}/target_variables_with_embeddings.csv'):
            st.write(":green[Codebook Uploaded and Embeddings Fetched :white_check_mark:]")
        else:
            st.write(":green[Codebook Uploaded, ] :red[Embeddings Not Fetched]")
    else:
        st.write(":red[Please Upload a Codebook]")

    avail_studies = []
    avail_studies = [f for f in fs.ls(f"{input_path}/") if fs.isdir(f)]
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.']
    uploaded = [x for x in avail_studies if fs.exists(f"{input_path}/{x}/dataset_variables.csv")]
    mapped = [x for x in avail_studies if fs.exists(f'{input_path}/{x}/dataset_variables_with_recommendations')]

    if len(uploaded) > 0 :
        if len(uploaded) == len(mapped):
            st.write(f":green[{len(uploaded)} studies have been uploaded and recommendations created for all of them. :white_check_mark:]")
        else:
            st.write(f":green[{len(uploaded)} studies have been uploaded.] :red[{len(mapped)} studies have had recommendations created for them.]")
    else:
         st.write(":red[Please upload a study to map]")

    run = st.button("Run Recomendation Engine")
    if run:
        with st.spinner('Phoning a friend :coffee:...'):
            convert_pdf_to_txt()
            generate_descriptions_without_context()
            generate_descriptions_with_context()
            get_embeddings()
            get_recommendations()
            st.experimental_rerun()

    st.divider()

    clear = st.button(":red[Clear Workspace]")
    if clear:
        delete_files_and_folders("input/")
        delete_files_and_folders("results/")
        st.experimental_rerun()
    

