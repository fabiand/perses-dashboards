# 	vim: noexpandtab:

sources := $(wildcard *.json.in)
jsons := $(patsubst %.json.in,%.json,$(sources))

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
URL := https://$(shell oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN := $(shell oc whoami -t)

import:
	make get-dashboard
	make inject-vars

	test -f 01-*.json && mv *.json .trash/ || :

get-dashboard:
	percli get -o json dash memory-overcommit \
	| jq '.[] | .metadata.project = "{{PROJECT}}"' \
	| jq 'del(.metadata.createdAt, .metadata.updatedAt, .metadata.version)' > 04-dash.json.in
	#sed -e "s#^\(\s\+\)project: .*#\\1project: {{PROJECT}}#" -e "/^\s\+\(createdAt\|updatedAt\|version\)/ d" > 04-dash.json.in

inject-vars: FORCE
	-rm vars.d/{URL,TOKEN,PROJECT}
	for VAR in $$(ls -1 vars.d); do	( set -x ; jq --arg var "{{$$VAR}}" --rawfile val "vars.d/$$VAR" 'walk(if type == "string" and contains($$val) then (split($$val)|join($$var)) else . end)' 04-dash.json.in > .04-dash.json.in && mv .04-dash.json.in 04-dash.json.in ; ) || exit 1 ; done

apply: FORCE $(jsons)
	@echo -n "$(URL)" > vars.d/URL
	@echo -n "$(TOKEN)" > vars.d/TOKEN
	@echo -n "$(PROJECT)" > vars.d/PROJECT
	
	echo sources $(sources)
	echo jsons $(jsons)
	percli apply -f 01-project.json
	percli project $(PROJECT)
	for F in $(jsons) ; do ( set -x ; percli apply -f $$F ; ) ; done

url:
	@echo "http://localhost:8080/projects/$(PROJECT)/dashboards/memory-overcommit"

%.json: %.json.in
	cp $< $@
	for VAR in $$(ls -1 vars.d); do	echo $$VAR ; jq --arg var "{{$$VAR}}" --rawfile val "vars.d/$$VAR" 'walk(if type == "string" and contains($$var) then (split($$var)|join($$val)) else . end)' $@ > .$@ ; mv .$@ $@ ; done

clean: $(jsons)
	rm -v $(jsons)

FORCE:

.PHONY: FORCE import apply $(sources) inject-vars
