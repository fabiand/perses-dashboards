# 	vim: noexpandtab:

apply: gen
	percli apply -d .

gen: 02-dts.yaml 03-secret.yaml

URL="https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com"
TOKEN="$$(oc whoami -t)"

02-dts.yaml: 02-dts.in
	sed "s/{{URL}}/$(URL)/" $< > $@

03-secret.yaml: $@.in
	sed "s/{{TOKEN}}/$(TOKEN)/" $< > $@

