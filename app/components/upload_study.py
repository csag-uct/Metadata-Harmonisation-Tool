import streamlit as st
import pandas as pd
import fsspec

from .get_recommendations import get_recommendations
from .generate_descriptions import generate_descriptions_with_context, generate_descriptions_without_context, convert_pdf_to_txt

import clevercsv
from io import StringIO


results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def streamlit_csv_reader(file_up):
    "CSV files are a nightmare this func takes in a streamlit file uploader and returns a pandas df"
    stringio = StringIO(file_up.getvalue().decode("utf-8"))
    delim = clevercsv.Sniffer().sniff(stringio.read()).delimiter
    return pd.read_csv(file_up, sep = delim)

def add_new_study(study_title, study_description, variables, example_data, context_docs):
    variables_df = streamlit_csv_reader(variables)[['variable_name', 'description']]
    study_path = f"{input_path}/{study_title}"
    fs.mkdir(study_path)
    if study_description:
        with fs.open(f"{study_path}/description.txt", "w") as file:
            file.write(study_description)
    variables_df.to_csv(f"{study_path}/dataset_variables.csv")
    if example_data:
        example_df = pd.read_csv(example_data)
        example_df.to_csv(f"{study_path}/example_data.csv")
    if context_docs:
        with open(f"{study_path}/context.pdf", "wb") as file:
            file.write(context_docs.getvalue())

def add_study_page():
    if not fs.exists(f"input/target_variables.csv"):
        st.write(":red[Please upload a target codebook before submitting a study to map]")
        disable = True
    else:
        disable = False
    st.text("Complete and submit the form below to add a new study to the mapping tool.")
    with st.form("my_form", clear_on_submit=True):
        study_title = st.text_input('Study Title:', '')
        study_description = st.text_input('Study Description:', '')
        variables = st.file_uploader('Variables Table:', type='csv', accept_multiple_files=False, help = "Only CSV format accepted. The File should contain two columns titled 'variable_name' and 'description', If the desription of a variable is unknown the cell should be an empty string.")
        example_data = st.file_uploader('Example Data (optional):', type='csv', accept_multiple_files=False, help = "Optional. To assist in mapping you can upload a file containing example data. The app will automatically select a random subset of this data to display alongside the variable's name and description. Column titles of the example data should correspond to a 'variable_name' in the variables table. ")
        context_docs = st.file_uploader('Contextual Documents (optional):', type=['pdf'], accept_multiple_files=False, help = "This application uses natural language processing to automatically provide variable descriptions. To aid this process you can upload a relevant document such as a study protocol, journal article, or ideally codebook here.")
        submit = st.form_submit_button(":green[Add New Study]", disabled = disable)
        if submit:
            add_new_study(study_title, study_description, variables, example_data, context_docs)
            st.experimental_rerun()