echo "No Content-Type"
curl -X POST --data-binary @data/occ_sample_with_dupes.txt \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""

echo "Not-allowed Content-Type"
curl -X POST -H "Content-Type: application/json" --data-binary @data/occ_sample_with_dupes.txt \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""

echo "Wrong Content-Type"
curl -X POST -H "Content-Type: text/csv" --data-binary @data/occ_sample_with_dupes.txt \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""

echo "Content-Type = text/tab-separated-values"
curl -X POST -H "Content-Type: text/tab-separated-values" --data-binary @data/occ_sample_with_dupes.txt \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""

echo "Content-Type = text/csv"
curl -X POST -H "Content-Type: text/csv" --data-binary @data/occ_sample_with_dupes.csv \
"http://localhost:8080/api/v0/report?email=javier.otegui@gmail.com"
echo ""
