#!/bin/bash

DB_URI="postgresql://zenodo:zenodo@localhost:5432/zenodo"

tables=(
    rdm_versions_state
    rdm_records_metadata
    rdm_drafts_metadata
    rdm_parents_metadata
)
rev_tables=$(for i in `printf '%s\n' "${tables[@]}"|tac`; do echo $i; done)

while getopts a: flag
do
    case "${flag}" in
        a) action=${OPTARG};;
    esac
done

case $action in
  dump)
    for t in ${tables[@]}; do
        echo Dumping $t
        psql "$DB_URI" -c "COPY $t TO STDOUT WITH BINARY" > "$t.dump"
    done
    ;;

  delete)
    for t in ${tables[@]}; do
        echo Deleting $t
        psql "$DB_URI" -c "DELETE FROM $t"
    done
    ;;

  load)
    for t in ${rev_tables[@]}; do
        echo Loading $t
        cat "$t.dump" | psql "$DB_URI" -c "COPY $t FROM STDIN WITH BINARY"
    done
    ;;

  *)
    echo -n "unknown"
    ;;
esac
