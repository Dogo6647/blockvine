import json, os
from urllib.parse import quote

def disassemble_json(data, path, *, split_arrays=True):
    """
    This recursively disassembles JSON data into files/folders.
    It only splits direct (parent) arrays as individual JSONs.
    Nested arrays inside dicts are kept inline in index.json.
    """
    os.makedirs(path, exist_ok=True)
    plain_values = {}

    for key, value in data.items():
        encoded_key = quote(str(key), safe="")

        if isinstance(value, dict):
            subdir = os.path.join(path, encoded_key)
            disassemble_json(value, subdir, split_arrays=True)

        elif isinstance(value, list) and split_arrays:
            list_dir = os.path.join(path, encoded_key)
            os.makedirs(list_dir, exist_ok=True)

            for i, item in enumerate(value):
                item_file = os.path.join(list_dir, f"{i}.json")
                with open(item_file, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2)

        else:
            plain_values[key] = value

    if plain_values:
        with open(os.path.join(path, "index.json"), "w", encoding="utf-8") as f:
            json.dump(plain_values, f, indent=2)
