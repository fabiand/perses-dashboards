# 	vim: noexpandtab:

jsons := $(wildcard *.json *.json.in)

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
URL := https://$(shell oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN := $(shell oc whoami -t)


run-dashboard:
	podman -r run --name perses --rm --net=host persesdev/perses:latest
	#-p 127.0.0.1:8080:8080  persesdev/perses:latest

dashboard-url:
	@echo "http://localhost:8080/projects/$(PROJECT)/dashboards/$$(basename $$PWD)"

apply: apply-prom apply-perses
apply-prom:
	# Create a Role with PrometheusRule permissions in current namespace
	oc get role prometheus-rule-creator || oc create role prometheus-rule-creator \
	  --verb=create,get,list,watch,update,patch,delete \
	  --resource=prometheusrules.monitoring.coreos.com &
	
	# Bind the role to your user in current namespace
	oc get rolebinding prometheus-rule-creator || oc create rolebinding prometheus-rule-creator \
	  --role=prometheus-rule-creator \
	  --user=$$(oc whoami) &
	
	kubectl apply -f rules.yaml

apply-perses: FORCE $(jsons)
	percli apply -f 01-project.json
	percli project $(PROJECT)
	jq --arg token "$(TOKEN)" '.[0].spec.authorization.credentials = $$token' 02-secret.json.in | percli apply -f -
	jq --arg url "$(URL)" '.[0].spec.plugin.spec.proxy.spec.url = $$url' 03-dts.json.in | percli apply -f -
	percli apply -f 04-dash-memory-full.json

docs: 04-dash-memory-summary.json.in 04-dash-memory-details.json.in
	cp documentation.md.in documentation.md
	cat $< | jq -re '[ .spec.panels[].spec.display ] | sort_by(.name) | .[] | "### " + .name + "\n" + (.description // "None") + "\n"' >> documentation.md

FORCE:

.PHONY: FORCE import apply $(jsons)
