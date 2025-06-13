import os

output_file = "combined_code.txt"
current_script = os.path.basename(__file__)
with open(output_file, "w", encoding="utf-8") as outfile:
    for file in os.listdir("."):
        if file.endswith(".py") and file != current_script:
            with open(file, "r", encoding="utf-8") as infile:
                outfile.write(f"\n\n# --- {file} ---\n")
                outfile.write(infile.read())
print(f"Combined .py files into {output_file}")