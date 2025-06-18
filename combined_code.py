import os

output_file = "combined_code.txt"
excluded_files = {
    "build_installer.py",
    "combined_py.py",
    "interface.py",
    "nuitka_build_installer.py",
    "realtime_effects.py",
    "test.py",
}

included_files = []

with open(output_file, "w", encoding="utf-8") as outfile:
    for file in os.listdir("."):
        if file.endswith(".py") and file not in excluded_files:
            included_files.append(file)
            with open(file, "r", encoding="utf-8") as infile:
                outfile.write(f"\n\n# --- {file} ---\n")    
                outfile.write(infile.read())

print(f"✅ Combined .py files into '{output_file}'")
print("🗂️ Archivos incluidos:")
for f in included_files:
    print(f" - {f}")
