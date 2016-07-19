#!/bin/bash
echo "Partial duplicates"
echo "================="
curl -X POST -H 'Content-Type: text/tab-separated-values' \
--data-binary @data/occ_sample_with_partial_dupes.txt \
"http://dev.dedupe.vertnet-portal.appspot.com/api/v0/report?email=javier.otegui@gmail.com"
echo ""
