# 	vim: noexpandtab:

apply: apply-project gen
	percli apply -d .

apply-project: 01-project.yaml
	percli apply -f 01-project.yaml
	percli project openshift-cnv

YAMLS=ß1-project.yaml 02-dts.yaml 03-secret.yaml 04-dash.yaml

gen: $(YAMLS)

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT=$$(oc project -q)
URL=$$(oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN=$$(oc whoami -t)

.PHONY: $(YAMLS) 01-project.yaml 02-dts.yaml 03-secret.yaml 04-dash.yaml
%.yaml: $@.in
	sed -e "s!{{URL}}!$(URL)!" $< > $@
	sed -e "s;{{TOKEN}};$(TOKEN);" $< > $@
	sed -e "s;{{PROJECT}};$(PROJECT);" $< > $@

