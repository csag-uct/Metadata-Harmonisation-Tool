# :blue[Metadata Harmonisation Tool]

This is a simple [streamlit](https://streamlit.io) application we have constructed that facilitates the matching of variables variables names in a dataset to a of target codebook. The first and often most tedious step in developping a common data model. 

### :blue[General work flow:]

#### :blue[Step 1: Upload Target Codebook]

This platform is built to harmonise incoming datasets to a single set of target_variables (codebook). An example codebook is included by default. A new codebook can be uploaded under the `Upload Codebook` tab. New codebooks should be in `.csv` format and contain two columns `variable_name` and `description`. It is recommended (but not needed for this tool) that these variables be linked to standardised ontologies. 

#### :blue[Step 2: Upload Incoming Datasets]

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

#### :blue[Step 3: Map Datasets to Codebook]

Once step 1 & 2 have been completed a recommendations algorithm will suggest the most likely variable mappings for each added dataset. The user will be presented with an interface to select the correct mappings from a list of suggested mappings. Thus the actual mapping process remains manual. 

#### :blue[Step 4: Download Mapping Results]

Once the mapping process has been completed. Each study that has been fully mapped will be available for download as a .csv file. The mapping result is simply a table mapping each dataset variable name to a corresponding codebook variable name. 