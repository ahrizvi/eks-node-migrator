from dotenv import load_dotenv
from distutils.util import strtobool
import os
load_dotenv('{}/.env'.format(os.getcwd()))


def str_to_bool(val):
    return val if type(val) is bool else bool(strtobool(val))


app_config = {
    'BETWEEN_NODES_WAIT': int(os.getenv('BETWEEN_NODES_WAIT', 0)),
    'DRY_RUN': str_to_bool(os.getenv('DRY_RUN', False)),
    'EXTRA_DRAIN_ARGS': os.getenv('EXTRA_DRAIN_ARGS', '').split()
}
