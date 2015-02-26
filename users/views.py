from django.views.generic.base import TemplateView

from .providers import LinkedIn


class ConnectLinkedInView(TemplateView):

    template_name = 'linkedin-connect.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ConnectLinkedInView, self).get_context_data(*args, **kwargs)
        context['linkedin_url'] = LinkedIn.get_authorization_url(additional_scopes='r_network')
        return context
