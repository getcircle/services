from protobufs.services.team import containers_pb2 as team_containers


def mock_get_teams(mock_instance, teams, role=None, admin=False, **overrides):
    for team in teams:
        if role == team_containers.TeamMemberV1.COORDINATOR or admin:
            team.permissions.can_edit = True
            team.permissions.can_add = True
            team.permissions.can_delete = True
        elif role is not None:
            team.permissions.can_add = True

    if 'fields' not in overrides:
        overrides['fields'] = {'only': ['permissions']}

    mock_instance.register_mock_object(
        service='team',
        action='get_teams',
        return_object=teams,
        return_object_path='teams',
        ids=[team.id for team in teams],
        **overrides
    )


def mock_get_team(mock_instance, team, role=None, admin=False):
    if role == team_containers.TeamMemberV1.COORDINATOR or admin:
        team.permissions.can_edit = True
        team.permissions.can_add = True
        team.permissions.can_delete = True
    elif role is not None:
        team.permissions.can_add = True

    mock_instance.register_mock_object(
        service='team',
        action='get_team',
        return_object=team,
        return_object_path='team',
        team_id=team.id,
        inflations={'disabled': True},
        fields={'only': ['permissions']},
    )


def mock_get_profile(mock_instance, profile):
    mock_instance.register_mock_object(
        service='profile',
        action='get_profile',
        return_object=profile,
        return_object_path='profile',
        fields={'only': ['is_admin']},
        profile_id=profile.id,
    )
