import streamlit as st
import pandas as pd
import fsspec
import duckdb
import time

fs = fsspec.filesystem("")

st.set_page_config(layout="wide",
                   page_title="Mapping Tool",
                   page_icon="logo.png"
                   )

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
    mapping_options = ['To do',
                        'Successfully mapped',
                        'Marked to reconsider',
                        'Marked unmappable']

    with st.sidebar:
        st.title("Mapping Tool")
        avail_studies = []
        avail_studies = [f for f in fs.ls(f"input/") if fs.isdir(f)]
        avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.']
        study = st.selectbox('Study', avail_studies)
        st.divider()
        variables_status = st.selectbox('View variables:',mapping_options)
        st.divider()
        col1, col2= st.columns(2)
        with col1:
            show_about = st.checkbox("About", help = 'Show an about section for the dataset you have selected. Hiding this can make the mapping process faster as you will not need to scroll up and down to submit')
        with col2:
            original_order = st.checkbox('Unsort', help = 'Show variables in the original order of incoming datasets. This can be helpful if you believe one variable is related to another. Default is from easiest to hardest to map')

    
    results_file = f'results/{study}.csv'
    input_path = f"input/{study}"
    

    # about data
    if show_about:
        st.write(f'### {study}')
        if fs.exists(f"{input_path}/metadata/description.txt"):
            with fs.open(f"{input_path}/metadata/description.txt", 'r') as of:
                text = of.read()
            st.write(text)
        st.divider()

    vars_df = pd.read_csv(
        f"preprocess/output/{study}_variables_with_recommendations.csv"
        )

    # the below sorts the variables by difficulty to match to a codebook variable
    vars_df['best_dist'] = [eval(x)[0] for x in vars_df['target_distances']]
    # get variables
    vars_unsorted = vars_df['variable_name']
    # get variables sorted
    vars_df = vars_df.sort_values('best_dist')
    all_variables = vars_df['variable_name']

    # get already mapped/init
    if not fs.exists(results_file):
        # write an empty dataframe to file
        empty_df = pd.DataFrame(columns=['study_var',
                                            'codebook_var',
                                            'confidence',
                                            'notes',
                                            'marked'])
        empty_df['study_var'] = all_variables
        empty_df['marked'] = 'To do'
        empty_df.to_csv(results_file, index=False)

    # query results file
    variables = duckdb.sql(f"""SELECT study_var
                        FROM read_csv_auto('{results_file}', delim = ',', header = True)
                        WHERE marked = '{variables_status}'""")
    # coerce db output to list
    variables = list(variables.fetchdf()['study_var'].values)

    # sort in original order if requested
    if original_order:
        variables = [x for x in vars_unsorted if x in variables]

    if len(variables) == 0:
        st.write(f'No variables have been: :red[{variables_status}]')
    else:
        # get var to map
        variable_to_map = st.selectbox('Select Variable To Map', variables)

        # previous info
        if not variables_status == 'To do':
            st.write('The following information has previously been recorded:')
            st.write(duckdb.sql(f"""SELECT *
                                FROM read_csv_auto('{results_file}', delim = ',', header = True)
                                WHERE study_var = '{variable_to_map}'""").fetchdf())

        col1, col2= st.columns(2)
        with col1:
            # information about variable
            st.write('Variable name and description:')
            to_map_df = vars_df[vars_df['variable_name'] == variable_to_map]
            df_to_show = to_map_df[['variable_name', 'description']].set_index('variable_name')
            st.dataframe(df_to_show, use_container_width=True)
        with col2:
            # show synthetic
            st.write('Example data:')
            if fs.exists(f"{input_path}/example_data.csv"):
                synthetic_df = pd.read_csv(f"{input_path}/example_data.csv")
                if variable_to_map in list(synthetic_df):
                    example_data = synthetic_df[variable_to_map]
                    example_data = [str(x) for x in list(example_data.dropna())]
                    if len(example_data) >= 5:
                        example_data.insert(5, '\n')
                    example = ' ; '.join(example_data)
                    st.code(example)

        # form
        st.write('Please complete the form below:')
        # recomendations
        recommended_codebook = eval(to_map_df.target_recommendations.to_list()[0])
        # distances
        recommended_confidence = eval(to_map_df.target_distances.to_list()[0])
        recommended_confidence = [f" - {round((1-x)*(100))}%" for x in recommended_confidence]
        # append confidence to var name
        recommended_keys = [f"{x} {y}" for x, y in zip(recommended_codebook, recommended_confidence)]

        with st.form("my_form"):
            mapped_variable = st.selectbox('Does this map to any of these variables?', recommended_keys)
            #st.write(df_codebook.loc[df_codebook['Variable Name'] == mapped_variable.split('  - ')[0]]) # inside form won't update
            avail_idx = st.radio("Can this variable be mapped to our codebook?", 
                                    range(len(mapping_options)),
                                    index = 1,
                                    format_func=lambda x: mapping_options[x])  # returns index of options
            notes = st.text_input('Notes about this variable:', '')
            submitted = st.form_submit_button(":green[Submit]")
            if submitted:
                _ = write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file)
                time.sleep(0.5)
                st.experimental_rerun()


main()
