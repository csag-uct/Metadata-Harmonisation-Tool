import streamlit as st
import pandas as pd
import fsspec

results_path = "results"

fs = fsspec.filesystem("")

def convert_to_download(df):
    """
    Convert a DataFrame to a CSV format and encode it in UTF-8.

    Args:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        bytes: The CSV data encoded in UTF-8.
    """
    return df.to_csv().encode('utf-8')

def download_page():
    """
    Display a Streamlit page for downloading study results as CSV files.

    This function lists available study results, allows the user to select one,
    displays the DataFrame, and provides a download button for the selected study.
    """
    avail_data = [f.split('/')[-1].split('.')[0] for f in fs.ls(f"{results_path}/")]
    if len(avail_data) == 0:
        st.write(':red[No results available, please initialise the mapping app]')
    else:
        name = st.selectbox('Select study to download:', avail_data)
        df = pd.read_csv(f"{results_path}/{name}.csv")
        df.replace('0%', None, inplace=True)
        # only keep the core columns and drop the rest where all values are NaN
        df1 = df[['study_var', 'codebook_var', 'confidence', 'notes', 'marked']]
        df2 = df.drop(columns=['study_var', 'codebook_var', 'confidence', 'notes', 'marked']).dropna(axis=1, how='all')
        df = pd.concat([df1, df2], axis=1)

        # reverse the order of the columns
        df = df.iloc[::-1]

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

