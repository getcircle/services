#!/bin/bash

COMPANY_NAME=$1
COMPANY_DOMAIN=$2
COMPANY_IMAGE_URL=$3
COMPANY_EMPLOYEES_FILE=$4
COMPANY_OFFICE_FILE=$5

python manage.py create_organization "$COMPANY_NAME" $COMPANY_DOMAIN --image_url "$COMPANY_IMAGE_URL" &&
    python manage.py load_organization_v2 $COMPANY_DOMAIN --filename=$COMPANY_EMPLOYEES_FILE --locations-filename=$COMPANY_OFFICE_FILE --commit &&
    python manage.py build_watson
