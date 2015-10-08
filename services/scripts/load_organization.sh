#!/bin/bash

COMPANY_NAME=$1
COMPANY_DOMAIN=$2
COMPANY_IMAGE_URL=$3
COMPANY_EMPLOYEES_FILE=$4
COMPANY_OFFICE_FILE=$5

python manage.py create_organization "$COMPANY_NAME" $COMPANY_DOMAIN --image_url "$COMPANY_IMAGE_URL" &&
    python manage.py load_organization $COMPANY_DOMAIN $COMPANY_EMPLOYEES_FILE $COMPANY_OFFICE_FILE &&
    python manage.py build_watson
