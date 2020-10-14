# settings for automatic email
from tools import resolve_env
mail_username = resolve_env.get_env('mail_username')
mail_password = resolve_env.get_env('mail_password')
mail_server = 'outlook.office365.com'
mail_server_port = 587
mail_address = "data@earlham.ac.uk"