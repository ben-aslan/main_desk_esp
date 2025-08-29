import ujson

def save_config(config):
    with open("config.json", "w") as f:
        ujson.dump(config, f)

def load_config():
    try:
        with open("config.json", "r") as f:
            return ujson.load(f)
    except OSError:
        return {}