# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""A module provides a function to convert a variable of type Any to a concrete type.

Inevitably, variables of type Any may occur, and such variables cannot be handled
in type checkers in strict mode. Any is allowed only in the module here.
"""

import sys
from collections.abc import Iterator
from typing import (
    Any,  # Any is allowed only in the module here.
    Optional,
)


def to_object(  # type: ignore[explicit-any]
    any_object: Any,  # noqa: ANN401  # Any is allowed only in the module here.
) -> object:
    # Interpret Unknown as object
    # https://github.com/microsoft/pyright/issues/3650
    if not isinstance(any_object, object):
        if sys.version_info >= (3, 11):
            from typing import assert_never

            assert_never(any_object)
        raise TypeError
    return any_object


def iterator_to_object_iterator(  # type: ignore[explicit-any]
    any_iterator: Any,  # noqa: ANN401  # Any is allowed only in the module here.
) -> Optional[Iterator[object]]:
    any_iterator_without_partial_type_narrowing = any_iterator
    if not isinstance(any_iterator, Iterator):
        return None
    return map(to_object, any_iterator_without_partial_type_narrowing)
