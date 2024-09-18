import streamlit as st
import pandas as pd
import fsspec
import duckdb
import time
import numpy as np

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

def write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instructions=None, transformation_type=None, source_dtype=None, target_dtype=None):
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
        'marked': marked,
        'transformation_instructions': transformation_instructions,
        'transformation_type': transformation_type,
        'source_dtype': source_dtype,
        'target_dtype': target_dtype},
        index = [0])
    st.write('The following has been saved:')
    st.write(df_new)
    df_old = pd.read_csv(results_file)
    df_updated = pd.concat([df_old, df_new], ignore_index=True)
    df_updated = df_updated.drop_duplicates(subset=['study_var'], keep='last')
    df_updated.to_csv(results_file, index=False)

def format_example_data(example_data):
    example_data = [str(x) for x in list(example_data)]
    if len(example_data) >= 5:
        example_data.insert(5, '\n')
    example = ' ; '.join(example_data)
    return example

def generic_catagorical_conversion(x, dictionary_str):
    dictionary_init = eval(dictionary_str)
    dictionary = {str(key): value for key, value in dictionary_init.items()} # convert all keys to string dtype
    x = str(x)
    if x in list(dictionary):
        out = dictionary[x]
        if not out == None:
            return out
        else:
            return np.nan
    else:
        return np.nan

def dtype_conversion(x, dtype):
    try:
        if dtype == 'string':
            return str(x)
        elif dtype == 'str':
            return str(x)    
        elif dtype == 'float':
            return float(x)
        elif dtype == 'integer':
            return int(x)
        elif dtype == 'int':
            return int(x)
        elif dtype == 'boolean':
            return bool(x)
        elif dtype == 'other':
            return x
    except:
        return np.nan

def generic_direct_conversion(x, x_str, source_dtype, target_dtype):
    x = dtype_conversion(x, source_dtype)
    x = eval(x_str)
    return dtype_conversion(x, target_dtype)

def test_transformation(example_data, transformation_type, transformation_instructions, source_dtype, target_dtype):
    if transformation_instructions == '':
        transformed_data = None
    else:
        if transformation_type == 'Direct':
            try:
                transformed_data = [generic_direct_conversion(x, transformation_instructions, source_dtype, target_dtype) for x in example_data]
                transformed_data = format_example_data(transformed_data)
            except Exception as e:
                transformed_data = f'Direct transformation failed with error: {e}'
        elif transformation_type == 'Categorical':
            try:
                transformed_data = [generic_catagorical_conversion(x, transformation_instructions) for x in example_data]
                transformed_data = format_example_data(transformed_data)
            except Exception as e:
                transformed_data = f'Categorical transformation failed with error: {e}'
    st.write('Preview of transformation:')
    st.code(transformed_data)

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

                example_avail = False
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
                        if variable_to_map in list(synthetic_df.columns):
                            example_data = synthetic_df[variable_to_map]
                            example_data = [str(x) for x in list(example_data.dropna())]
                            st.code(format_example_data(example_data))
                            example_avail = True

                st.write('Please complete the form below:')
                # recomendations
                recommended_codebook = eval(to_map_df.target_recommendations.to_list()[0])
                # distances
                recommended_confidence = eval(to_map_df.target_distances.to_list()[0])
                recommended_confidence = [f" - {round((1-x)*(100))}%" for x in recommended_confidence]
                # append confidence to var name
                recommended_keys = [f"{x} {y}" for x, y in zip(recommended_codebook, recommended_confidence)]
                # select variable
                mapped_variable = st.selectbox('Does this map to any of these variables?', recommended_keys)
                # select mapping option
                avail_idx = st.radio("Can this variable be mapped to our codebook?", 
                                        range(len(mapping_options)),
                                        index = 1,
                                        format_func=lambda x: mapping_options[x])  # returns index of options
                notes = st.text_input('Notes about this variable:', '')
                if example_avail:
                    col3, col4= st.columns(2)
                    with col3:
                        transformation_instructions = st.text_input('Transformation instructions for this variable:', '')
                        transformation_type = st.selectbox('Type of transformation applied to this variable:', ['Direct', 'Categorical'])
                        if transformation_type == 'Direct':
                            source_dtype = st.selectbox('Source data type:', ['float', 'integer', 'string', 'boolean'])
                            target_dtype = st.selectbox('Target data type:', ['float', 'integer', 'string', 'boolean'])
                        else:
                            source_dtype = None
                            target_dtype = None
                    with col4:
                        test_transformation(example_data, transformation_type, transformation_instructions, source_dtype, target_dtype)
                submitted = st.button(":green[Submit]", key = 'submit')
                if submitted:
                    # write mappings to results
                    _ = write_to_results(variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instructions, transformation_type, source_dtype, target_dtype)
                    # sleep a few seconds to show results being written
                    time.sleep(0.2)
                    # I need to use session states, the above is a hack to fix death looping 
                    # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
                    del st.session_state['submit'] 
                    st.rerun()