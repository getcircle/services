import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'post'

    actions = {
        'create_post': actions.CreatePost,
        'update_post': actions.UpdatePost,
        'get_post': actions.GetPost,
        'get_posts': actions.GetPosts,
        'delete_post': actions.DeletePost,
    }
