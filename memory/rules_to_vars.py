#!/usr/bin/env python3
import yaml
import os
import sys
import argparse

def get_rules_from_doc(doc):
    """Helper to extract rule list from a PrometheusRule or raw rule document."""
    if not doc:
        return None
    spec = doc.get('spec', {})
    groups = spec.get('groups', [])
    if not groups:
        groups = doc.get('groups', [])
    return groups

def export_rules(input_file, output_dir):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r') as f:
        try:
            docs = list(yaml.safe_load_all(f))
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML: {exc}")
            return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    count = 0
    for doc in docs:
        groups = get_rules_from_doc(doc)
        if not groups:
            continue

        for group in groups:
            rules = group.get('rules', [])
            for rule in rules:
                record_name = rule.get('record')
                expr = rule.get('expr')
                if record_name and expr:
                    expr = expr.strip()
                    file_path = os.path.join(output_dir, record_name)
                    with open(file_path, 'w') as out_f:
                        out_f.write(expr + '\n')
                    print(f"Exported: {record_name} -> {file_path}")
                    count += 1

    print(f"Successfully exported {count} rules to {output_dir}")

def import_rules(input_dir, yaml_file):
    if not os.path.exists(yaml_file):
        print(f"Error: {yaml_file} not found.")
        return
    if not os.path.exists(input_dir):
        print(f"Error: {input_dir} not found.")
        return

    # Load all files in input_dir
    expr_map = {}
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path) and not filename.startswith('.'):
            with open(file_path, 'r') as f:
                expr_map[filename] = f.read().strip()

    if not expr_map:
        print(f"No valid rule files found in {input_dir}")
        return

    with open(yaml_file, 'r') as f:
        try:
            # We use full_load to handle complex YAML if any, though safe_load is usually enough
            docs = list(yaml.safe_load_all(f))
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML: {exc}")
            return

    updated_count = 0
    for doc in docs:
        groups = get_rules_from_doc(doc)
        if not groups:
            continue

        for group in groups:
            rules = group.get('rules', [])
            for rule in rules:
                record_name = rule.get('record')
                if record_name in expr_map:
                    rule['expr'] = expr_map[record_name]
                    print(f"Updated: {record_name}")
                    updated_count += 1

    if updated_count > 0:
        with open(yaml_file, 'w') as f:
            yaml.dump_all(docs, f, sort_keys=False, default_flow_style=False, width=1000)
        print(f"Successfully updated {updated_count} rules in {yaml_file}")
    else:
        print("No matching rules found to update.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage Prometheus recording rules via files.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export recording rules from YAML to files')
    export_parser.add_argument('input', help='Input rules.yaml file')
    export_parser.add_argument('--output', default='vars.d', help='Output directory (default: vars.d)')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import expressions from files into YAML rules')
    import_parser.add_argument('input_dir', help='Directory containing rule files')
    import_parser.add_argument('yaml_file', help='Target rules.yaml file to update')

    args = parser.parse_args()

    if args.command == 'export':
        export_rules(args.input, args.output)
    elif args.command == 'import':
        import_rules(args.input_dir, args.yaml_file)
    else:
        parser.print_help()
