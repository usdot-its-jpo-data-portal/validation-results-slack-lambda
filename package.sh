#!/bin/bash

# NOTE!
# This script is deprecated and was intended for manual deployment packaging,
# Refer to the Dockerfile of this repository for the updated deployment process.

mkdir _package
pip install -r src/requirements.txt --upgrade --target _package
cp src/* _package/
cd _package/
zip -r ../validation-results-lambda.zip *
cd ..
rm -rf _package/
echo "Created package in validation-results-lambda.zip"
