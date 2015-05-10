from factory import Factory
from services.test import factory


class BaseObject(object):

    def __init__(self, *args, **kwargs):
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def as_dict(self):
        output = {}
        for attr in dir(self):
            if not attr.startswith('_'):
                value = getattr(self, attr)
                if not callable(value):
                    output[attr] = value
        return output


class GoogleGroupSettings(BaseObject):
    kind = 'groupsSettings#groups'


class GoogleGroup(BaseObject):
    kind = 'admin#directory#groups'


class GoogleGroupMember(BaseObject):
    kind = 'admin#directory#member'


class GoogleGroupSettingsFactory(Factory):
    class Meta:
        model = GoogleGroupSettings

    email = factory.FuzzyText(suffix='@circlehq.co')
    description = factory.FuzzyText()
    allowExternalMembers = factory.FuzzyChoice([False, True])
    showInGroupDirectory = factory.FuzzyChoice([False, True])
    whoCanJoin = factory.FuzzyChoice([
        'ANYONE_CAN_JOIN',
        'ALL_IN_DOMAIN_CAN_JOIN',
        'INVITED_CAN_JOIN',
        'CAN_REQUEST_TO_JOIN',
    ])
    whoCanViewMembership = factory.FuzzyChoice([
        'ALL_IN_DOMAIN_CAN_VIEW',
        'ALL_MEMBERS_CAN_VIEW',
        'ALL_MANAGERS_CAN_VIEW',
    ])
    whoCanViewGroup = factory.FuzzyChoice([
        'ANYONE_CAN_VIEW',
        'ALL_IN_DOMAIN_CAN_VIEW',
        'ALL_MEMBERS_CAN_VIEW',
        'ALL_MANAGERS_CAN_VIEW',
    ])
    whoCanInvite = factory.FuzzyChoice([
        'ALL_MEMBERS_CAN_INVITE',
        'ALL_MANAGERS_CAN_INVITE',
    ])


class GoogleGroupFactory(Factory):
    class Meta:
        model = GoogleGroup

    etag = factory.FuzzyUUID()
    name = factory.FuzzyText()
    adminCreated = True
    directMembersCount = factory.FuzzyInteger(100)
    email = factory.FuzzyText(suffix='@circlehq.co')
    id = factory.FuzzyText()
    description = factory.FuzzyText()
    nonEditableAliases = factory.List([factory.SelfAttribute('..email')])
    settings = factory.SubFactory(
        GoogleGroupSettingsFactory,
        email=factory.SelfAttribute('..email'),
    )


class GoogleGroupMemberFactory(Factory):
    class Meta:
        model = GoogleGroupMember

    email = factory.FuzzyText(suffix='@circlehq.co')
    etag = factory.FuzzyUUID()
    role = factory.FuzzyChoice([
        'MEMBER',
        'OWNER',
        'MANAGER',
    ])
    type = 'USER'
    id = factory.FuzzyUUID()


class GoogleProviderGroupsFactory(object):

    def __init__(self, groups):
        self.kind = 'admin#directory#groups'
        self.etag = factory.FuzzyUUID().fuzz()
        self.groups = map(lambda x: x.as_dict(), groups)

    def as_dict(self):
        return {'kind': self.kind, 'etag': self.etag, 'groups': self.groups}
