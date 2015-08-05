#!/bin/bash

COMPANY_NAME=$1
COMPANY_DOMAIN=$2
COMPANY_IMAGE_URL=$3

python manage.py create_organization $COMPANY_NAME $COMPANY_DOMAIN --image_url "$COMPANY_IMAGE_URL" &&
    python manage.py load_organization $COMPANY_DOMAIN --commit &&
    python manage.py build_watson
