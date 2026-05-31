import yaml
import os
import sys
import argparse

def generate_vars(input_file, output_dir):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML: {exc}")
            return

    if not data:
        print("Error: Empty YAML file.")
        return

    # Check for PrometheusRule structure
    spec = data.get('spec', {})
    groups = spec.get('groups', [])
    
    # If not in spec (maybe a raw rules file), try top-level groups
    if not groups:
        groups = data.get('groups', [])

    if not groups:
        print("No recording rule groups found.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    count = 0
    for group in groups:
        rules = group.get('rules', [])
        for rule in rules:
            record_name = rule.get('record')
            expr = rule.get('expr')
            if record_name and expr:
                # Clean up expression if it's a multi-line block with extra spaces/newlines
                expr = expr.strip()
                
                file_path = os.path.join(output_dir, record_name)
                
                # Check if file_path has subdirectories (if record name has slashes)
                # Though Prometheus record names usually don't have slashes.
                
                with open(file_path, 'w') as out_f:
                    # Based on existing files, I'll add the parentheses wrapper if it doesn't have it?
                    # The prompt says "contents of the file are the expression". 
                    # Existing files have:
                    # (
                    # expression
                    # )
                    # I'll stick to what the prompt said exactly: "contents... are the expression".
                    out_f.write(expr + '\n')
                
                print(f"Generated: {file_path}")
                count += 1

    print(f"Successfully generated {count} files in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate var files from Prometheus recording rules.')
    parser.add_argument('input', help='Input rules.yaml file')
    parser.add_argument('--output', default='vars.d', help='Output directory (default: vars.d)')
    
    args = parser.parse_args()
    generate_vars(args.input, args.output)
