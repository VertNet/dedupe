#!/bin/bash
echo "Default id fields"
echo "================="
curl -X POST -H 'Content-Type: text/csv' --data-binary @data/occ_sample_with_dupes.csv \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""

echo "Using existing field as ID"
echo "=========================="
curl -X POST -H 'Content-Type: text/csv' --data-binary @data/occ_sample_with_dupes.csv \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com&id=individualID"
echo ""

echo "Using non existing field as ID (error)"
echo "======================================"
curl -X POST -H 'Content-Type: text/csv' --data-binary @data/occ_sample_with_dupes.csv \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com&id=foo"
echo ""

echo "No ID field (no id info)"
echo "========================"
curl -X POST -H 'Content-Type: text/csv' --data-binary @data/occ_sample_no_id.csv \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""