# sage.doctest: needs sage.combinat sage.modules
"""
Linear Recurrence Sequences

This class implements several methods relating to general linear
recurrence sequences of order d (not necessarily binary).

EXAMPLES::

    sage: T = LinearRecurrenceSequence([0,0,1],[1,1,1])        #the Tribonacci sequence
    sage: T(100)        #the 100th term of the Tribonacci sequence
    53324762928098149064722658
    sage: P = LinearRecurrenceSequence([0,0,0,0,1],[1,1,1,1,1])        #the Pentanacci sequence
    sage: P(100)        #the 100th term of the Pentanacci sequence
    8196759338261258264777004033


AUTHORS:

- Lily McBeath (2024): initial version

- Isabel Vogt (2013): initial version of binary_recurrence_sequences.py

See [SV2013]_, [BMS2006]_, and [SS1983]_.
"""

# ****************************************************************************
#       Copyright (C) 2024 Lily McBeath <mcbeathlc@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  https://www.gnu.org/licenses/
# ****************************************************************************


from sage.structure.sage_object import SageObject
from sage.matrix.berlekamp_massey import berlekamp_massey
from sage.matrix.constructor import matrix
from sage.matrix.special import companion_matrix
from sage.modules.free_module_element import vector
from sage.rings.number_field.number_field import QuadraticField
from sage.rings.finite_rings.integer_mod_ring import Integers
from sage.rings.finite_rings.finite_field_constructor import GF
from sage.rings.integer import Integer
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.arith.functions import lcm
from sage.arith.misc import is_prime, next_prime, next_prime_power, legendre_symbol
from sage.functions.log import log
from sage.misc.functional import sqrt


class LinearRecurrenceSequence(SageObject):
    """
    Create a linear recurrence sequence of order d defined by initial conditions
    `u_0`, ..., `u_{d-1}` and recurrence relation `u_{n+d} = a_0*u_{n+d-1}+...+a_{d-1}*u_n`.

    INPUT:

    - ``a`` -- a list of integers of length d (partially determining the recurrence relation)

    - ``u`` -- a list of integers of length d (the first d terms of the linear recurrence sequence)


    OUTPUT:

    - An integral linear recurrence sequence defined by `u_0`, ..., `u_{d-1}` and recurrence relation `u_{n+d} = a_0*u_{n+d-1}+...+a_{d-1}*u_n`

    EXAMPLES::

        sage: T = LinearRecurrenceSequence([0,0,1],[1,1,1])
        sage: T
        Linear recurrence sequence defined by: u_{n+3} = 1*u_{n+2} + 1*u_{n+1} + 1*u_{n+0};
        With initial conditions: u_0 = 0, u_1 = 0, u_2 = 1

    """

    def __init__(self, u, a):
        """
        See :class:`LinearRecurrenceSequence` for full documentation.

        EXAMPLES::

            sage: R = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: R
            Linear recurrence sequence defined by: u_{n+3} = -2*u_{n+2} + 1*u_{n+1} + 2*u_{n+0};
            With initial conditions: u_0 = 0, u_1 = 1, u_2 = 2

        If the order given does not match the length of the lists given, an error will occur::

            sage: S = LinearRecurrenceSequence([0,1,1,2],[-2,1,2])
            Traceback (most recent call last):
            ...
            ValueError: length of initial conditions list u must match length of definition list a
            
        If an order of 1 or less is given, a NotImplemented error will be produced::

            sage: LinearRecurrenceSequence([1],[2])
            Traceback (most recent call last):
            ...
            NotImplementedError: not implemented for order d < 2
            
        For Binary recurrence sequences, use ``BinaryRecurrenceSequence``::

            sage: T = LinearRecurrenceSequence([0,1],[1,1])
            Traceback (most recent call last):
            ...
            NotImplementedError: use BinaryRecurrenceSequence for recurrence sequences of order 2

        """
        self.u = u
        self.a = a
        self.d = len(u)
        if len(u) != len(a):
            raise ValueError("length of initial conditions list u must match length of definition list a")
        elif self.d < 3:
            if self.d < 2:
                raise NotImplementedError("not implemented for order d < 2")
            else:
                raise NotImplementedError("use BinaryRecurrenceSequence for recurrence sequences of order 2")

    def __repr__(self):
        """
        Give string representation of the class.

        EXAMPLES::

            sage: P = LinearRecurrenceSequence([0,0,0,0,1],[1,1,1,1,1])
            sage: P
            Linear recurrence sequence defined by: u_{n+5} = 1*u_{n+4} + 1*u_{n+3} + 1*u_{n+2} + 1*u_{n+1} + 1*u_{n+0};
            With initial conditions: u_0 = 0, u_1 = 0, u_2 = 0, u_3 = 0, u_4 = 1

        """
        initial = ", ".join(f"u_{i} = {self.u[i]}" for i in range(self.d))
        definition = " + ".join(f"{self.a[i]}*u_{{n+{self.d-i-1}}}" for i in range(self.d))
        return f"Linear recurrence sequence defined by: u_{{n+{self.d}}} = {definition};\nWith initial conditions: {initial}"

    def __eq__(self, other):
        """
        Compare two binary recurrence sequences.

        EXAMPLES::

            sage: R = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: S = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: R == S
            True

            sage: T = LinearRecurrenceSequence([0,0,1],[-2,1,2])
            sage: R == T
            False
        """
        return (self.u == other.u) and (self.a == other.a)

    def __call__(self, n, modulus=0):
        """
        Give the nth term of a linear recurrence sequence, possibly mod some modulus.

        INPUT:

        - ``n`` -- an integer (the index of the term in the linear recurrence sequence)

        - ``modulus`` -- a natural number (optional --  default value is 0)

        OUTPUT:

        - An integer (the nth term of the linear recurrence sequence modulo ``modulus``)

        EXAMPLES::

            sage: R = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: R(2)
            2
            sage: R(100)
            845100400152152934331135470250
            sage: R(100,12)
            10
            sage: R(100)%12
            10
        """
        R = Integers(modulus)
        charpoly = [-c for c in reversed(self.a)]+[1]
        F = companion_matrix(charpoly, format='bottom').change_ring(R)
        # F*[u_{n}, ..., u_{n+d-1}]^T = [u_{n+1}, ..., u_{n+d}]^T (T indicates transpose).
        v = vector(R, self.u)
        return list(F**n * v)[0]

    def characteristic_polynomial(self):
        """
        Give the characteristic polynomial associated to the linear recurrence sequence.

        EXAMPLES::

            sage: R = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: R.characteristic_polynomial()
            x^3 + 2*x^2 - x - 2
        """
        R = PolynomialRing(Integers(),'x')
        charpoly = R([-c for c in reversed(self.a)]+[1])
        return charpoly

    def minimal_polynomial(self):
        """
        Give the minimal polynomial associated to the linear recurrence sequence using the Berlekamp-Massey algorithm.

        EXAMPLES::

            sage: R = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: R.minimal_polynomial()
            x^3 + 2*x^2 - x - 2
        """
        input = self.u+[self(self.d+i) for i in range(self.d)]
        return berlekamp_massey(input)

    def transformation_matrix(self):
        """
        Give the transformation matrix associated to the linear recurrence sequence.

        EXAMPLES::

            sage: R = LinearRecurrenceSequence([0,1,2],[-2,1,2])
            sage: R.transformation_matrix()
            [ 0  1  0]
            [ 0  0  1]
            [ 2  1 -2]
        """
        charpoly = [-c for c in reversed(self.a)]+[1]
        T = companion_matrix(charpoly, format='bottom')
        return T
