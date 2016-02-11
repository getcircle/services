from protobufs.services.team import containers_pb2 as team_containers


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
