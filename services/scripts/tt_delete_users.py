from django.db import transaction

from users.models import User
from profiles.models import Profile
from post.models import Post
from organizations.models import (
    ReportingStructure,
    LocationMember,
)


users_to_delete = ['83f73571-d634-4133-9fb6-fcedc0090866', 'e5a05334-41a4-4daf-89ea-6ae8dc345e89', '41efd0cf-a1ac-4d88-902c-5b858bcac168', '66c500a4-d499-4d54-aed6-94d643e98884', '4dff221e-b444-4cbd-a5ca-578c1a326032', '6b978a58-54df-4ce0-a85a-3028c9daf732', '33a22ae0-8bc0-41a6-8d8f-e66afbb38fc8', '8cb21cb5-946f-4733-b764-74f71d9fdd82', '4dff0505-9f98-421e-b0da-7933dd86a481', 'ed98bdde-1b6e-4b9c-99e6-4e7eb7566f27', 'f03429c6-8a4b-46af-b834-7a9972a07351', '76aac8e3-9cc5-4e08-9327-393efdac3286', '3ea6e06a-234a-49cf-9135-fadfdb9081b5', 'e79eb395-eca3-41fc-b3fe-8ebfb35c8528', '273a85e3-c30f-46e1-b067-ee7957a2682e', '768005da-5f34-4632-9e44-5bbd630e92e2', '5b40f49a-1eba-4d3b-9601-819a64445652', '5dca0b2c-7e87-4dfb-a785-5fe500106291', '03ec486b-3080-47b9-bba4-a1190144d6dd', '18493c49-8031-466b-8fc3-07af4f6030bc', 'cc3cb2a8-3d57-4d9b-988f-d62ffbf458b0', '6952bb2d-9016-407c-9bb0-03f70b317204', 'c75674b4-c232-4247-a5fe-04ae2247ea87', 'ac8fa445-c3d4-4d5f-8d76-d0dd47ea0962', 'd1db45f6-f041-48d5-94f2-3591ca741795', 'fe83be23-b8e1-4899-9d00-9b4e35bce3be', '49f7621e-56ff-4bd5-b4fe-a52a7f2add2f', 'a22b4dfa-a6ed-4acb-93b0-f5f0a929e36f', '8bb58712-ccf8-4f7f-841c-3499f727f41b', 'd221fa4b-02cd-4e1a-9d59-8fb573838890', 'ac0ff696-7a7b-473c-bfc2-1d50967e0c7a']


@transaction.atomic
def delete_profile_id(profile_id):
    #try:
        #profile = Profile.objects.get(pk=profile_id)
    #except Profile.DoesNotExist:
        #print 'profile: %s already deleted' % (profile_id,)
        #return

    #user = User.objects.get(pk=profile.user_id)
    #if Post.objects.filter(by_profile_id=profile.id).exists():
        #print 'posts exist for user: %s, refusing to delete' % (profile.as_dict(),)

    try:
        report = ReportingStructure.objects.get(profile_id=profile_id)
    except ReportingStructure.DoesNotExist:
        report = None

    members = LocationMember.objects.filter(profile_id=profile_id)
    print 'delete user:\nuser data:%s\nprofile data:%s\n%s\n%s' % (None, None, report, members)
    confirmation = raw_input('y/n/exit: ')
    if confirmation == 'y':
        print 'deleting user...'
        #user.delete()
        #profile.delete()
        if report:
            report.delete()
        if members:
            members.delete()
    elif confirmation == 'exit':
        raise Exception()
    else:
        print 'keeping user...'


def run():
    for profile_id in users_to_delete:
        delete_profile_id(profile_id)
