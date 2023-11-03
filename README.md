# Metadata Harmonisation Tool

This is a simple [streamlit](https://streamlit.io) application we have constructed that facilitates the matching of variables in the incoming dataset studies to your project’s codebook (which will also be known as target variables).

Currently, it also contains a general template/example being used by the [HE2AT Centre](https://heatcenter.wrhi.ac.za) data harmonisation team, here using the [CINECA synthetic cohort Africa H3ABioNet v1](https://www.cineca-project.eu/synthetic-data/sdc-africa-h3abionet-v1) dataset as an example.


## General work flow:

### Initialise:

If you do not have a preferred python package manager already installed I recommend installing [Micromamba](https://mamba.readthedocs.io/en/latest/micromamba-installation.html#)

```
git clone git@github.com:csag-uct/Health_Data_Harmonisation_Platform.git

cd Health_Data_Harmonisation_Platform


conda env create -f environment.yml -c conda-forge
conda activate harmonisation_env

pip install -r requirements.txt # some packages not available on conda channels

cd app/

streamlit run mapping_interface.py
```

This should automatically open your browser to this page:

![GUI screenshot](GUI.png)


User Interface Instructions copied below:

# Metadata Harmonisation Tool]

This is a simple [streamlit](https://streamlit.io) application we have constructed that facilitates the matching of variables variables names in a dataset to a of target codebook. The first and often most tedious step in developping a common data model. 

### General work flow:

#### Step 1: Upload Target Codebook

This platform is built to harmonise incoming datasets to a single set of target_variables (codebook). An example codebook is included by default. A new codebook can be uploaded under the `Upload Codebook` tab. New codebooks should be in `.csv` format and contain two columns `variable_name` and `description`. It is recommended (but not need for this tool) that these variables be linked to standardised ontologies. 

#### Step 2: Upload Incoming Datasets

From here incoming study data whichs need to be mapped to the target codebook can be uploaded. The following documents can be uploaded: 

 - Study Name (required)
 - Study Description (optional)
 - Variables Table (required)
    - File Format: .csv
    - File Contains: variable names or descriptions from the incoming dataset
    - 2 columns with headers: variable_name, description
  - Example_data (optional)
    - File Format: .csv
    - column headers should correspond to variable name in the dataset variables table.
  - Contextual Documents (optional)
    - File Format: .pdf
    - If the uploaded variables table contains missing variable descriptions a large language model will be used to populate the descriptions. Uploading a study protocol or some other relevant documentation can help inhance this process. 

#### Step 3: Initialise Tool

Once studies have been uploaded you can run the variable description completion and ontology recomendation engines. You will be prompted to upload an OpenAI API key and given the option to fine tune the LLM propt used by the description completion engine.

#### Step 3: Map Datasets to Codebook

Once step 1 & 2 have been completed a recommendations algorithm will suggest the most likely variable mappings for each added dataset. The user will be presented with an interface to select the correct mappings from a list of suggested mappings. Thus the actual mapping process remains manual. 

#### Step 4: Download Mapping Results

Once the mapping process has been completed. Each study that has been fully mapped will be available for download as a .csv file. The mapping result is simply a table mapping each dataset variable name to a corresponding codebook variable name. 





This work is licensed under a
[Creative Commons Attribution-ShareAlike 4.0 International License][cc-by-sa].  [![CC BY-SA 4.0][cc-by-sa-image]][cc-by-sa]

[cc-by-sa]: http://creativecommons.org/licenses/by-sa/4.0/
[cc-by-sa-image]: https://licensebuttons.net/l/by-sa/4.0/88x31.png
[cc-by-sa-shield]: https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg
