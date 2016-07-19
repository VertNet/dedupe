#!/bin/bash

echo "======================================="
echo "Running all tests against local version"
echo "======================================="
echo ""
echo "------------------------------"
echo "Checking 'content-type' header"
echo "------------------------------"
echo ""
echo ""

test/test_local_content_type.sh

echo ""
echo "-----------------------"
echo "Checking 'id' parameter"
echo "-----------------------"
echo ""
echo ""

test/test_local_id_field.sh

echo ""
echo "---------------------------"
echo "Checking partial duplicates"
echo "---------------------------"
echo ""
echo ""

test/test_local_partial_dupes.sh

echo ""
echo "=================="
echo "All tests finished"
echo "=================="
echo ""