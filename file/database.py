# This is a standalone script that is run via command line execution. Arguments are passed from the command line.
# Requires that any file this script is run on exists in the MeshProperties.json

import sys
import json
import sqlite3

textools    = sys.argv[1]
file_name   = sys.argv[2]
props_path  = sys.argv[3]

with open(props_path, "r") as file:
    model_props:dict[str, dict[str, dict[str, str]]] = json.load(file)

database = rf"{textools}\converters\fbx\result.db"

conn = sqlite3.connect(f"{database}")
cursor = conn.cursor() 

for mesh_name, attr in model_props[file_name]["attributes"].items():
    if attr == "":
        continue
    cursor.execute(f"UPDATE parts SET attributes = '{attr}' WHERE name = '{mesh_name}'")

for mesh_id, material in model_props[file_name]["materials"].items():
    cursor.execute(f"INSERT INTO materials (material_id, name) VALUES ({mesh_id}, '{material}')")
    cursor.execute(f"UPDATE meshes SET material_id = {mesh_id} WHERE mesh = {mesh_id}")

conn.commit()
