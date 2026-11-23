"""A pyramid with a triangular base: a temporary Entry for testing inert expressions.

Its base_area and volume are inert expressions, computed when asked for, from whatever the asking call provides.
"""

from math import sqrt


def heron_area(a: float, b: float, c: float) -> float:
    """Return the area of a triangle with sides a, b and c (Heron's formula).

        Usage examples:
            axs byname pyramid , heron_area 3 4 5                                    # => 6.0
            axs byname pyramid , get base_area                                       # => 6.0
            axs byname pyramid , get base_area --a=5 --b=5 --c=6                     # => 12.0
            axs byname pyramid , get base_area --@base_area.named_params.a=5 --a=100 --b=5 --c=6     # => 12.0
            axs byname pyramid , get base_area --@base_area.pos_params.0=5 --b=5 --c=6               # => 12.0
    """
    s = (a + b + c) / 2
    return sqrt( s * (s-a) * (s-b) * (s-c) )


def pyramid_volume(base_area: float, height: float) -> float:
    """Return the volume of a pyramid with the given base area and height.

        Usage examples:
            axs byname pyramid , get volume                                          # => 12.0
            axs byname pyramid , get volume --volume=20                              # => 20
            axs byname pyramid , get volume --base_area=10 --height=5                # => 16.666666666666668
            axs byname pyramid , get volume --a=5 --b=5 --c=6                        # => 24.0
            axs byname pyramid , get volume ---@base_area='["noop", 9]'             # => 18.0
    """
    return base_area * height / 3
