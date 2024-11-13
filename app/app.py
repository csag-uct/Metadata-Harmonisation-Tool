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

study, variables_status, show_about, original_order, relational_mode, enable_transformations = None, None, None, None, None, None  # just to clear error checking

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

st.set_page_config(layout="wide",
                   page_title="Mapping Tool",
                   page_icon="logo.png"
                   )

with st.sidebar:
    st.image('logo.png', width=200)
    st.write("## Mapping App")
    st.divider()
    page = st.selectbox('Page', ["About", "Upload Codebook","Upload Studies", "Initialise", "Map Studies", "Download Results"])
    if page == "Map Studies":
        if fs.exists(f'input/'):
            avail_studies = []
            avail_studies = [f for f in fs.ls(f"{input_path}/") if fs.isdir(f)]
            avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.']
            study = st.selectbox('Study', avail_studies)
            variables_status = st.selectbox('View variables:',mapping_options)
        col1, col2 = st.columns(2)
        with col1:
            show_about = st.checkbox("About", value = False, help = 'Show an about section for the dataset you have selected.')
        with col2:
            original_order = st.checkbox('Unsort', value = False, help = 'Show variables in the original order of incoming datasets. This can be helpful if you believe one variable is related to a neighbouring variable in the table.')
        col3, col4 = st.columns(2)
        with col3:
            relational_mode = st.checkbox('Relational Mode', value = True, help = 'Enable this to map date and index (eg patient ID) to each variable. Use this if the goal is to populate a relational database.')
        with col4:
            enable_transformations = st.checkbox('Transform Mode', value = True, help = 'This adds functionality to create and test transformations instructions for each variable. These instructions can then be used to transform data to a common format. Example transformation instructions available [here](https://github.com/csag-uct/Metadata-Harmonisation-Tool/pull/19#issuecomment-2356409576). Only available if example data is provided.')
    st.divider()
    st.write('Please report any issues to the [GitHub repository](https://github.com/csag-uct/Metadata-Harmonisation-Tool) or contact peter.marsh@uct.ac.za for more information.')

if page == 'About':
    about_page()
elif page == "Upload Studies":
    add_study_page()
elif page == "Upload Codebook":
    upload_codebook_page()
elif page == "Initialise":
    initialise_mapping_recommendations()
elif page == 'Map Studies':
    if study is not None:
        map_study(study, variables_status, show_about, original_order, relational_mode, enable_transformations)
    else:
        st.write(':red[No studies available. Please initialise the mapping app]')
elif page == "Download Results":
    download_page()