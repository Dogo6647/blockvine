import tomllib

# might change the default data
default_toml = """launch-turbowarp-on-open = true
turbowarp-path = \"\" # Insert the path to your TurboWarp executable here."""

def settings() -> dict:
    toml_data = {}

    try:
        with open("blockvine.toml", "rb") as f:
            toml_data = tomllib.load(f)
        print("Settings file loaded successfully!")
    except FileNotFoundError:
        print("No settings file. Creating settings file.")
        file = open("blockvine.toml", "w")
        file.write(default_toml)
        file.close()

        with open("blockvine.toml", "rb") as f:
            toml_data = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        print("Settings file malformed. Recreating settings file.")
        file = open("blockvine.toml", "w")
        file.write(default_toml)
        file.close()

        with open("blockvine.toml", "rb") as f:
            toml_data = tomllib.load(f)


    
    return toml_data

if __name__ == "__main__":
    settings()