
"""
The aim of this module is to store helper functions,
not specific to fixture processing.
"""


def iter_dict_values(dictionary_arg: dict)

"""
    Very often when iterating through a dictionary,
    the value is a list or another sort of iterator,
    and that is then iterated on.

    This creates an unnecessary indentation.
    """

for key, item_iterable in dictionary_arg.items():

    for item in item_iterable:
        yield key, item
