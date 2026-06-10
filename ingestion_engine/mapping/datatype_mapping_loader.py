import csv


class DataTypeMappingLoader:

    def __init__(self, filepath):
        self.filepath = filepath

    def load(self):
        mapping = {}
        with open(self.filepath, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = (row["source_type"].lower(), row["target_type"].lower())
                mapping[key] = row["cast_template"]
        #         print(f"Loaded mapping: {key} → {row['cast_template']}")
        # print(f"mappings loaded: {mapping}")
        return mapping