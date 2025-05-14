import pandas as pd
import fsspec
from scipy import spatial
from dotenv import dotenv_values
from .util import init_llm_models

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def get_embedding(openai_client, text, model="text-embedding-ada-002"):
    """
    Generate an embedding for the given text using the specified OpenAI model.

    Args:
        openai_client: The OpenAI client instance.
        text (str): The text to generate an embedding for.
        model (str): The model to use for generating the embedding.

    Returns:
        list: The generated embedding.
    """
    text = str(text).replace("\n", " ")
    if openai_client:
        try:
            response = openai_client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating OpenAI embedding: {str(e)}")
    else:
        raise ValueError("No OpenAI client available. Please provide an OpenAI API key.")
    return None


def embed_codebook(openai_client):
    """
    Embed the codebook variables and descriptions using the OpenAI client and save the results.

    Args:
        openai_client: The OpenAI client instance.
    """
    if not fs.exists(f'{input_path}/target_variables_with_embeddings.csv'):
        df = pd.read_csv(f"{input_path}/target_variables.csv")
        df["var_embeddings"] = df['variable_name'].apply(lambda x: get_embedding(openai_client, x)) # type: ignore
        df["description_embeddings"] = df['description'].apply(lambda x: get_embedding(openai_client, x)) # type: ignore
        df.to_csv(f'{input_path}/target_variables_with_embeddings.csv', index=False)

def embed_study(openai_client, study):
    """
    Embed the study variables and descriptions using the OpenAI client and save the results.

    Args:
        openai_client: The OpenAI client instance.
        study (str): The study name.
    """
    df = pd.read_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv')[['variable_name','description']]
    df["var_embeddings"] = df['variable_name'].apply(lambda x: get_embedding(openai_client, x)) # type: ignore
    df["description_embeddings"] = df['description'].apply(lambda x: get_embedding(openai_client, x)) # type: ignore

    df.to_csv(f'{input_path}/{study}/dataset_variables_with_embeddings.csv', index=False)

def calculate_cosine_similarity(embedding1, embedding2):
    """
    Calculate the cosine similarity between two embeddings.

    Args:
        embedding1 (str): The first embedding.
        embedding2 (str): The second embedding.

    Returns:
        float: The cosine similarity between the two embeddings.
    """
    similarity = spatial.distance.cosine(eval(embedding1), eval(embedding2))
    return similarity
    
def generate_recommendations(study):

    """
    Generate recommendations for the given study based on cosine similarity of embeddings.

    Args:
        study (str): The study name.
    """

    study_df = pd.read_csv(f'{input_path}/{study}/dataset_variables_with_embeddings.csv')
    target_df = pd.read_csv(f'{input_path}/target_variables_with_embeddings.csv')
    recommendations = []
    distances = []
    for i in range(len(study_df)):
        study_var = study_df['var_embeddings'].iloc[i]
        target_df["var_distance"] = target_df['var_embeddings'].apply(lambda x: calculate_cosine_similarity(study_var, x)) # type: ignore
        study_desc = study_df['description_embeddings'].iloc[i]
        target_df["desc_distance"] = target_df['description_embeddings'].apply(lambda x: calculate_cosine_similarity(study_desc, x)) # type: ignore
        target_df["distance"] = (target_df["desc_distance"] * 0.8) + (target_df["var_distance"] * 0.2)
        target_df = target_df.sort_values("distance")
        recommendations.append(list(target_df.description))
        distances.append(list(target_df.distance))
    study_df['target_recommendations'] = recommendations
    study_df['target_distances'] = distances
    study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv', index = False)

def get_embeddings():
    """
    Generate embeddings for all available studies and the codebook.

    This function initializes the OpenAI client, embeds the codebook, and then
    iterates over all available studies to embed their variables and descriptions.
    """
    config = dotenv_values(".env")
    openai_client = init_llm_models(config)
    embed_codebook(openai_client)
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_embeddings.csv'):
            embed_study(openai_client, study)
        
def get_recommendations():
    """
    Generate recommendations for all available studies.

    This function iterates over all available studies and generates recommendations
    based on the cosine similarity of embeddings.
    """
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_recommendations.csv'):
            generate_recommendations(study)

def generate_PID_date_recommendations(openai_client, study):
    """
    Generate Index and date recommendations for the given study.

    Args:
        openai_client: The OpenAI client instance.
        study (str): The study name.
    """
    study_df = pd.read_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv')
    date_recommendations = []
    date_distances = []
    for i in range(len(study_df)):
        study_var = study_df['description'].iloc[i]
        date_embed = get_embedding(openai_client, f'Date of {study_var}')
        date_embed = str(date_embed) # need to convert to string so eval in cosine similarity func works
        study_df["date_distance"] = study_df['description_embeddings'].apply(lambda x: calculate_cosine_similarity(date_embed, x)) # type: ignore
        study_df_sorted = study_df.sort_values("date_distance")
        date_recommendations.append(list(study_df_sorted.variable_name))
        date_distances.append(list(study_df_sorted.date_distance))
    study_df['date_recommendations'] = date_recommendations
    study_df['date_distances'] = date_distances

    PID_recommendations = []
    PID_distances = []
    for i in range(len(study_df)):
        study_var = study_df['description'].iloc[i]
        PID_embed = get_embedding(openai_client, f'Unique Identifier of {study_var}')
        PID_embed = str(PID_embed) # need to convert to string so eval in cosine similarity func works
        study_df["PID_distance"] = study_df['description_embeddings'].apply(lambda x: calculate_cosine_similarity(PID_embed, x)) # type: ignore
        study_df_sorted = study_df.sort_values("PID_distance")
        PID_recommendations.append(list(study_df_sorted.variable_name))
        PID_distances.append(list(study_df_sorted.PID_distance))

    study_df['PID_recommendations'] = PID_recommendations
    study_df['PID_distances'] = PID_distances

    study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv', index = False)


def get_PID_date_recommendations():
    """
    Generate PID and date recommendations for all available studies.

    This function iterates over all available studies and generates PID and date
    recommendations based on the cosine similarity of embeddings.
    """
    config = dotenv_values(".env")
    openai_client = init_llm_models(config)
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv'):
            generate_PID_date_recommendations(openai_client, study)