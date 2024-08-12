def generate_descriptions_without_context():
    config = dotenv_values(".env")
    OpenAI_api_key = config['OpenAI_api_key']
    client = OpenAI(api_key = OpenAI_api_key)
    init_prompt = config['init_prompt']
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    print(avail_studies)
    # skip already done
    done = [x for x in avail_studies if fs.exists(f'{input_path}/{x}/dataset_variables_auto_completed.csv')]
    avail_studies = [x for x in avail_studies if x not in done]
    # only do if no context
    studies_without_context = [study for study in avail_studies if not fs.exists(f"{input_path}/{study}/context.txt")]
    print(studies_without_context)
    for study in studies_without_context:
        print(study)
        variables_df = pd.read_csv(f'{input_path}/{study}/dataset_variables.csv')

        to_do = []
        described = []
        for i in range(len(variables_df)):
            if not type(variables_df.iloc[i]['description']) == str:
                if math.isnan(variables_df.iloc[i]['description']):
                    to_do.append(variables_df.iloc[i]['variable_name'])
            else:
                described.append(variables_df.iloc[i]['variable_name'])
        
        if not len(to_do) > 0:
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv') # no need to autocomplete
        else:
            # Call openai API
            codebook = {}
            for var in to_do:
                prompts = return_prompt_no_context(init_prompt, var)
                llm_response = None
                try:
                    llm_response = client.chat.completions.create(model="gpt-3.5-turbo", messages=prompts)
                except:
                    time.sleep(1)
                    print('retry')
                    try:
                        llm_response = client.chat.completions.create(model="gpt-3.5-turbo", messages=prompts)
                    except:
                        llm_response = None
                        print('fail') # if all fail good chance the context length is too long
                if llm_response:
                    label = llm_response.choices[0].message.content # type: ignore
                    codebook[var] = ''.join(['*',label]) #add a * to indicate this description is AI generated
                time.sleep(0.1)

            for var in list(codebook):
                variables_df.loc[variables_df['variable_name'] == var,'description'] = codebook[var]

            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index = False)