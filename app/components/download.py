import streamlit as st
import pandas as pd
import fsspec

results_path = "results"

fs = fsspec.filesystem("")

def convert_to_download(df):
    return df.to_csv().encode('utf-8')

def download_page():
    avail_data = [f.split('/')[-1].split('.')[0] for f in fs.ls(f"{results_path}/")]
    if len(avail_data) == 0:
        st.write(':red[No results available, please upload a codebook and study to map]')
    else:
        name = st.selectbox('Select study to download:', avail_data)
        df = pd.read_csv(f"{results_path}/{name}.csv")
        col1, col2= st.columns(2)
        with col1:
            st.dataframe(df)
        with col2:
            st.download_button(
                label="Download data as CSV",
                data=convert_to_download(df),
                file_name=f'{name}_mapping_results.csv',
                mime='text/csv',
                )

