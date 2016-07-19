#!/bin/bash
echo "Partial duplicates"
echo "================="
curl -X POST -H 'Content-Type: text/tab-separated-values' \
--data-binary @data/occ_sample_with_partial_dupes.txt \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""
