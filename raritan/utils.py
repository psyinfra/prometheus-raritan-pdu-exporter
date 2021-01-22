import re


def camel_to_snake(label: str) -> str:
    """Convert camelCase strings to snake_case"""
    label = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', label)
    label = re.sub('([a-z0-9])([A-Z])', r'\1_\2', label).lower()
    return label
