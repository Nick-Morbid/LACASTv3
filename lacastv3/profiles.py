"""Explicit generator profiles for reproducible execution evidence."""
from .generator import SQLGenerator
from .context_generator import ContextSQLGenerator


def generator_class(profile):
    if profile == 'baseline':
        return SQLGenerator
    if profile == 'expanded':
        return ContextSQLGenerator
    raise ValueError(f'Unknown generation profile: {profile}')
