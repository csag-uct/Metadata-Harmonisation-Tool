import streamlit as st
import pandas as pd
import fsspec
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

def upload_codebook(file_in):
    target_df = streamlit_csv_reader(file_in)
    target_df= target_df[['variable_name', 'description']]
    target_df.to_csv(f"{input_path}/target_variables.csv", index = False)

def upload_codebook_page():
    col1, col2= st.columns(2)
    with col1:
        st.write("To Upload a new codebook complete the form below. By default an example codebook is added.")
        with st.form("my_form"):
            new_target_df = st.file_uploader('Target Codebook', type='csv', accept_multiple_files=False, help = "Only CSV format accepted. The File should contain two columns titled 'variable_name' and 'description'. A description is required for each variable_name.")
            submit = st.form_submit_button(":green[Update Codebook]", help = 'Note when uploading a new codebook the recommendation engine will rerun for all studies. This may take a few minutes.')
            if submit:
                upload_codebook(new_target_df)
                
    with col2:
        if fs.exists(f'{input_path}/target_variables.csv'):
            st.write("Target Codebook")
            target_df = pd.read_csv(f'{input_path}/target_variables.csv')[['variable_name', 'description']]
            st.dataframe(target_df, use_container_width=True)
        else:
            st.write("No codebook is currently loaded")