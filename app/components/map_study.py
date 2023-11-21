import streamlit as st
import pandas as pd
import fsspec
import duckdb
import time

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

def split_mapped(mapped_variable):
    mapped_variable = mapped_variable.split(' - ')
    if len(mapped_variable) > 1:
        codebook_var = mapped_variable[0]
        confidence = mapped_variable[1]
    else:
        codebook_var = mapped_variable[0]
        confidence = None
    return codebook_var, confidence

def write_to_results(variable_to_map, mapped_variable_list, notes, avail_idx, results_file):
    codebook_var_list = [split_mapped(x)[0] for x in mapped_variable_list]
    confidence_list = [split_mapped(x)[1] for x in mapped_variable_list]
    mark_options = ['To do',
                    'Successfully mapped',
                    'Marked to reconsider',
                    'Marked unmappable']
    marked = mark_options[avail_idx]
    df = pd.read_csv(results_file).set_index('study_var')
    df.at[variable_to_map, 'codebook_var'] = codebook_var_list
    df.at[variable_to_map, 'confidence'] = confidence_list
    df.at[variable_to_map, 'notes'] = notes
    df.at[variable_to_map, 'marked'] = marked
    st.write('The following has been saved:')
    st.write(df.loc[variable_to_map].to_dict())
    df.to_csv(results_file)

def map_study(study, variables_status, show_about, original_order):
    if study == None:
        st.write(':red[No Studies Loaded]')
    else:
        fs.mkdirs(results_path, exist_ok = True)
        results_file = f'{results_path}/{study}.csv'
        study_input_path = f"{input_path}/{study}"
        # about data
        if show_about:
            st.write(f'### {study}')
            if fs.exists(f"input/{study}/description.txt"):
                with fs.open(f"{study_input_path}/description.txt", 'r') as of:
                    text = of.read()
                st.write(text)
            st.divider()

        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_recommendations'):
            st.write(":red[This study has not had a recommendations file created please initialise the mapping app before proceeding.]")
        else:
            vars_df = pd.read_csv(
                f'{input_path}/{study}/dataset_variables_with_recommendations'
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
                    if fs.exists(f"{study_input_path}/example_data.csv"):
                        synthetic_df = pd.read_csv(f"{study_input_path}/example_data.csv")
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
                mapped_to = []
                mapped_variable = st.selectbox('Does this map to any of these variables?', recommended_keys)
                multiple = st.toggle('Does this variable also map to other codebook variables?')
                print(multiple)
                if multiple:
                    mapped_variable_2 = st.selectbox('Which other variables?', recommended_keys)
                    multiple_2 = st.toggle('Any more? (maximum of 3)')
                    if multiple_2:
                        mapped_variable_3 = st.selectbox('Which variable?', recommended_keys)
                avail_idx = st.radio("Can this variable be mapped to our codebook?", 
                                        range(len(mapping_options)),
                                        index = 1,
                                        format_func=lambda x: mapping_options[x])  # returns index of options
                notes = st.text_input('Notes about this variable:', '')
                submitted = st.button(":green[Submit]", key = 'submit')
                if submitted:
                    if multiple == False:
                        mapped_variable = [mapped_variable]
                    elif multiple_2 == True:
                        mapped_variable = [mapped_variable, mapped_variable_2, mapped_variable_3]
                    else:
                        mapped_variable = [mapped_variable, mapped_variable_2]
                    _ = write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file)
                    time.sleep(0.75)
                    # I need to use session states, the above is a hack to fix death looping 
                    # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
                    del st.session_state['submit'] 
                    st.rerun()