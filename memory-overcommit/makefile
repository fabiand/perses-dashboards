# 	vim: noexpandtab:

sources := $(wildcard *.json.in)
jsons := $(patsubst %.json.in,%.yaml,$(sources))

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
URL := https://$(shell oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN := $(shell oc whoami -t)

import:
	percli get -o json dash memory-overcommit \
	| jq '.[] | .metadata.project = "{{PROJECT}}"' > 04-dash.json.in
	#sed -e "s#^\(\s\+\)project: .*#\\1project: {{PROJECT}}#" -e "/^\s\+\(createdAt\|updatedAt\|version\)/ d" > 04-dash.json.in
	test -f 01-*.json && mv *.json .trash/ || :

apply: $(jsons)
	echo $(sources) 
	echo $(jsons)
	percli apply -f 01-project.json
	percli project $(PROJECT)
	for F in $(jsons) ; do ( set -x ; percli apply -f $$F ; ) ; done

url:
	@echo "http://localhost:8080/projects/$(PROJECT)/dashboards/memory-overcommit"

%.json: %.json.in
	echo "$(URL)" > vars.d/URL
	echo "$(TOKEN)" > vars.d/TOKEN
	echo "$(PROJECT)" > vars.d/PROJECT
	#python3 vars.py $< > $@
	for VAR in $$(ls -1 vars.d); do	jq --arg var $$VAR --rawfile val vars.d/$$VAR 'walk(if . == $$var then $$val else . end)' $<

FORCE:

.PHONY: FORCE $(sources)
