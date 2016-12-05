from organizations.models import (
    Team,
    ReportingStructure,
)

ORGANIZATION_ID = '4d3ec6da-1c34-4880-bc92-a2ec7d35b073'


def run():
    teams = Team.objects.filter(organization_id=ORGANIZATION_ID)
    for team in teams:
        node = ReportingStructure.objects.get(
            pk=team.manager_profile_id,
            organization_id=ORGANIZATION_ID,
        )
        if not node.get_descendant_count():
            confirm = raw_input('should delete team: %s, y/n: ' % (team.as_dict(),))
            if confirm == 'y':
                print 'deleting team..'
                team.delete()
            else:
                print 'not deleting team...'
