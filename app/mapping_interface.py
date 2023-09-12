import streamlit as st
import pandas as pd
import fsspec
import duckdb
import time

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



st.set_page_config(layout="wide",
                   page_title="HE2AT Codebook Mapping Tool",
                   page_icon=":wave:"
                   )

# init side bar
avail_studies = [f for f in fs.ls("input/") if fs.isdir(f)]
avail_studies = [f.split('/')[-1] for f in avail_studies
                 if f.split('/')[-1][0] != '.']

with st.sidebar:
    st.image('DS-I_logo.png', width=200)
    st.title("Mapping Tool")
    study = st.selectbox('Study', avail_studies)


results_file = f'results/{study}.csv'
input_path = f"input/{study}"

mapping_options = ['To do',
                    'Successfully mapped',
                    'Marked to reconsider',
                    'Marked unmappable']

# about data
st.title(study)

if fs.exists(f"{input_path}/description.txt"):
    with fs.open(f"{input_path}/description.txt", 'r') as of:
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

# get variables
variables_status = st.selectbox('View variables:',mapping_options)
# query results file
variables = duckdb.sql(f"""SELECT study_var
                    FROM read_csv_auto('{results_file}', delim = ',', header = True)
                    WHERE marked = '{variables_status}'""")
# coerce db output to list
variables = list(variables.fetchdf()['study_var'].values)

# sort in original order if requested
agree = st.checkbox('Show variables in original study order (default is easiest to hardest to map)')
if agree:
    variables = [x for x in vars_unsorted if x in variables]

if len(variables) == 0:
    st.write(f'No variables have been marked: :red[{variables_status}]')
else:
    # get var to map
    variable_to_map = st.selectbox('Select Variable To Map', variables)
    # previous info
    st.write('The following information has previously been recorded:')
    st.write(duckdb.sql(f"""SELECT *
                        FROM read_csv_auto('{results_file}', delim = ',', header = True)
                        WHERE study_var = '{variable_to_map}'""").fetchdf())

    # information about variable
    to_map_df = vars_df[vars_df['variable_name'] == variable_to_map]
    st.write('The Study provides the following abbreviation and description')
    df_to_show = to_map_df[['variable_name', 'description']].set_index('variable_name')
    st.dataframe(df_to_show, use_container_width=True)

    # show synthetic
    st.write('Here is an example of some values for this variable:')
    if fs.exists(f"{input_path}/example_data.csv"):
        synthetic_df = pd.read_csv(f"{input_path}/example_data.csv")
        if variable_to_map in list(synthetic_df):
            example_data = synthetic_df[variable_to_map]
        else:
            example_data = None
        st.write(list(example_data))

    # form
    st.write('Please complete the form below:')
    # recomendations
    recommended_codebook = eval(to_map_df.target_recommendations.to_list()[0])
    # distances
    recommended_confidence = eval(to_map_df.target_distances.to_list()[0])
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
                                index = 1,
                                format_func=lambda x: mapping_options[x])  # returns index of options
        notes = st.text_input('Notes about this variable:', '')
        submitted = st.form_submit_button(":green[Submit]")
        if submitted:
            _ = write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file)
            time.sleep(0.5)
            st.experimental_rerun()