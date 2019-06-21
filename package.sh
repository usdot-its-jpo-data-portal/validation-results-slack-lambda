#!/bin/bash
mkdir _package
pip install -r requirements.txt --upgrade --target ./_package
cp main.py ./_package
cp slacker.py ./_package
cp -r sqs_client ./_package/sqs_client
cd _package
zip -r results.zip main.py slacker.py odevalidator*/ sqs_client/ PyYAML-5.1.1.dist-info/ yaml/
mv results.zip ..
cd ..
rm -rf ./_package
echo "Created package in results.zip"
