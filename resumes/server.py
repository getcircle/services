import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'resume'

    actions = {
        'bulk_create_educations': actions.BulkCreateEducations,
        'bulk_create_positions': actions.BulkCreatePositions,
        'create_company': actions.CreateCompany,
        'get_resume': actions.GetResume,
        'bulk_create_companies': actions.BulkCreateCompanies,
    }
