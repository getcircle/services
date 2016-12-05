from django.conf import settings
from mock import patch

from services.test import (
    fuzzy,
    MockedTestCase,
)

from .. import helpers


class Test(MockedTestCase):

    def _mock_get_hosted_zone(self, patched_boto):
        patched_boto.client().get_hosted_zone.side_effect = lambda *args, **kwargs: {
            'HostedZone': {
                'CallerReference': 'aa40f093-8501-4bb0-9d32-905dbd292e49',
                'Config': {'PrivateZone': False},
                'Id': '/hostedzone/Z2RUM0QYIALWAH',
                'Name': 'dev.lunohq.com.',
                'ResourceRecordSetCount': 7,
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': '7f6d2c6b-a1e2-11e5-8259-adeb0679db70',
            },
        }

    @patch('organizations.helpers.boto3')
    def test_create_a_record_for_subdomain(self, patched_boto):
        self._mock_get_hosted_zone(patched_boto)

        helpers.create_a_record_for_subdomain('example')

        call_kwargs = patched_boto.client().change_resource_record_sets.call_args[1]
        self.assertEqual(call_kwargs['HostedZoneId'], settings.AWS_HOSTED_ZONE_ID)
        action = call_kwargs['ChangeBatch']['Changes'][0]
        self.assertEqual(action['Action'], 'CREATE')
        record_set = action['ResourceRecordSet']
        self.assertEqual(record_set['Name'], 'example.dev.lunohq.com.')
        self.assertEqual(record_set['Type'], 'A')

        alias_target = record_set['AliasTarget']
        self.assertEqual(alias_target['HostedZoneId'], settings.AWS_ALIAS_HOSTED_ZONE_ID)
        self.assertEqual(alias_target['DNSName'], settings.AWS_ALIAS_TARGET)

    @patch('organizations.helpers.boto3')
    def test_create_mx_record_for_subdomain(self, patched_boto):
        self._mock_get_hosted_zone(patched_boto)
        helpers.create_mx_record_for_subdomain('example')

        call_kwargs = patched_boto.client().change_resource_record_sets.call_args[1]
        self.assertEqual(call_kwargs['HostedZoneId'], settings.AWS_HOSTED_ZONE_ID)
        action = call_kwargs['ChangeBatch']['Changes'][0]
        self.assertEqual(action['Action'], 'CREATE')
        record_set = action['ResourceRecordSet']
        self.assertEqual(record_set['Name'], 'example.dev.lunohq.com.')
        self.assertEqual(record_set['Type'], 'MX')

        resource_records = record_set['ResourceRecords']
        self.assertEqual(len(resource_records), 1)
        self.assertEqual(
            resource_records[0]['Value'], '10 %s' % (settings.AWS_SES_INBOUND_ENDPOINT,)
        )

    @patch('organizations.helpers.boto3')
    def test_create_txt_verification_record_for_subdomain(self, patched_boto):
        self._mock_get_hosted_zone(patched_boto)
        verification_token = fuzzy.uuid()
        patched_boto.client().verify_domain_identity.side_effect = lambda *args, **kwargs: {
            'VerificationToken': verification_token,
        }

        helpers.create_ses_verification_record_for_subdomain('example')

        call_kwargs = patched_boto.client.call_args[1]
        self.assertEqual(call_kwargs['region_name'], settings.AWS_REGION_NAME)

        call_kwargs = patched_boto.client().verify_domain_identity.call_args[1]
        self.assertEqual(call_kwargs['Domain'], 'example.dev.lunohq.com')

        call_kwargs = patched_boto.client().change_resource_record_sets.call_args[1]
        self.assertEqual(call_kwargs['HostedZoneId'], settings.AWS_HOSTED_ZONE_ID)
        action = call_kwargs['ChangeBatch']['Changes'][0]
        self.assertEqual(action['Action'], 'CREATE')
        record_set = action['ResourceRecordSet']
        self.assertEqual(record_set['Name'], '_amazonses.example.dev.lunohq.com.')
        self.assertEqual(record_set['Type'], 'TXT')

        resource_records = record_set['ResourceRecords']
        self.assertEqual(len(resource_records), 1)
        self.assertEqual(resource_records[0]['Value'], '"%s"' % (verification_token,))
