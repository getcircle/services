from service import actions


POSTS_FEATURE = 'posts'


class GetFlags(actions.Action):

    def run(self, *args, **kwargs):
        self.response.flags[POSTS_FEATURE] = True
