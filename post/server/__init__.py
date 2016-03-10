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
        'create_collection': actions.CreateCollection,
        'delete_collection': actions.DeleteCollection,
        'reorder_collection': actions.ReorderCollection,
        'reorder_collections': actions.ReorderCollections,
        'add_to_collections': actions.AddToCollections,
        'remove_from_collections': actions.RemoveFromCollections,
        'update_collection': actions.UpdateCollection,
        'get_collections': actions.GetCollections,
        'get_collection': actions.GetCollection,
        'get_collection_items': actions.GetCollectionItems,
    }
