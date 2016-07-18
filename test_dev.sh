#!/bin/bash

echo "====================================="
echo "Running all tests against dev version"
echo "====================================="
echo ""
echo "------------------------------"
echo "Checking 'content-type' header"
echo "------------------------------"
echo ""
echo ""

test/test_dev_content_type.sh

echo ""
echo "-----------------------"
echo "Checking 'id' parameter"
echo "-----------------------"
echo ""
echo ""

test/test_dev_id_field.sh

echo ""
echo "=================="
echo "All tests finished"
echo "=================="
echo ""