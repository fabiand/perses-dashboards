import sys
import os
import re
import yaml

def replace_tpl_vars(data):
    tpl_vars = (
        (e.name, open(e.path).read().rstrip())
        for e in (e for e in os.scandir("vars.d") if e.is_file())
        )
#    print(tpl_vars)

    for (key, val) in tpl_vars:
        data = data.replace("{{%s}}" % key, val)
    return data

with open(sys.argv[1]) as srcfile:
    print(replace_tpl_vars(srcfile.read()))
        
