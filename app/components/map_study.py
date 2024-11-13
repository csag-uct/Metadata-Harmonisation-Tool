import streamlit as st
import pandas as pd
import fsspec
import duckdb
import time
import numpy as np
from dotenv import dotenv_values
from .generate_transformations import generate_transformations
from .transformation_utils import generic_direct_conversion, generic_catagorical_conversion
from .util import split_var_confidence, format_example_data, add_to_session_state, pre_process_recomendations

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

if 'transformation_instructions' not in st.session_state:
    st.session_state.transformation_instructions = {}


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

def test_transformation(example_data, transformation_type, transformation_instructions, source_dtype, target_dtype):
    """
    Runs the transformation instructions on the example data. And displays the results.

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
    config = dotenv_values(".env")

    if 'auto_transform_available' in list(config):
        auto_transform_available = config['auto_transform_available']
    else:
        auto_transform_available = 'no'

    if auto_transform_available == 'yes':
        codebook = pd.read_csv(f'{input_path}/target_variables.csv')
    
    if study == None:
        st.write(':red[No studies available, please initialise the mapping app]')
    else:
        transformation_instruction = None
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
                if enable_transformations and example_avail:
                    # Initialize the transformation instructions dictionary if it doesn't exist
                    if 'transformation_instructions' not in st.session_state:
                        st.session_state.transformation_instructions = {}

                    codebook_var, codebook_conf = split_var_confidence(mapped_variable)
                    
                    if codebook_conf:
                        codebook_conf = int(codebook_conf[:-1])
                    else:
                        codebook_conf = 0
                    
                    dtype_options = ['float', 'integer', 'string', 'boolean']
                    if auto_transform_available == 'yes':
                        codebook_var_df = codebook[codebook['description'] == codebook_var]
                        value = codebook_var_df.Categories.item()
                        if isinstance(value, float) and np.isnan(value): # direct
                            transformation_type_idx = 0 
                            dtype = codebook_var_df.dType.item()
                            if variable_to_map not in st.session_state.transformation_instructions:
                                st.session_state.transformation_instructions[variable_to_map] = 'x'
                            try:
                                target_dtype_idx = dtype_options.index(dtype)
                            except:
                                target_dtype_idx = 0
                        else: # categorical
                            transformation_type_idx = 1
                            if variable_to_map not in st.session_state.transformation_instructions:
                                st.session_state.transformation_instructions[variable_to_map] = '{}'
                        generate_instructions = st.button('Auto Generate Transformation Instructions', key='generate')
                        if generate_instructions:
                            st.session_state.transformation_instructions[variable_to_map] = generate_transformations(split_var_confidence(mapped_variable)[0], variable_to_map, example_data, st.session_state.transformation_instructions.get(variable_to_map, ''), codebook_var_df)
                    else:
                        generate_instructions = st.button('Auto Generate Transformation Instructions', key='generate', disabled=True, help='Auto transformations are not available for this study as the target codebook does not contain dType, Unit, Categories, or Unit Example columns.')
                        transformation_type_idx = 0
                        if variable_to_map not in st.session_state.transformation_instructions:
                            st.session_state.transformation_instructions[variable_to_map] = 'x'
                        target_dtype_idx = 0

                    col3, col4 = st.columns(2)
                    with col3:
                        transformation_instruction_final = st.text_input('Transformation instructions for this variable:', st.session_state.transformation_instructions.get(variable_to_map, ''), key='transformation_input')
                        st.session_state.transformation_instructions[variable_to_map] = transformation_instruction_final
                        transformation_types = ['Direct', 'Categorical']
                        transformation_type = st.selectbox('Type of transformation applied to this variable:', transformation_types, index=transformation_type_idx)
                        if transformation_type == 'Direct':
                            source_dtype = st.selectbox('Source data type:', dtype_options)
                            target_dtype = st.selectbox('Target data type:', dtype_options, index=target_dtype_idx)
                        else:
                            source_dtype = None
                            target_dtype = None
                    
                    with col4:
                        test_transformation(example_data, transformation_type, transformation_instruction_final, source_dtype, target_dtype)
                        if st.session_state.get('transformation_input') != st.session_state.get('last_transformation_input'):
                            st.session_state['last_transformation_input'] = st.session_state.get('transformation_input')
                    transformation_instruction = st.session_state.transformation_instructions.get(variable_to_map, None)
                else:
                    transformation_instruction = None
                    transformation_type = None
                    source_dtype = None
                    target_dtype = None
                submitted = st.button(":green[Submit]", key='submit')
                if submitted:
                    # write mappings to results
                    _ = write_to_results(study, variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instruction, transformation_type, source_dtype, target_dtype, patient_id, date)
                    transformation_instruction = None
                    # sleep a few seconds to show results being written
                    time.sleep(0.2)
                    # I need to use session states, the above is a hack to fix death looping, but also this is vagualy equivalant to repaint in react which is what I want
                    # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
                    del st.session_state['submit']
                    st.rerun()