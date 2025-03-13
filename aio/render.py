import yaml
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

# Load the configuration data
with open('config.yml', 'r') as file:
    config_data = yaml.safe_load(file)

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('main.j2')

# Render the configuration
output = template.render(**config_data)

# Save the output
with open('switch_config.txt', 'w') as file:
    file.write(output)
