import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'profile'

    auth_exempt_actions = (
        'profile_exists',
    )

    actions = {
        'create_profile': actions.CreateProfile,
        'bulk_create_profiles': actions.BulkCreateProfiles,
        'update_profile': actions.UpdateProfile,
        'get_profile': actions.GetProfile,
        'get_profiles': actions.GetProfiles,
        'get_extended_profile': actions.GetExtendedProfile,
        'create_tags': actions.CreateTags,
        'add_tags': actions.AddTags,
        'remove_tags': actions.RemoveTags,
        'get_tags': actions.GetTags,
        'get_upcoming_anniversaries': actions.GetUpcomingAnniversaries,
        'get_upcoming_birthdays': actions.GetUpcomingBirthdays,
        'get_recent_hires': actions.GetRecentHires,
        'get_active_tags': actions.GetActiveTags,
        'profile_exists': actions.ProfileExists,
        'get_status': actions.GetStatus,
    }
