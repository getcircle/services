from django.views.generic.base import TemplateView


class AuthSuccessView(TemplateView):
    template_name = 'auth-success.html'


class AuthErrorView(TemplateView):
    template_name = 'auth-error.html'
