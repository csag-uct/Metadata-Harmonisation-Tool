# Metadata Harmonisation Tool

This is a simple [streamlit](https://streamlit.io) application we have constructed that facilitates the matching of variables in the incoming dataset studies to your project’s codebook (which will also be known as target variables).

Currently, it also contains a general template/example being used by the [HE2AT Centre](https://heatcenter.wrhi.ac.za) data harmonisation team, here using the [CINECA synthetic cohort Africa H3ABioNet v1](https://www.cineca-project.eu/synthetic-data/sdc-africa-h3abionet-v1) dataset as an example.


## General work flow:

### Initialise:

This repository is intended to form the foundation of a jupyter lab based data science platform. To configure this on your local machine follow these instructions:

```
git clone git@github.com:csag-uct/Health_Data_Harmonisation_Platform.git
cd Health_Data_Harmonisation_Platform

conda create --name health_harmonisation
conda activate health_harmonisation
conda install --file requirements.txt

jupyter lab
```

### Step 1: Adding Target_Variables Codebook 

This platform is built to harmonise incoming datasets to a single set of target_variables (codebook). An example codebook is included in this repository at `app/input/target_variables.csv`. In this step, add your target_variables codebook as to `app/input/target_variables.csv`. 



The semi-automated process of mapping incoming dataset variables to this codebook, outlined in this repo, utilises a [text-embedding](https://platform.openai.com/docs/guides/embeddings/what-are-embeddings) approach. 

In Step 3, the notebook located at `app/preprocess/get_recommendations.ipynb` is used to fetch embedding vectors from OpenAI - there is a nominal cost involved in this process. Embedding vectors for the target_variables are saved in `app/preprocess/output/target_variables_with_embeddings.csv`. 



### Step 2: Adding Incoming Dataset Files to Input Folder

From here incoming dataset files are expected to be placed into the `app/input/{dataset}` folder. Where `{dataset}` is the codename used for respective datasets going forward. There are three files which must be included into this folder. 

- dataset_variables.csv
- example_data.csv 
- description.txt (optional) 

Dataset_variables
- File Format: .csv
- File Contains: variable names or descriptions from the incoming dataset
2 columns with headers: variable_name, description
- File Generation: Manual

Example_data
- File Format: .csv
- File Contains: 10 rows of data from dataset, including a variety of values 
- File Generation: ‘Generate_synthetic_data’ script or manual (first 10 rows of data) 

Description File (Optional)
- File Format: .txt; markdown
- File Contains: project name, project description
- File Generation: Manual or from Trello

If no optional description file is provided, then the `{dataset}` name is used, where `{dataset}` is the folder name in `app/input/{dataset}`

Both dataset_variables and example_data are used as the inputs into `get_recommendations.ipynb`


### Step 3: Pre-Processing with `get_recommendations.ipynb` 

The notebook at `/app/preprocess/get_recommendations.ipynb` is used to fetch embedding vectors for the dataset variables and target variables. Dataset Variables with embedding vectors are saved as `/app/preprocess/output/{dataset}_variables_with_embeddings.csv`. Target Variables with embedding vectors are saved as `/app/preprocess/output/target_variables_with_embeddings.csv` 

The target_variable_embeddings is only generated if it doesn't already exist {delete file to force re-run}. 

The cosine_similarity between the dataset variables and target variables is calculated, and codebook variables are ranked from most to least similar for each incoming dataset variable. This is saved as `/app/preprocess/output/{dataset}_variables_with_recommendations.csv`. 



### Step 4 / TL;DR:

Once the above has been completed the mapping GUI is ready to be used. (These have already been completed in this example repo). To run the GUI follow these instructions:

```
cd app/
streamlit run Home.py
```

This should automatically open your browser to this page:

![GUI screenshot](GUI.png)

### step 5:
Work in progress. 

The intention is that the GUI can be used to create data pipelines that extract and convert mapped variables from the standardised study files to a single harmonised dataset. 


This work is licensed under a
[Creative Commons Attribution-ShareAlike 4.0 International License][cc-by-sa].  [![CC BY-SA 4.0][cc-by-sa-image]][cc-by-sa]

[cc-by-sa]: http://creativecommons.org/licenses/by-sa/4.0/
[cc-by-sa-image]: https://licensebuttons.net/l/by-sa/4.0/88x31.png
[cc-by-sa-shield]: https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg
