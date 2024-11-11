# anonymization_tool/anonymization_factory.py

from .anonymizationEngine import (
    pseudonymize_sha256,
    generalize_to_range,
    create_consistent_swap_mapping,
)

class AnonymizationFactory:
    @staticmethod
    def get_anonymization_method(method, **kwargs):
        if method == 'sha256':
            return pseudonymize_sha256
        elif method == 'generalize':
            range_size = kwargs.get('range_size', 10)
            return lambda x: generalize_to_range(x, range_size)
        elif method == 'swap':
            swap_mapping = kwargs.get('swap_mapping', {})
            return lambda x: swap_mapping.get(x, x)
        else:
            return lambda x: x 