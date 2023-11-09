import streamlit as st
import fsspec

from components.upload_codebook import upload_codebook_page
from components.upload_study import add_study_page
from components.map_study import map_study
from components.about import about_page
from components.download import download_page
from components.initialise_mapping_app import initialise_mapping_recommendations

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

study, variables_status, show_about, original_order = None, None, None, None  # just to clear error checking

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

st.set_page_config(layout="wide",
                   page_title="Mapping Tool",
                   page_icon="logo.png"
                   )

with st.sidebar:
    st.image('DS-I_logo.png', width=200)
    st.write("## Metadata Harmonisation Tool")
    st.divider()
    page = st.selectbox('Page', ["About", "Upload Codebook","Upload Studies", "Initialise", "Map Studies", "Download Results"])
    if page == "Map Studies":
        avail_studies = []
        avail_studies = [f for f in fs.ls(f"{input_path}/") if fs.isdir(f)]
        avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.']
        study = st.selectbox('Study', avail_studies)
        variables_status = st.selectbox('View variables:',mapping_options)
        col1, col2 = st.columns(2)
        with col1:
            show_about = st.checkbox("About", help = 'Show an about section for the dataset you have selected. Hiding this can make the mapping process faster as you will not need to scroll up and down to submit')
        with col2:
            original_order = st.checkbox('Unsort', help = 'Show variables in the original order of incoming datasets. This can be helpful if you believe one variable is related to a neighbouring variable in the table. Default is from easiest to hardest to map')

if page == 'About':
    about_page()
elif page == "Upload Studies":
    add_study_page()
elif page == "Upload Codebook":
    upload_codebook_page()
elif page == "Initialise":
    initialise_mapping_recommendations()
elif page == 'Map Studies':
    map_study(study, variables_status, show_about, original_order)
elif page == "Download Results":
    download_page()