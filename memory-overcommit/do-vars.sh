
#set -x

query_to_vars() {
  local JSONFILE="${1}"

  [[ -z "$1" ]] && exit 4

  for VAR in $(ls -1 vars.d)
  do
    jq \
      --arg var "{{$VAR}}" \
      --rawfile val "vars.d/$VAR" \
      'walk(if type == "string" and contains($val) then (split($val)|join($var)) else . end)' \
      "$JSONFILE" > ".$JSONFILE" || exit 4
      mv ".$JSONFILE" "$JSONFILE"
  done
}

vars_to_query() {
  local JSONFILE="${1}"
  
  [[ -z "$1" ]] && exit 4

  # Replace vars as long as vars are in the file
  while grep -qE "{{($(ls -1 vars.d | tr "\n" "|"))}}" $JSONFILE;
  do
    for VAR in $(ls -1 vars.d);
    do
      jq \
        --arg var "{{$VAR}}" \
        --rawfile val "vars.d/$VAR" \
        'walk(if type == "string" and contains($var) then (split($var)|join($val)) else . end)' \
        "$JSONFILE" > ".$JSONFILE" || exit 4
        mv ".$JSONFILE" "$JSONFILE"
    done
  done
}


$@
