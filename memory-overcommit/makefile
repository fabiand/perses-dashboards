# 	vim: noexpandtab:

sources := $(wildcard *.yaml.in)
yamls := $(patsubst %.yaml.in,%.yaml,$(sources))

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
URL := https://$(shell oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN := $(shell oc whoami -t)

import:
	percli get -o yaml dash memory-overcommit | sed -e "s#^\(\s\+\)project: .*#\\1project: {{PROJECT}}#" -e "/^\s\+\(createdAt\|updatedAt\|version\)/ d" > 04-dash.yaml.in
	test -f 01-*.yaml && mv *.yaml .trash/ || :

apply: $(yamls)
	echo $(sources) 
	echo $(yamls)
	percli apply -f 01-project.yaml
	percli project $(PROJECT)
	for F in $(yamls) ; do ( set -x ; percli apply -f $$F ; ) ; done

url:
	@echo "http://localhost:8080/projects/$(PROJECT)/dashboards/memory-overcommit"

%.yaml: %.yaml.in
	echo "$(URL)" > vars.d/URL
	echo "$(TOKEN)" > vars.d/TOKEN
	echo "$(PROJECT)" > vars.d/PROJECT
	python3 vars.py $< > $@

FORCE:

.PHONY: FORCE $(sources)
