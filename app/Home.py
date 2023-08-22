import streamlit as st
import pandas as pd
import fsspec
import duckdb
from streamlit_keycloak import login

fs = fsspec.filesystem("")


def write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file):
    mapped_variable = mapped_variable.split(' - ')
    if len(mapped_variable) > 1:
        codebook_var = mapped_variable[0]
        confidence = mapped_variable[1]
    else:
        codebook_var = mapped_variable[0]
        confidence = None
    mark_options = ['To do',
                    'Successfully mapped',
                    'Marked to reconsider',
                    'Marked unmappable']
    marked = mark_options[avail_idx]
    df_new = pd.DataFrame({
        'study_var': variable_to_map,
        'codebook_var': codebook_var,
        'confidence': confidence,
        'notes': notes,
        'marked': marked},
        index = [0])
    st.write('The following has been saved:')
    st.write(df_new)
    df_old = pd.read_csv(results_file)
    df_updated = pd.concat([df_old, df_new], ignore_index=True)
    df_updated = df_updated.drop_duplicates(subset=['study_var'], keep='last')
    df_updated.to_csv(results_file, index=False)


def main():
    results_file = f'results/{study}/out.csv'
    health_open_path = f"../data/{study}"

    mapping_options = ['To do',
                       'Successfully mapped',
                       'Marked to reconsider',
                       'Marked unmappable']
    # about data
    with fs.open(f"{health_open_path}/metadata/about.md", 'r') as of:
        text = of.read()
    st.markdown(text)

    st.divider()

    vars_df = pd.read_csv(
        f"{health_open_path}/metadata/variables_with_recomendations.csv"
        )

    # the below sorts the variables by difficulty to match to a codebook variable
    vars_df['best_dist'] = [eval(x)[0] for x in vars_df['codebook_distances']]
    # get variables
    vars_unsorted = vars_df['var']
    # get variables sorted
    vars_df = vars_df.sort_values('best_dist')
    all_variables = vars_df['var']

    # get already mapped/init
    if not fs.exists(results_file):
        fs.mkdirs(f'results/{study}', exist_ok = True)
        # write an empty dataframe to file
        empty_df = pd.DataFrame(columns=['study_var',
                                         'codebook_var',
                                         'confidence',
                                         'notes',
                                         'marked'])
        empty_df['study_var'] = all_variables
        empty_df['marked'] = 'To do'
        empty_df.to_csv(results_file, index=False)

    agree = st.checkbox('Show all variables in original study order')
    # get variables
    if agree:
        variables = vars_unsorted
    else:
        variables_status = st.selectbox('View variables:',mapping_options)
        # query results file
        variables = duckdb.sql(f"""SELECT study_var
                            FROM '{results_file}'
                            WHERE marked = '{variables_status}'""")
        # coerce db output to list
        variables = list(variables.fetchdf()['study_var'].values)
    

    if len(variables) == 0:
        st.write(f'No variables have been marked: :red[{variables_status}]')
    else:
        # get var to map
        variable_to_map = st.selectbox('Select Variable To Map', variables)

        st.write('The following information has previously been recorded:')
        st.write(duckdb.sql(f"""SELECT *
                            FROM '{results_file}'
                            WHERE study_var = '{variable_to_map}'""").fetchdf())

        # previous info
        to_map_df = vars_df[vars_df['var'] == variable_to_map]
        st.write('The Study provides the following abbreviation and description')
        df_to_show = to_map_df[['var', 'description']].set_index('var')
        st.dataframe(df_to_show, use_container_width=True)

        # show synthetic
        st.write('Here is an example of some values for this variable:')
        example_data = None
        synthetic_files = fs.glob(f"{health_open_path}/synthetic/*.csv")
        synthetic_files = [f.split('/')[-1] for f in synthetic_files]
        for file in synthetic_files:
            synthetic_df = pd.read_csv(f"{health_open_path}/synthetic/{file}")
            if variable_to_map in list(synthetic_df):
                example_data = synthetic_df[variable_to_map]
        if example_data is not None:
            st.write(list(example_data))

        # form
        st.write('Please complete the form below:')
        # recomendations
        recommended_codebook = eval(to_map_df.codebook_recomendations.to_list()[0])
        # distances
        recommended_confidence = eval(to_map_df.codebook_distances.to_list()[0])
        recommended_confidence = [f" - {round((1-x)*(100))}%" for x in recommended_confidence]
        # default is No
        recommended_codebook.insert(0, "No")
        recommended_confidence.insert(0, '')
        # append confidence to var name
        recommended_keys = [f"{x} {y}" for x, y in zip(recommended_codebook, recommended_confidence)]

        with st.form("my_form"):
            mapped_variable = st.selectbox('Does this map to any of these variables?', recommended_keys)
            avail_idx = st.radio("Can this variable be mapped to our codebook?",
                                 range(len(mapping_options)),
                                 format_func=lambda x: mapping_options[x])  # returns index of options
            notes = st.text_input('Notes about this variable:', '')
            submitted = st.form_submit_button(":green[Submit]")
            if submitted:
                write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file)



st.set_page_config(layout="wide",
                   page_title="HE2AT Codebook Mapping Tool",
                   page_icon=":wave:"
                   )

# init side bar
avail_studies = [f for f in fs.ls("../data/") if fs.isdir(f)]
avail_studies = [f.split('/')[-1] for f in avail_studies
                 if f.split('/')[-1][0] != '.']

with st.sidebar:
    st.image('heat_lOGO_5_1.png', width=200)
    st.title("Mapping Tool")
    study = st.selectbox('Study', avail_studies)


main()
