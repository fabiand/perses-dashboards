#!/usr/bin/env python3
import sys, yaml, requests, subprocess, json
from flask import Flask, request, Response

THANOS = "https://thanos-querier-openshift-monitoring.apps.cnv2.engineering.redhat.com"
TOKEN = subprocess.run(['oc', 'whoami', '-t'], capture_output=True, text=True).stdout.strip()

app = Flask(__name__)

def load_rules():
    """Load recording rules with their labels"""
    rules = []
    with open('rules.yaml') as f:
        for group in yaml.safe_load(f)['spec']['groups']:
            for rule in group['rules']:
                if 'record' in rule:
                    rules.append({
                        'name': rule['record'],
                        'labels': rule.get('labels', {}),
                        'expr': rule['expr'].strip()
                    })
    return rules

def rewrite(query):
    """Match metric name + labels, then replace with expression"""
    import re
    rules = load_rules()

    # Check if query contains a bare recording rule metric (without labels)
    for rule in rules:
        metric = rule['name']
        # Match bare metric at word boundary, not followed by {
        bare_pattern = rf'\b{re.escape(metric)}\b(?!\{{)'
        if re.search(bare_pattern, query):
            # Found bare metric - check if there are multiple variants
            variants = [r for r in rules if r['name'] == metric]
            if len(variants) > 1:
                # Multiple variants exist - error
                label_sets = []
                for v in variants:
                    labels_str = ', '.join(f'{k}="{v["labels"][k]}"' for k in sorted(v['labels'].keys()) if k not in ['unit', 'DevelopmentPreview'])
                    label_sets.append(f"  {metric}{{{labels_str}}}")

                error_msg = f"Metric '{metric}' requires labels. Available variants:\n" + "\n".join(label_sets)
                raise ValueError(error_msg)

    # For each rule, try to find and replace metric{labels} with its expression
    for rule in rules:
        metric = rule['name']
        rule_labels = rule['labels']
        expr = rule['expr']

        if metric not in query:
            continue

        # Find metric{...} pattern in query
        pattern = rf'{re.escape(metric)}\{{([^}}]+)\}}'
        match = re.search(pattern, query)

        if not match:
            continue

        query_label_str = match.group(1)

        # Parse query labels into dict
        query_labels = {}
        for part in query_label_str.split(','):
            if '=' in part:
                k, v = part.strip().split('=', 1)
                query_labels[k.strip()] = v.strip().strip('"')

        # Check if query labels match rule labels (subset match)
        # Query labels must all be present in rule labels with same values
        matches = all(
            rule_labels.get(k) == v
            for k, v in query_labels.items()
        )

        if matches:
            # Replace this occurrence
            query = query.replace(match.group(0), f'({expr})', 1)
            break

    return query

def make_error_response(error_msg):
    """Create Prometheus-compatible error response"""
    return Response(
        json.dumps({
            'status': 'error',
            'errorType': 'bad_data',
            'error': error_msg
        }),
        status=400,
        headers={'Content-Type': 'application/json'}
    )

def proxy_request(endpoint, method='GET'):
    """Proxy request to Thanos, rewriting queries if needed"""
    # Debug logging
    import sys

    # Extract query and params from request
    # POST can have params in URL query string, form data, or JSON body
    query = ''
    url_params = {}  # Only for GET
    body_params = {}  # Only for POST

    if method == 'GET':
        query = request.args.get('query', '')
        url_params = request.args.to_dict(flat=False)  # Keep multiple values for match[]
        # Flatten single-value lists
        url_params = {k: v[0] if len(v) == 1 else v for k, v in url_params.items()}
    else:  # POST
        # For POST, collect params from form/JSON (NOT URL params to avoid header size limits)
        if request.is_json and request.json:
            json_data = request.json
            body_params = dict(json_data)
            query = json_data.get('query', '')
        elif request.form:
            body_params = request.form.to_dict(flat=False)
            # Flatten single-value lists
            body_params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in body_params.items()}
            query = request.form.get('query', '')
        else:
            # Fallback: check URL params
            body_params = request.args.to_dict(flat=False)
            body_params = {k: v[0] if len(v) == 1 else v for k, v in body_params.items()}
            query = request.args.get('query', '')

    # Debug output
    print(f"{method} /api/v1/{endpoint}", file=sys.stderr)
    if query:
        print(f"  Query: {query[:100]}...", file=sys.stderr)

    # Only rewrite on query/query_range endpoints
    if endpoint in ['query', 'query_range'] and query:
        try:
            rewritten_query = rewrite(query)
            if rewritten_query != query:
                print(f"  Rewritten: {rewritten_query[:100]}...", file=sys.stderr)
            query = rewritten_query
            if method == 'GET':
                url_params['query'] = query
            else:
                body_params['query'] = query
        except ValueError as e:
            print(f"  Error: {e}", file=sys.stderr)
            return make_error_response(str(e))

    # Forward to Thanos
    url = f"{THANOS}/api/v1/{endpoint}"
    headers = {'Authorization': f'Bearer {TOKEN}'}

    if method == 'GET':
        # For large queries, switch to POST to avoid header size limits
        query_str = str(url_params.get('query', ''))
        if len(query_str) > 4000:  # If query is large, use POST instead
            print(f"  Warning: Query too large for GET ({len(query_str)} chars), switching to POST", file=sys.stderr)
            r = requests.post(url, data=url_params, headers=headers, verify=False)
        else:
            r = requests.get(url, params=url_params, headers=headers, verify=False)
    else:  # POST
        # Send as form-encoded data in the body (NOT URL params)
        # This avoids "header line too long" errors
        r = requests.post(url, data=body_params, headers=headers, verify=False)

    print(f"  Response: {r.status_code}, {len(r.content)} bytes", file=sys.stderr)

    # Ensure Content-Type is preserved from Thanos response
    response_headers = dict(r.headers)
    if 'Content-Type' not in response_headers:
        response_headers['Content-Type'] = 'application/json'

    return Response(r.content, r.status_code, response_headers)

# Perses-required endpoints
@app.route('/api/v1/query', methods=['GET', 'POST'])
def query():
    return proxy_request('query', request.method)

@app.route('/api/v1/query_range', methods=['GET', 'POST'])
def query_range():
    return proxy_request('query_range', request.method)

@app.route('/api/v1/labels', methods=['GET', 'POST'])
def labels():
    return proxy_request('labels', request.method)

@app.route('/api/v1/series', methods=['GET', 'POST'])
def series():
    return proxy_request('series', request.method)

@app.route('/api/v1/metadata', methods=['GET'])
def metadata():
    return proxy_request('metadata', 'GET')

@app.route('/api/v1/label/<label_name>/values', methods=['GET'])
def label_values(label_name):
    return proxy_request(f'label/{label_name}/values', 'GET')

@app.route('/api/v1/parse_query', methods=['POST'])
def parse_query():
    return proxy_request('parse_query', 'POST')

# Catch-all for any other endpoints
@app.route('/api/v1/<path:endpoint>', methods=['GET', 'POST'])
def catch_all(endpoint):
    return proxy_request(endpoint, request.method)

if __name__ == '__main__':
    # CLI mode: rewrite query from command line and execute it
    if len(sys.argv) > 1:
        query = sys.argv[1]
        print("Original query:")
        print(f"  {query}")
        print()

        rules = load_rules()
        print(f"Loaded {len(rules)} recording rules")
        print()

        try:
            rewritten = rewrite(query)
            print("Rewritten query:")
            print(f"  {rewritten}")
            print()
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

        # Execute the query
        print("Executing against Thanos...")
        import urllib3
        urllib3.disable_warnings()

        r = requests.get(
            f"{THANOS}/api/v1/query",
            params={'query': rewritten},
            headers={'Authorization': f'Bearer {TOKEN}'},
            verify=False
        )

        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Result status: {data.get('status')}")
            if data.get('status') == 'success':
                results = data.get('data', {}).get('result', [])
                print(f"Result count: {len(results)}")
                if results:
                    print("First result:")
                    print(f"  {results[0]}")
            else:
                print(f"Error: {data.get('error')}")
        else:
            print(f"HTTP error: {r.text[:200]}")

        sys.exit(0)

    # Server mode
    import urllib3
    urllib3.disable_warnings()
    print(f"Prometheus Recording Rules Proxy")
    print(f"=================================")
    print(f"Listening: http://localhost:9090")
    print(f"Proxying: {THANOS}")
    print(f"Rules: rules.yaml (reloaded on each request)")
    print()
    print("Perses-compatible endpoints:")
    print("  POST /api/v1/query")
    print("  POST /api/v1/query_range")
    print("  POST /api/v1/labels")
    print("  POST /api/v1/series")
    print("  GET  /api/v1/metadata")
    print("  GET  /api/v1/label/<name>/values")
    print("  POST /api/v1/parse_query")
    print()
    app.run(host='0.0.0.0', port=9090)
