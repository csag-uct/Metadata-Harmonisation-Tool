import pandas as pd
import fsspec
import openai


def get_embedding(str, engine="text-similarity-davinci-001", **kwargs):
    text = text.replace("\n", " ")
    return openai.Embedding.create(input=[text], engine=engine, **kwargs)["data"][0]["embedding"]

from scipy import spatial

from dotenv import dotenv_values

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def embed_codebook():
    config = dotenv_values(".env")
    OpenAI_api_key = config['OpenAI_api_key']
    openai.api_key = OpenAI_api_key
    embedding_model = "text-embedding-ada-002"
    if not fs.exists(f'{input_path}/target_variables_with_embeddings.csv'):
        df = pd.read_csv(f"{input_path}/target_variables.csv")
        df = df[['variable_name','description']]
        df["var_embeddings"] = df['variable_name'].apply(lambda x: get_embedding(x, engine=embedding_model))
        df["description_embeddings"] = df['description'].apply(lambda x: get_embedding(x, engine=embedding_model))
        df.to_csv(f'{input_path}/target_variables_with_embeddings.csv', index=False)

def embed_study(study):
    config = dotenv_values(".env")
    OpenAI_api_key = config['OpenAI_api_key']
    openai.api_key = OpenAI_api_key
    embedding_model = "text-embedding-ada-002"
    df = pd.read_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv')[['variable_name','description']]
    df["var_embeddings"] = df['variable_name'].apply(lambda x: get_embedding(x, engine=embedding_model))
    df["description_embeddings"] = df['description'].apply(lambda x: get_embedding(x, engine=embedding_model))
    df.to_csv(f'{input_path}/{study}/dataset_variables_with_embeddings.csv', index=False)

def calculate_cosine_similarity(embedding1, embedding2):
    similarity = spatial.distance.cosine(eval(embedding1), eval(embedding2))
    return similarity
    
def generate_recommendations(study):
    config = dotenv_values(".env")
    OpenAI_api_key = config['OpenAI_api_key']
    openai.api_key = OpenAI_api_key
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
    study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_recommendations', index = False)

def get_embeddings():
    embed_codebook()
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_embeddings.csv'):
            embed_study(study)

def get_recommendations():
    embed_codebook()
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_recommendations'):
            generate_recommendations(study)





