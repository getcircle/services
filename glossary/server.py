import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'glossary'

    actions = {
        'create_term': actions.CreateTerm,
        'update_term': actions.UpdateTerm,
        'get_term': actions.GetTerm,
        'get_terms': actions.GetTerms,
        'delete_term': actions.DeleteTerm,
    }
