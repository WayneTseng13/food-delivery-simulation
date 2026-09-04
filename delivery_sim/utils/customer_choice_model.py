# delivery_sim/utils/customer_choice_model.py
"""
Customer restaurant choice under a distance-based random-utility (softmax) model.

The customer assigns each restaurant R a utility

    u(R) = -beta * d(R, C) + b * s(R) + eps(R)

where d(R, C) is the delivery-leg distance from R to the customer C, s(R) is 1
for the single restaurant the platform slotted (boosted) and 0 otherwise, b is
the boost strength, and eps(R) is iid Gumbel noise. Marginalizing the Gumbel
noise gives a softmax (multinomial logit) over restaurants:

    P(R) = exp(-beta*d(R,C) + b*s(R)) / sum_k exp(-beta*d(R_k,C) + b*s(R_k))

The customer samples one restaurant from P. The Gumbel noise never appears in
code -- the softmax IS the marginalized object.

Parameters
----------
beta  (>= 0, units 1/km) : proximity sensitivity.
        beta = 0     -> distance ignored; unslotted choice is uniform over all
                        restaurants (the 1/N floor).
        beta large   -> the customer almost always takes their nearest.
b     (>= 0)             : boost the slotted restaurant receives.
        b = 0        -> no steering (the slot has no effect).

Endogenous compliance
---------------------
There is no exogenous compliance constant. "Compliance" -- the chance the
customer takes the slotted restaurant -- is just P(slotted), an OUTPUT of
(beta, b, which restaurant was slotted, where the customer is). It rides beta
when the slot is near the customer and fights beta when the slot is far, so
featuring a distant restaurant self-limits.

Nesting / regression identity
-----------------------------
At beta = 0 with a slotted restaurant, the softmax mass on that restaurant is
exactly

    P(slotted) = e^b / (e^b + N - 1)

so this model reproduces the old constant-compliance-p (with uniform fallback
over the other N-1) model EXACTLY, with

    p = e^b / (e^b + N - 1)   <=>   b = ln( p*(N-1) / (1-p) ).

This is an exact identity, asserted directly in the tests, so the old constant-p
code path need not be kept alive to validate against.
"""

import math

from delivery_sim.utils.location_utils import calculate_distance


class CustomerChoiceModel:

    def __init__(self, beta, b, selection_stream):
        if beta < 0:
            raise ValueError(f"beta (distance sensitivity) must be >= 0, got {beta}.")
        if b < 0:
            raise ValueError(f"b (recommendation boost) must be >= 0, got {b}.")
        self.beta = beta
        self.b = b
        self.selection_stream = selection_stream

    def choice_probabilities(self, customer_location, restaurants, boost_id):
        """
        Softmax probability vector over `restaurants`, aligned to their order.

        boost_id is the restaurant_id of the slotted restaurant (b applied), or
        None when nothing is slotted (Policy U). Pure function of its arguments:
        consumes no randomness, so it is safe to call for offline calibration and
        diagnostics without perturbing any RNG stream.
        """
        # Linear utilities. Numerically stabilized by subtracting the max before
        # exponentiating (shifts cancel in the normalization).
        utilities = []
        for r in restaurants:
            u = -self.beta * calculate_distance(r.location, customer_location)
            if boost_id is not None and r.restaurant_id == boost_id:
                u += self.b
            utilities.append(u)

        u_max = max(utilities)
        weights = [math.exp(u - u_max) for u in utilities]
        total = sum(weights)
        return [w / total for w in weights]

    def select(self, customer_location, restaurants, boost_id):
        """
        Sample one restaurant from the softmax, consuming exactly one draw from
        the selection stream. Returns the chosen Restaurant.

        This single draw replaces BOTH the old uniform restaurant draw (U) and
        the old compliance-coin-plus-uniform-fallback (curated). One arrival ->
        one draw on the selection stream, every policy.
        """
        probs = self.choice_probabilities(customer_location, restaurants, boost_id)
        idx = self.selection_stream.choice(len(restaurants), p=probs)
        return restaurants[idx]