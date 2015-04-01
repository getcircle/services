#!/bin/bash

COMPANY_NAME=$0
COMPANY_DOMAIN=$1

python manage.py create_organization $COMPANY_NAME $COMPANY_DOMAIN --reset &&
    python manage.py load_organization $COMPANY_DOMAIN --commit &&
    python manage.py load_skills $COMPANY_DOMAIN --filename onboarding/fixtures/eventbrite_skills.csv --commit &&
    python manage.py make_new_hires $COMPANY_DOMAIN &&
    python manage.py add_skills $COMPANY_DOMAIN &&
    python manage.py add_rhlabs_members $COMPANY_DOMAIN mwhahn@gmail.com ravirani@gmail.com
