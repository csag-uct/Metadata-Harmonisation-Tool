from openai import OpenAI # type: ignore
import streamlit as st

def init_llm_models(config):
    openai_client = None
    if 'OpenAI_api_key' in list(config):
        openai_client = OpenAI(api_key=config['OpenAI_api_key'])
    else:
        raise ValueError("No OpenAI API key found. Please provide an API key to proceed.")
    return openai_client

# map study utils below
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
        if st.session_state[f'{type_}_{study}'] != 'None':
            recommended_keys.insert(1, 'None  - 0%') # insert None at second position if a PID or date has previously been mapped
        else:
            recommended_keys.insert(0, 'None  - 0%')
    return recommended_keys

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