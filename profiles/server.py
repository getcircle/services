import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'profile'

    actions = {
        'create_profile': actions.CreateProfile,
        'bulk_create_profiles': actions.BulkCreateProfiles,
        'update_profile': actions.UpdateProfile,
        'get_profile': actions.GetProfile,
        'get_profiles': actions.GetProfiles,
        'get_extended_profile': actions.GetExtendedProfile,
        'create_skills': actions.CreateSkills,
        'add_skills': actions.AddSkills,
        'get_skills': actions.GetSkills,
        'get_direct_reports': actions.GetDirectReports,
        'get_peers': actions.GetPeers,
        'get_profile_stats': actions.GetProfileStats,
        'get_upcoming_anniversaries': actions.GetUpcomingAnniversaries,
        'get_upcoming_birthdays': actions.GetUpcomingBirthdays,
        'get_recent_hires': actions.GetRecentHires,
        'get_active_skills': actions.GetActiveSkills,
        'get_attributes_for_profiles': actions.GetAttributesForProfiles,
    }
