# Metadata Harmonisation Tool

This is a [streamlit](https://streamlit.io) application we have constructed that facilitates the matching of variables variables names in a dataset to that of a target codebook. The first and often most tedious step in developping a common data model. 

#### <span style="color:red">A video demonstration is avaliable [here](https://drive.google.com/file/d/1fLhKLtDvA_02pvjJYkFjXyDobZA4Y6V8/view?usp=sharing)</span>

## What it does:

The Metadata Harmonisation Interface provides a convenient portal to match variables from an incoming dataset to a target set of ontologies. In this way the tool provides a similar role to that of the [White Rabbit tool](https://github.com/OHDSI/WhiteRabbit) utilised by the OHDSI community. This tool differentiates itself by using Large Language Models to generate variable descriptions where none have been provided and by recommending the most likely target variable to map to. A confidence indication is provided alongside mapping recommendations. This dramatically speeds up the mapping process.

## How it works:
The Metadata Harmonisation Interface compromises of two key parts:

First the LLM-based description generator provides a way to quickly and easily extract variable description information from complex free text documents such as study protocols or journal articles. While in an ideal world descriptions should come from a codebook and should match to standardised ontologies, in our experience this is often not the case. The description generator works by taking in a PDF document and converting it to plain text using the pdfminer python package. Next, we use a text-splitter from the Llangchain suite of python functions.  This works by recursively  splitting the text by the special characters: "\n\n", "\n", " ” and "” until a text length of 1000 characters is reached. An overlap of 20 character between chunks is preserved to ensure no information is lost between chunks. A text embedding model is then used to get a vector representation of each chunk. This information is stored as a simple Numpy array.  Next a prompt is constructed by taking an already completed variable and description pair and retrieving the most relevant context, calculated as the spatial distance between the chunk embeddings and the variable name embedding. A hard coded variable and description pair alongside the least relevant context is also included with a (?) appended to the description. This is an attempt to get the LLM to return some indication of whether the context has been useful. The prompt template is shown above in figure 3.  This prompt style is known as few-shot prompting. If no context is provided by the user a similar prompt pattern is followed without providing the LLM with context. 

The next step in the process is the ontology recommendation engine. This again uses text embeddings to retrieve vector representations of variable names and descriptions for both the target codebook and incoming datasets. Recommendations are then calculated using the spatial distance between vectors weighted 80/20 to descriptions. The interface utilises DuckDB to retrieve these recommendations from plain csv files. 


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
