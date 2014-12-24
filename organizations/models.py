from common.db import models


class LTreeField(models.Field):

    def db_type(self, connection):
        return 'ltree'


class Organization(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=64, unique=True)


class Team(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=256)
    owner_id = models.UUIDField()
    organization = models.ForeignKey(Organization)
    path = LTreeField(null=True)

    def get_path(self):
        path_parts = self.path.split('.')
        names = Team.objects.filter(pk__in=path_parts).values_list(
            'id',
            'name',
        )
        name_dict = dict((k.hex, v) for k, v in names)
        return [name_dict[p] for p in path_parts]


class TeamMembership(models.UUIDModel, models.TimestampableModel):

    team = models.ForeignKey(Team)
    user_id = models.UUIDField()

    class Meta:
        unique_together = ('team', 'user_id')
