export AWS_PROFILE=big-cloud-country-admin
aws s3 cp ./templates s3://big-cloud-country/templates/ --recursive --acl public-read