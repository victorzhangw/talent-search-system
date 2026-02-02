import pandas as pd
import argparse
import os

def convert_xlsx_to_md(input_path, output_path):
    print(f"Reading from {input_path}...")
    try:
        xls = pd.ExcelFile(input_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {os.path.basename(input_path)}.md\n\n")

        for sheet_name in xls.sheet_names:
            print(f"Processing sheet: {sheet_name}...")
            f.write(f"## Sheet: {sheet_name}\n\n")
            
            # Read sheet
            df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
            
            # Handle NaN
            df = df.fillna('nan') # Keep consistent with v3 format which seemed to have 'nan' strings or empty.
            # Actually, v3 had some 'nan' strings in the example output I saw (e.g. dimension_group 'nan'). 
            # Better to use string 'nan' or empty string?
            # Looking at v3 file: 
            # | ANI_01 | ... | nan |
            # So 'nan' string is acceptable/expected.
            
            # Convert to markdown table
            # pandas to_markdown requires 'tabulate' usually, but let's check if we can do it simply or if tabulate is installed.
            # If tabulate is not installed, we can write a simple formatter.
            # Let's try df.to_markdown(index=False) first, catch error if tabulate missing.
            
            try:
                md_table = df.to_markdown(index=False)
                f.write(md_table)
            except ImportError:
                # Manual markdown conversion if tabulate missing
                headers = df.columns.tolist()
                f.write("| " + " | ".join(headers) + " |\n")
                f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
                for _, row in df.iterrows():
                    row_str = "| " + " | ".join(str(x).replace('\n', '<br>') for x in row.tolist()) + " |"
                    f.write(row_str + "\n")
            
            f.write("\n\n---\n\n")

    print(f"Done. Written to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel Spec to Markdown.")
    parser.add_argument("--input", required=True, help="Input .xlsx file path")
    parser.add_argument("--output", required=True, help="Output .md file path")
    args = parser.parse_args()

    convert_xlsx_to_md(args.input, args.output)
