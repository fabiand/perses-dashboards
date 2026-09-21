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

    # Pre-processing: Replace bare metric names with sum of all variants
    # Group rules by metric name
    metrics_map = {}
    for rule in rules:
        metric = rule['name']
        if metric not in metrics_map:
            metrics_map[metric] = []
        metrics_map[metric].append(rule)

    # For each metric with multiple variants, replace bare usage with sum
    for metric, variants in metrics_map.items():
        if len(variants) <= 1:
            continue  # Single variant, no need to sum

        # Match bare metric at word boundary, not followed by {
        bare_pattern = rf'\b{re.escape(metric)}\b(?!\{{)'
        if re.search(bare_pattern, query):
            # Build sum of all variants with their labels
            variant_selectors = []
            for v in variants:
                # Build label selector, excluding metadata labels
                label_pairs = []
                for k in sorted(v['labels'].keys()):
                    if k not in ['unit', 'DevelopmentPreview']:
                        label_pairs.append(f'{k}="{v["labels"][k]}"')

                if label_pairs:
                    selector = f'{metric}{{{", ".join(label_pairs)}}}'
                else:
                    selector = metric
                variant_selectors.append(selector)

            # Replace bare metric with sum of all variants
            sum_expr = '(' + ' + '.join(variant_selectors) + ')'
            query = re.sub(bare_pattern, sum_expr, query)

    # Loop and replace until no more recording rules are found
    max_iterations = 20  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        replaced = False

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
                replaced = True
                break  # Start over with new query

        if not replaced:
            # No more replacements found
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
    if method == 'GET':
        print(f"  Extracted params: {list(url_params.keys())}", file=sys.stderr)
        if 'start' in url_params or 'end' in url_params:
            print(f"    Time range: start={url_params.get('start')}, end={url_params.get('end')}", file=sys.stderr)
    else:
        print(f"  Extracted params: {list(body_params.keys())}", file=sys.stderr)
        if 'start' in body_params or 'end' in body_params:
            print(f"    Time range: start={body_params.get('start')}, end={body_params.get('end')}, step={body_params.get('step')}", file=sys.stderr)
    if query:
        print(f"  ORIGINAL QUERY:", file=sys.stderr)
        # Pretty-print by adding indentation to newlines
        indented = query.replace('\n', '\n    ')
        print(f"    {indented}", file=sys.stderr)

    # Only rewrite on query/query_range endpoints
    if endpoint in ['query', 'query_range'] and query:
        try:
            rewritten_query = rewrite(query)
            if rewritten_query != query:
                print(f"  REWRITTEN QUERY (full):", file=sys.stderr)
                # Pretty-print by adding indentation to newlines
                indented = rewritten_query.replace('\n', '\n    ')
                print(f"    {indented}", file=sys.stderr)
                print(f"", file=sys.stderr)
            query = rewritten_query
            if method == 'GET':
                url_params['query'] = query
            else:
                body_params['query'] = query
        except ValueError as e:
            print(f"  Error: {e}", file=sys.stderr)
            return make_error_response(str(e))

    # Forward to Thanos
    # Always use POST to avoid URL length limits
    url = f"{THANOS}/api/v1/{endpoint}"
    headers = {'Authorization': f'Bearer {TOKEN}'}

    # Use POST for all requests to avoid "header line too long" errors
    # Convert GET params to POST body
    params_to_send = body_params if method == 'POST' else url_params

    print(f"  Forwarding as POST: {list(params_to_send.keys())}", file=sys.stderr)
    if endpoint in ['query', 'query_range'] and params_to_send.get('query'):
        print(f"  Query length: {len(str(params_to_send.get('query')))} chars", file=sys.stderr)

    r = requests.post(url, data=params_to_send, headers=headers, verify=False)

    print(f"  Response: {r.status_code}, {len(r.content)} bytes", file=sys.stderr)
    print(f"  Response headers: {list(r.headers.keys())}", file=sys.stderr)

    # Debug: show response for small responses (likely errors or empty)
    if len(r.content) < 200:
        try:
            response_json = json.loads(r.content)
            print(f"  Response body: {json.dumps(response_json, indent=2)[:200]}", file=sys.stderr)
        except:
            print(f"  Response body: {r.content[:200]}", file=sys.stderr)

    # Only pass through essential headers to avoid "header line too long" errors
    # Skip hop-by-hop headers, auth headers, and encoding headers
    # Note: requests library automatically decompresses r.content, so we must
    # not pass Content-Encoding header (it would cause double-decompression)
    skip_headers = {
        'Connection', 'Keep-Alive', 'Proxy-Authenticate',
        'Proxy-Authorization', 'TE', 'Trailers', 'Transfer-Encoding',
        'Upgrade', 'Authorization', 'Cookie', 'Set-Cookie',
        'Content-Encoding',  # Skip because r.content is already decompressed
    }

    essential_headers = {}
    for key, value in r.headers.items():
        # Skip problematic headers
        if key in skip_headers or key.lower() in {h.lower() for h in skip_headers}:
            continue
        # Skip very long headers that might cause issues
        if len(value) > 8000:
            print(f"  Skipping long header: {key} ({len(value)} bytes)", file=sys.stderr)
            continue
        essential_headers[key] = value

    # Ensure Content-Type is set
    if 'Content-Type' not in essential_headers:
        essential_headers['Content-Type'] = 'application/json'

    return Response(r.content, r.status_code, essential_headers)

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
