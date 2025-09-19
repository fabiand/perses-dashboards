# 	vim: noexpandtab:

sources := $(wildcard *.json.in)
jsons := $(patsubst %.json.in,%.json,$(sources))

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
URL := https://$(shell oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN := $(shell oc whoami -t)

import:
	make get-dashboard

	test -f 01-*.json && mv *.json .trash/ || :

get-dashboard:
	percli get -o json dash $$(basename $$PWD) \
	| jq '.[] | .metadata.project = "{{PROJECT}}"' \
	| jq 'del(.metadata.createdAt, .metadata.updatedAt, .metadata.version)' > 04-dash.json.in
	bash do-vars.sh query_to_vars "04-dash.json.in"

env-vars: FORCE
	echo -n "$(URL)" > vars.d/URL
	echo -n "$(TOKEN)" > vars.d/TOKEN
	echo -n "$(PROJECT)" > vars.d/PROJECT

apply: FORCE env-vars $(jsons)
	percli apply -f 01-project.json
	percli project $(PROJECT)
	for F in $(jsons) ; do ( set -x ; percli apply -f $$F ; ) ; done

docs: 04-dash.json.in
	cp documentaion.md.in documentation.md
	cat $< | jq -re '[ .spec.panels[].spec.display ] | sort_by(.name) | .[] | "### " + .name + "\n" + (.description // "None") + "\n"' >> documentation.md

url:
	@echo "http://localhost:8080/projects/$(PROJECT)/dashboards/$$(basename $$PWD)"

%.json: %.json.in
	cp $< $@
	bash do-vars.sh vars_to_query $@

clean: $(jsons)
	rm -v $(jsons)

FORCE:

.PHONY: FORCE import apply $(sources) inject-vars env-vars
