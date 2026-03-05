import json
import os

FLAGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'feature_flags.json')


def is_enabled(flag_name):
    try:
        with open(FLAGS_PATH) as f:
            flags = json.load(f)
        return flags.get(flag_name, False)
    except Exception:
        return False


def load_all():
    try:
        with open(FLAGS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}
