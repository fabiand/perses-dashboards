# 	vim: noexpandtab:

jsons := $(wildcard */*.json)

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
PROM_URL ?= https://$(shell $(OC) get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')

ifdef TOKEN
	OC = oc --server "$(URL)" --token "$(TOKEN)" --insecure-skip-tls-verify
else
	TOKEN ?= $(shell oc whoami -t)
	OC=oc
endif	

URL=https://api.cnv2.engineering.redhat.com:6443

run-dashboard:
	podman -r run --name perses --rm --net=host persesdev/perses:latest
	#-p 127.0.0.1:8080:8080  persesdev/perses:latest

dashboard-url:
	@echo "http://localhost:8080/projects/$(PROJECT)/dashboards/$$(basename $$PWD)"

apply: apply-prom apply-perses
apply-prom:
	# Create a Role with PrometheusRule permissions in current namespace
	$(OC) get role prometheus-rule-creator || $(OC) create role prometheus-rule-creator \
	  --verb=create,get,list,watch,update,patch,delete \
	  --resource=prometheusrules.monitoring.coreos.com
	# Bind the role to your user in current namespace
	$(OC) get rolebinding prometheus-rule-creator || $(OC) create rolebinding prometheus-rule-creator \
	  --role=prometheus-rule-creator \
	  --user=$$($(OC) whoami)
	
	for R in rules/*.yaml ; do $(OC) apply -f $$R ; done

apply-perses: FORCE $(jsons)
	percli apply -f 01-project.json
	percli project $(PROJECT)
	jq --arg token "$(TOKEN)" '.[0].spec.authorization.credentials = $$token' 02-secret.json.in | percli apply -f -
	jq --arg url "$(PROM_URL)" '.[0].spec.plugin.spec.proxy.spec.url = $$url' 03-dts.json.in | percli apply -f -
	
	for D in dashboards/*.json ; do percli apply -f $$D ; done

docs: 04-dash-memory-summary.json.in 04-dash-memory-details.json.in
	cp documentation.md.in documentation.md
	cat $< | jq -re '[ .spec.panels[].spec.display ] | sort_by(.name) | .[] | "### " + .name + "\n" + (.description // "None") + "\n"' >> documentation.md

FORCE:

.PHONY: FORCE import apply $(jsons)
