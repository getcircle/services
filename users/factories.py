import factory


class UserFactory(factory.DjangoModelFactory):

    class Meta:
        model = 'users.User'
