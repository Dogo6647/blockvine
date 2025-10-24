import json, os
from urllib.parse import unquote

def rebuild_json(path):
    """
    This reassembles jsonbreak directory structure into a single JSON file.
    (Basically, it does the same process but tries to reverse it)
    """
    print(f"rebuilding {path}")

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    entries = [e for e in os.listdir(path) if not e.startswith(".")]
    obj = {}

    index_path = os.path.join(path, "index.json")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            obj.update(json.load(f))

    for entry in entries:
        if entry == "index.json":
            continue

        full_path = os.path.join(path, entry)
        decoded_key = unquote(entry)

        if os.path.isdir(full_path):
            subentries = [e for e in os.listdir(full_path) if e.endswith(".json")]
            if all(e[:-5].isdigit() for e in subentries):
                arr = []
                for i in sorted(map(int, [e[:-5] for e in subentries])):
                    with open(os.path.join(full_path, f"{i}.json"), "r", encoding="utf-8") as f:
                        arr.append(json.load(f))
                obj[decoded_key] = arr
            else:
                obj[decoded_key] = rebuild_json(full_path)

        elif entry.endswith(".json"):
            key = unquote(entry[:-5])
            with open(full_path, "r", encoding="utf-8") as f:
                obj[key] = json.load(f)

    return obj
