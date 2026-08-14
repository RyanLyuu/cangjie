__all__ = [
    'create_skeleton_main',
]


def __getattr__(name):
    """Load pipeline entry points only when their type-resolution seam is used."""
    if name == 'create_skeleton_main':
        from .create_skeleton import main
        return main
    raise AttributeError(name)
