# 	vim: noexpandtab:

sources := $(wildcard *.yaml.in)
yamls := $(patsubst %.yaml.in,%.yaml,$(sources))

#URL=https://prometheus-k8s-openshift-monitoring.apps.cnv2.engineering.redhat.com
PROJECT := openshift-cnv
URL := https://$(shell oc get route -n openshift-monitoring prometheus-k8s -o jsonpath='{.status.ingress[0].host}')
TOKEN := $(shell oc whoami -t)


apply: $(yamls)
	echo $(sources) 
	echo $(yamls)
	percli apply -f 01-project.yaml
	percli project $(PROJECT)
	for F in $(yamls) ; do ( set -x ; percli apply -f $$F ; ) ; done

%.yaml: %.yaml.in
	sed -e "s!{{URL}}!$(URL)!" \
	    -e "s;{{TOKEN}};$(TOKEN);" \
	    -e "s;{{PROJECT}};$(PROJECT);" \
	$< > $@

FORCE:

.PHONY: FORCE $(sources)
