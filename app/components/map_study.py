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

def split_var_confidence(mapped_value):
    """
    Splits a mapped value into variable and confidence parts.

    Args:
        mapped_value (str): The mapped value string.

    Returns:
        tuple: A tuple containing the variable and confidence.
    """
    parts = mapped_value.split('  - ')
    if len(parts) > 1:
        return parts[0], parts[1]
    else:
        return parts[0], None

def write_to_results(study, variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instructions=None, transformation_type=None, source_dtype=None, target_dtype=None, patient_id=None, date=None):
    """
    Writes the mapping results to a CSV file.

    Args:
        study (str): The study name.
        variable_to_map (str): The variable to map.
        mapped_variable (str): The mapped variable.
        notes (str): Notes about the mapping.
        avail_idx (int): Index of the mapping option.
        results_file (str): Path to the results file.
        transformation_instructions (str, optional): Transformation instructions. Defaults to None.
        transformation_type (str, optional): Type of transformation. Defaults to None.
        source_dtype (str, optional): Source data type. Defaults to None.
        target_dtype (str, optional): Target data type. Defaults to None.
        patient_id (str, optional): Patient ID. Defaults to None.
        date (str, optional): Date. Defaults to None.
    """
    codebook_var, confidence = split_var_confidence(mapped_variable)
    patient_id_var, patient_id_confidence = split_var_confidence(patient_id)
    date_var, date_confidence = split_var_confidence(date)

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
        'target_dtype': target_dtype,
        'patient_id_var': patient_id_var,
        'patient_id_confidence': patient_id_confidence,
        'date_var': date_var,
        'date_confidence': date_confidence},
        index=[0])
    st.write('The following has been saved:')
    st.write(df_new)
    df_old = pd.read_csv(results_file)
    df_updated = pd.concat([df_old, df_new], ignore_index=True)
    df_updated = df_updated.drop_duplicates(subset=['study_var'], keep='last')
    df_updated.to_csv(results_file, index=False)
    add_to_session_state(study, patient_id_var, date_var)

def format_example_data(example_data):
    """
    Formats example data for display.

    Args:
        example_data (list): List of example data.

    Returns:
        str: Formatted example data string.
    """
    example_data = [str(x) for x in list(example_data)]
    if len(example_data) >= 5:
        example_data.insert(5, '\n')
    example = ' ; '.join(example_data)
    return example

def generic_catagorical_conversion(x, dictionary_str):
    """
    Converts a value using a categorical dictionary.

    Args:
        x (any): The value to convert.
        dictionary_str (str): The dictionary as a string.

    Returns:
        any: The converted value or NaN if conversion fails.
    """
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
    """
    Converts a value to a specified data type.

    Args:
        x (any): The value to convert.
        dtype (str): The target data type.

    Returns:
        any: The converted value or NaN if conversion fails.
    """
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
    """
    Performs a direct conversion of a value.

    Args:
        x (any): The value to convert.
        x_str (str): The conversion expression as a string.
        source_dtype (str): The source data type.
        target_dtype (str): The target data type.

    Returns:
        any: The converted value.
    """
    x = dtype_conversion(x, source_dtype)
    x = eval(x_str)
    return dtype_conversion(x, target_dtype)

def test_transformation(example_data, transformation_type, transformation_instructions, source_dtype, target_dtype):
    """
    Tests a transformation on example data.

    Args:
        example_data (list): List of example data.
        transformation_type (str): The type of transformation.
        transformation_instructions (str): The transformation instructions.
        source_dtype (str): The source data type.
        target_dtype (str): The target data type.
    """
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

def add_to_session_state(study, patient_id, date):
    """
    Adds patient ID and date to the session state.

    Args:
        study (str): The study name.
        patient_id (str): The patient ID.
        date (str): The date.
    """
    st.session_state[f'PID_{study}'] = patient_id
    st.session_state[f'date_{study}'] = date

def reorder_lists(list1, list2, value):
    """
    Reorders two lists, such that the value is at the top of list1.

    Args:
        list1 (list): The first list.
        list2 (list): The second list.
        value (any): The value to reorder around.

    Returns:
        tuple: The reordered lists.
    """
    index = list1.index(value)
    reordered_list1 = [value] + list1[:index] + list1[index+1:]
    reordered_list2 = [list2[index]] + list2[:index] + list2[index+1:]
    return reordered_list1, reordered_list2

def pre_process_recomendations(to_map_df, type_, study):
    """
    Pre-processes recommendations for mapping. By appending the confidence to the recommendation and reordering the list to have the previous PID or Date at the top of the respective lists. 

    Args:
        to_map_df (DataFrame): The DataFrame containing variables to map.
        type_ (str): The type of recommendation (e.g., 'target', 'PID', 'date').
        study (str): The study name.

    Returns:
        list: List of recommended keys.
    """
    recommended_codebook = eval(to_map_df[f'{type_}_recommendations'].to_list()[0])
    recommended_confidence = eval(to_map_df[f'{type_}_distances'].to_list()[0])
    recommended_confidence = [f" - {round((1-x)*(100))}%" for x in recommended_confidence]
    if f'{type_}_{study}' in st.session_state:
        if st.session_state[f'{type_}_{study}'] != 'None':
            recommended_codebook, recommended_confidence = reorder_lists(recommended_codebook, recommended_confidence, st.session_state[f'{type_}_{study}'])
    recommended_keys = [f"{x} {y}" for x, y in zip(recommended_codebook, recommended_confidence)]
    if type_ in ['PID', 'date']:
        recommended_keys.insert(0, 'None  - 0%')
    return recommended_keys

def map_study(study, variables_status, show_about, original_order, relational_mode, enable_transformations):
    """
    Main function to map study variables to codebook variables.

    Args:
        study (str): The study name.
        variables_status (str): The status of the variables to map.
        show_about (bool): Whether to show the about section.
        original_order (bool): Whether to sort variables in original order.
        relational_mode (bool): Whether to enable relational mode.
        enable_transformations (bool): Whether to enable transformations.
    """
    if study == None:
        st.write(':red[No studies available, please initialise the mapping app]')
    else:
        fs.mkdirs(results_path, exist_ok=True)
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

        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv'):
            st.write(":red[This study has not had a recommendations file created please initialise the mapping app before proceeding.]")
        else:
            vars_df = pd.read_csv(
                f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv'
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
                                                 'marked',
                                                 'patient_id',
                                                 'date',
                                                 'time'])
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
                col1, col2 = st.columns(2)
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
                # append confidence to var name
                recommended_keys = pre_process_recomendations(to_map_df, 'target', study)
                # select variable
                mapped_variable = st.selectbox('Does this map to any of these variables?', recommended_keys) # type: ignore
                if relational_mode:
                    patient_id_keys = pre_process_recomendations(to_map_df, 'PID', study)
                    patient_id = st.selectbox('Patient ID:', patient_id_keys) # type: ignore
                    date_keys = pre_process_recomendations(to_map_df, 'date', study)
                    date = st.selectbox('Date:', date_keys) # type: ignore
                else:
                    patient_id = 'None  - 0%'
                    date = 'None  - 0%'
                # select mapping option
                avail_idx = st.radio("Can this variable be mapped to our codebook?",
                                     range(len(mapping_options)),
                                     index=1,
                                     format_func=lambda x: mapping_options[x])  # returns index of options
                notes = st.text_input('Notes about this variable:', '')
                if enable_transformations:
                    if example_avail:
                        col3, col4 = st.columns(2)
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
                else:
                    transformation_instructions = None
                    transformation_type = None
                    source_dtype = None
                    target_dtype = None
                submitted = st.button(":green[Submit]", key='submit')
                if submitted:
                    # write mappings to results
                    _ = write_to_results(study, variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instructions, transformation_type, source_dtype, target_dtype, patient_id, date)
                    # sleep a few seconds to show results being written
                    time.sleep(0.2)
                    # I need to use session states, the above is a hack to fix death looping 
                    # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
                    del st.session_state['submit']
                    st.rerun()