from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.organization.containers import integration_pb2

from services.test import factory

from . import models


class OrganizationFactory(factory.Factory):
    class Meta:
        model = models.Organization
        protobuf = organization_containers.OrganizationV1

    name = factory.FuzzyText()
    domain = factory.FuzzyText()
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = organization_containers.TeamV1

    name = factory.FuzzyText()
    organization = factory.SubFactory(OrganizationFactory)
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')
    manager_profile_id = factory.FuzzyUUID()
    created_by_profile_id = factory.FuzzyUUID()

    @factory.post_generation
    def status(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            if isinstance(extracted, dict):
                value = extracted['value']
                by_profile_id = extracted['by_profile_id']
            else:
                value = extracted.value
                by_profile_id = extracted.by_profile_id

            models.TeamStatus.objects.create(
                team=self,
                value=value,
                organization_id=self.organization_id,
                by_profile_id=by_profile_id,
            )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # NB: If we're creating a team from scratch, ensure we create a manager
        # and a direct report since that is our requirement for a team. If one
        # already exists, we don't want to add anything.
        manager = models.ReportingStructure.objects.filter(
            organization=kwargs['organization'],
            profile_id=kwargs['manager_profile_id'],
        )
        if not manager:
            manager = ReportingStructureFactory.create(
                manager_id=None,
                organization=kwargs['organization'],
                profile_id=kwargs['manager_profile_id'],
            )
        else:
            manager = manager[0]

        if not manager.get_descendant_count():
            ReportingStructureFactory.create(
                manager_id=kwargs['manager_profile_id'],
                organization=kwargs['organization'],
            )
        return super(TeamFactory, cls)._create(model_class, *args, **kwargs)


class LocationFactory(factory.Factory):
    class Meta:
        model = models.Location
        protobuf = organization_containers.LocationV1

    name = factory.FuzzyText()
    organization = factory.SubFactory(OrganizationFactory)
    address_1 = factory.FuzzyText(suffix=' Street')
    address_2 = factory.FuzzyText(suffix=' Suite 700')
    city = factory.FuzzyText()
    region = factory.FuzzyText(length=2)
    postal_code = '94010'
    country_code = 'USA'
    latitude = '37.578286'
    longitude = '-122.348729'
    timezone = 'America/Los_Angeles'


class LocationMemberFactory(factory.Factory):
    class Meta:
        model = models.LocationMember

    location = factory.SubFactory(LocationFactory)
    profile_id = factory.FuzzyUUID()
    added_by_profile_id = factory.FuzzyUUID()
    organization = factory.SubFactory(OrganizationFactory)


class TokenFactory(factory.Factory):
    class Meta:
        model = models.Token
        protobuf = organization_containers.TokenV1

    organization = factory.SubFactory(OrganizationFactory)
    requested_by_user_id = factory.FuzzyUUID()


class IntegrationFactory(factory.Factory):
    class Meta:
        model = models.Integration
        protobuf = integration_pb2.IntegrationV1

    organization = factory.SubFactory(OrganizationFactory)
    type = integration_pb2.GOOGLE_GROUPS
    provider_uid = factory.FuzzyText()


class ReportingStructureFactory(factory.Factory):
    class Meta:
        model = models.ReportingStructure
        django_get_or_create = ('profile_id',)

    organization = factory.SubFactory(OrganizationFactory)
    profile_id = factory.FuzzyUUID()
    added_by_profile_id = factory.FuzzyUUID()


class SSOFactory(factory.Factory):
    class Meta:
        model = models.SSO
        protobuf = organization_containers.SSOV1

    provider = organization_containers.SSOV1.OKTA
    organization = factory.SubFactory(OrganizationFactory)
    metadata_url = factory.FuzzyText(prefix='http://sso.metadata.', suffix='.com')
    metadata = '<?xml version="1.0" encoding="UTF-8"?><md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="http://www.okta.com/exk4ucst4sA1qzof90h7"><md:IDPSSODescriptor WantAuthnRequestsSigned="true" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"><md:KeyDescriptor use="signing"><ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:X509Data><ds:X509Certificate>MIIDpDCCAoygAwIBAgIGAU+F5WdaMA0GCSqGSIb3DQEBBQUAMIGSMQswCQYDVQQGEwJVUzETMBEG\nA1UECAwKQ2FsaWZvcm5pYTEWMBQGA1UEBwwNU2FuIEZyYW5jaXNjbzENMAsGA1UECgwET2t0YTEU\nMBIGA1UECwwLU1NPUHJvdmlkZXIxEzARBgNVBAMMCmRldi00MTAzNjIxHDAaBgkqhkiG9w0BCQEW\nDWluZm9Ab2t0YS5jb20wHhcNMTUwODMxMjIzMzA4WhcNNDUwODMxMjIzNDA4WjCBkjELMAkGA1UE\nBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExFjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xDTALBgNV\nBAoMBE9rdGExFDASBgNVBAsMC1NTT1Byb3ZpZGVyMRMwEQYDVQQDDApkZXYtNDEwMzYyMRwwGgYJ\nKoZIhvcNAQkBFg1pbmZvQG9rdGEuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\ngeRZrc+svHeBVdVDsZX2lvvKLPPKWxWAWrGENqeQuXe8iomXgiyOHROf78eSke7nXUzdLFrjCUPP\na5m+LXTTDUEqfVIloZHiQZWq2hkp4JO0K3ksAdpNHcVeh9nKHOuHHznVvm+namP4PBRaz/yG43yN\n+Bl2XiyQjrSvG/6m7KmuLU1YL5IICeoYwU+r6WI4rCfoDoH+w7tgqyGBdqu38UiUc48/fWMqq1PW\n7tjS8B/ayFZnCdKclDPSCMoChtb95wbEgF2/w4PygYyb1GmjHxzjLGtxcSyvcyBC2w1CEHAq8ZWw\nRmyQ/2B6omz8EdXy92Q0rWIG/JYezOEki6FnjwIDAQABMA0GCSqGSIb3DQEBBQUAA4IBAQBzT+7o\nh1WvkLZ4P6LUS6CMntzgIJ7rB1JA85/kYc6pWu6Z8lIveG0Z4X1DXh4koVEcMXphzIUlXjduMFTG\nDn2i0nn0r4bcXhtKpyFUHqTPH6jhteQsjMnsi7vBzAstvWT2O14claCjxvG+YQN2ZSx4sX1dnZtU\nPdRdvkFD01680+WApwKOhlLf0vUd0s4TsM64QliN/WFwNeV3K5wAJ07XiDYVhoQ10QSPiG4DZEqb\n/CLouBrX5b0LxPMgQtdtOWM9eeRvNG8KCPZ4cPKLUh9kahI7g5xLDhQJhEfaKc+C5dcQ0HzoqXb+\nvlTMzJldSQEgQT5Lfikn7rL8ZuuZxLyD</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor><md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat><md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</md:NameIDFormat><md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="https://dev-410362.oktapreview.com/app/rhlabsdev410362_circle_2/exk4ucst4sA1qzof90h7/sso/saml"/><md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://dev-410362.oktapreview.com/app/rhlabsdev410362_circle_2/exk4ucst4sA1qzof90h7/sso/saml"/></md:IDPSSODescriptor></md:EntityDescriptor>'
