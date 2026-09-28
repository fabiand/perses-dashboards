# ocpercli - Perses Dashboard CLI for OpenShift

A simple CLI wrapper to apply Perses dashboard files to OpenShift/Kubernetes clusters.

## Installation

```bash
# Make executable (already done)
chmod +x ocpercli

# Add to PATH (optional)
sudo cp ocpercli /usr/local/bin/
# OR add to your PATH
export PATH="$PATH:$(pwd)"
```

## Prerequisites

- **oc** (OpenShift CLI) or **kubectl** installed and configured
- **jq** installed (`dnf install jq` or `apt install jq`)
- **Perses CRDs** installed in your cluster
- Valid kubeconfig / oc login session

## Usage

### Basic Usage

Apply a dashboard to the current namespace:
```bash
./ocpercli dashboards/overview.json
```

### Specify Namespace

Apply to a specific namespace:
```bash
./ocpercli -n monitoring dashboards/memory.json
```

### Dry Run

Preview what would be applied without actually applying:
```bash
./ocpercli --dry-run dashboards/cpu.json
```

### Override Project Name

Override the project name in dashboard metadata:
```bash
./ocpercli --project my-custom-project dashboards/io.json
```

## How It Works

The tool:

1. **Validates** the Perses dashboard JSON file
2. **Wraps** it in a Kubernetes Custom Resource (`PersesDashboard`)
3. **Applies** it to the cluster using `oc apply` or `kubectl apply`

### Input Format

Expects Perses dashboard JSON files with this structure:
```json
{
  "kind": "Dashboard",
  "metadata": {
    "name": "overview",
    "project": "openshift-cnv"
  },
  "spec": {
    ...
  }
}
```

### Output Format

Wraps the dashboard in a `PersesDashboard` CRD:
```yaml
apiVersion: perses.dev/v1alpha1
kind: PersesDashboard
metadata:
  name: overview
  namespace: current-namespace
spec:
  dashboard: {...}
```

## Examples

### Apply All Dashboards

```bash
for dash in dashboards/*.json; do
  ./ocpercli "$dash"
  sleep 1
done
```

### Apply to Different Namespace

```bash
./ocpercli -n my-namespace dashboards/overview.json
./ocpercli -n my-namespace dashboards/memory.json
./ocpercli -n my-namespace dashboards/cpu.json
./ocpercli -n my-namespace dashboards/io.json
```

### Check What Would Be Applied

```bash
./ocpercli --dry-run dashboards/overview.json > preview.yaml
cat preview.yaml
```

## Troubleshooting

### "oc: command not found"

Install OpenShift CLI:
```bash
# Download from https://mirror.openshift.com/pub/openshift-v4/clients/ocp/
# Or install kubectl as fallback
```

### "jq: command not found"

Install jq:
```bash
# Fedora/RHEL
sudo dnf install jq

# Debian/Ubuntu
sudo apt install jq

# macOS
brew install jq
```

### "Perses CRDs not found"

Install Perses operator/CRDs first:
```bash
# Follow Perses installation guide for your cluster
kubectl apply -f https://github.com/perses/perses-operator/releases/latest/download/install.yaml
```

### "Invalid JSON" Error

Validate your JSON:
```bash
jq . dashboards/overview.json
```

## Version

```bash
./ocpercli --version
```

## License

Same as the dashboard files in this repository.
