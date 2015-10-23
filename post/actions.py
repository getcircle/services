import service.control
from service import (
    actions,
    validators,
)

from services.mixins import PreRunParseTokenMixin
from services.utils import should_inflate_field


class CreatePost(actions.Action):

    def run(self, *args, **kwargs):
        pass


class UpdatePost(actions.Action):

    def run(self, *args, **kwargs):
        pass


class GetPost(actions.Action):

    def run(self, *args, **kwargs):
        pass


class GetPosts(actions.Action):

    def run(self, *args, **kwargs):
        pass


class DeletePost(actions.Action):

    def run(self, *args, **kwargs):
        pass
