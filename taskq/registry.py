"""A tiny task registry. Handlers register themselves with @task("name")."""

_REGISTRY = {}


def task(name):
    def decorator(fn):
        if name in _REGISTRY:
            raise ValueError(f"task '{name}' is already registered")
        _REGISTRY[name] = fn
        return fn
    return decorator


def get_handler(name):
    if name not in _REGISTRY:
        raise KeyError(f"no handler registered for task '{name}'")
    return _REGISTRY[name]


def is_registered(name):
    return name in _REGISTRY


def registered_tasks():
    return sorted(_REGISTRY)
