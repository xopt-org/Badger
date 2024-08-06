import yaml
import os
from pydantic import BaseModel

def generate_config(template_model: BaseModel, config_path: str):
    """
    Creates or updates a config file from a Pydantic model as the template.
    
    Parameters
    ----------
    template_model: BaseModel
        Pydantic model instance to use as the template.
    config_path: str
        Path to the user config file.
    """
    template_data = template_model.dict(by_alias=True)
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as user_file:
            config_data = yaml.safe_load(user_file) or {}
        
        for key, value in template_data.items():
            if key not in config_data:
                config_data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in config_data[key]:
                        config_data[key][sub_key] = sub_value
    else:
        config_data = template_data
    
    with open(config_path, 'w') as user_file:
        yaml.dump(config_data, user_file, default_flow_style=False)
    
    print(f'User configuration written to {config_path}')

