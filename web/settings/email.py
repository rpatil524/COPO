# settings for automatic email
from tools import resolve_env
mail_username = resolve_env.get_env('MAIL_USERNAME')
mail_password = resolve_env.get_env('MAIL_PASSWORD')
mail_server = resolve_env.get_env('MAIL_SERVER')
mail_server_port = resolve_env.get_env('MAIL_PORT')
mail_address = resolve_env.get_env('MAIL_ADDRESS')