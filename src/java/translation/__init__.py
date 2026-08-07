__all__ = [
    'create_skeleton_main',
    'run_compositional_translation_validation',
    'cangjie_compilation_validation',
    'PromptGenerator',
]


def __getattr__(name):
    """Load pipeline entry points only when their type-resolution seam is used."""
    if name == 'create_skeleton_main':
        from .create_skeleton import main
        return main
    if name == 'run_compositional_translation_validation':
        from .compositional_translation_validation import main
        return main
    if name == 'cangjie_compilation_validation':
        from .cangjie_compilation_validation import cangjie_compilation_validation
        return cangjie_compilation_validation
    if name == 'PromptGenerator':
        from .prompt_generator import PromptGenerator
        return PromptGenerator
    raise AttributeError(name)
