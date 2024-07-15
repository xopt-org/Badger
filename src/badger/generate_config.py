import yaml
import os

def generate_config(template_path: str, config_path: str):
    """
    Creates or updates a config file from badger's template config file.
    
    Parameters
    ----------
    template_path: str
        path to the template config file
    user_config_path: str
        path to the config file 

    """
    with open(template_path, 'r') as template_file:
        template_data = yaml.safe_load(template_file)
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as user_file:
            config_data = yaml.safe_load(user_file)
        
        for key, value in template_data.items():
            if key not in config_data:
                config_data[key] = value
    else:
        config_data = template_data
    
    with open(config_path, 'w') as user_file:
        yaml.dump(config_data, user_file, default_flow_style=False)
    
    print(f'User configuration written to {config_path}')

