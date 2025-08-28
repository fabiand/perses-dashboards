
set -x
query_to_vars() {
  local JSONINFILE="${1:-04-dash.json.in}"

  for VAR in $(ls -1 vars.d)
  do
    jq \
      --arg var "{{$VAR}}" \
      --rawfile val "vars.d/$VAR" \
      'walk(if type == "string" and contains($val) then (split($val)|join($var)) else . end)' \
      $JSONINFILE > .$JSONINFILE || exit 4
      mv .$JSONINFILE $JSONINFILE
  done
}

vars_to_query() {
  local JSONINFILE="${1:-04-dash.json.in}"

	for VAR in $(ls -1 vars.d);
  do
    jq \
      --arg var "{{$VAR}}" \
      --rawfile val "vars.d/$VAR" \
      'walk(if type == "string" and contains($var) then (split($var)|join($val)) else . end)' \
      $JSONINFILE > .$JSONINFILE || exit 4
      mv .$JSONINFILE $JSONINFILE
  done
}


$@
