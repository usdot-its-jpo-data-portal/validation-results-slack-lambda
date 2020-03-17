#!/bin/bash
PARAMETER_OVERRIDES=$(eval echo $PARAMETER_OVERRIDES)
docker run --rm \
    -e AWS_DEFAULT_REGION \
    -e AWS_CONTAINER_CREDENTIALS_RELATIVE_URI \
    -e "BUCKET=$BUCKET" \
    -e "FUNCTION_NAME=$FUNCTION_NAME" \
    -e "REGION=$AWS_DEFAULT_REGION" \
    -e "ENV=$ENV" \
    -e "PARAMETER_OVERRIDES=${PARAMETER_OVERRIDES}" \
    -i $IMAGE_URI:$IMAGE_TAG