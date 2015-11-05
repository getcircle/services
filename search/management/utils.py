import service.control

PAGE_SIZE = 100


def execute_handler_on_paginated_items(
        token,
        service_name,
        action,
        return_object_path,
        handler,
        action_kwargs=None,
        **kwargs
    ):
    if not action_kwargs:
        action_kwargs = {}

    client = service.control.Client(service_name, token=token)
    next_page = 1
    while next_page:
        response = client.call_action(
            action,
            control={'paginator': {'page': next_page, 'page_size': PAGE_SIZE}},
            **action_kwargs
        )
        items = getattr(response.result, return_object_path)
        if not items:
            print 'no items found for %s:%s' % (service_name, action)
            break

        handler(items, token=token, **kwargs)
        if response.control.paginator.page != response.control.paginator.total_pages:
            next_page = response.control.paginator.next_page
        else:
            break
