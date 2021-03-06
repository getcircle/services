import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_fqn(route53_client, subdomain, hosted_zone_id):
    hosted_zone = route53_client.get_hosted_zone(Id=hosted_zone_id)
    return '%s.%s' % (subdomain, hosted_zone['HostedZone']['Name'])


def _create_resource_record_sets(client, record_set, comment, hosted_zone_id):
    action = {
        'Action': 'CREATE',
        'ResourceRecordSet': record_set,
    }
    batch = {
        'Comment': comment,
        'Changes': [action],
    }
    logger.info('%s:\n%s', comment, {'hosted_zone_id': hosted_zone_id, 'batch': batch})
    return client.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=batch)


def _boto_client(*args, **kwargs):
    kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
    kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client(*args, **kwargs)


def create_a_record_for_subdomain(subdomain):
    client = _boto_client('route53')
    fqn = _get_fqn(client, subdomain, settings.AWS_HOSTED_ZONE_ID)
    record_set = {
        'Name': fqn,
        'Type': 'A',
        'AliasTarget': {
            'HostedZoneId': settings.AWS_ALIAS_HOSTED_ZONE_ID,
            'DNSName': settings.AWS_ALIAS_TARGET,
            'EvaluateTargetHealth': False,
        },
    }
    comment = 'Creating "A" record for subdomain: "%s"' % (subdomain,)
    return _create_resource_record_sets(client, record_set, comment, settings.AWS_HOSTED_ZONE_ID)


def create_mx_record_for_subdomain(subdomain):
    client = _boto_client('route53')
    fqn = _get_fqn(client, subdomain, settings.AWS_HOSTED_ZONE_ID)
    record_set = {
        'Name': fqn,
        'Type': 'MX',
        'TTL': 1800,
        'ResourceRecords': [{'Value': '10 %s' % (settings.AWS_SES_INBOUND_ENDPOINT,)}],
    }
    comment = 'Creating "MX" record for subdomain: "%s"' % (subdomain,)
    return _create_resource_record_sets(client, record_set, comment, settings.AWS_HOSTED_ZONE_ID)


def create_ses_verification_record_for_subdomain(subdomain):
    route53 = _boto_client('route53')
    ses = _boto_client('ses', region_name=settings.AWS_REGION_NAME)
    fqn = _get_fqn(route53, subdomain, settings.AWS_HOSTED_ZONE_ID)

    # remove trailing ".", SES doesn't treat this as a valid domain
    ses_fqn = fqn
    if ses_fqn.endswith('.'):
        ses_fqn = ses_fqn[:-1]

    response = ses.verify_domain_identity(Domain=ses_fqn)
    verification_token = response['VerificationToken']

    record_set = {
        'Name': '_amazonses.%s' % (fqn,),
        'Type': 'TXT',
        'TTL': 1800,
        'ResourceRecords': [{'Value': '"%s"' % (verification_token,)}],
    }
    comment = 'Creating SES "TXT" verification record for subdomain: "%s"' % (subdomain,)
    return _create_resource_record_sets(route53, record_set, comment, settings.AWS_HOSTED_ZONE_ID)
