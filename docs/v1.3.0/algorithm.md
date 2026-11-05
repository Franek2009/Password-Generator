# Advanced generation: exact counts, uniform ranks

Basic random generation preserves the v1.2.0 algorithm and its nonuniform
composition distribution. Passphrase generation is unchanged. The following
proof is specifically for advanced generation; it is not a claim of a uniform
legacy generator or an independent security certification.

## Semantics

Visible ASCII 33–126 is partitioned into U/L/D/S. The custom alphabet intersects
enabled sets; forbidden and similar characters are then subtracted. Duplicates
have no weight. Minima may be zero; no implicit category requirement applies in
advanced mode. First/last types select unions of categories. A run restriction
compares exact, case-sensitive characters. Endpoint characters count toward
minima, including a single position subject to both endpoint restrictions.

## Reference recurrence and uniformity

For a prefix, F(r,d,c,t) counts suffixes of length r satisfying remaining minima
d, the final-position mask, and the run rule after a last character in category
c with run t. At the root, the first-position mask is also applied. F(0,d,c,t)
is 1 iff every deficit is zero. Transitions sum exact counts for every allowed
next character. Characters within a category are symmetric except for the
previous character: multiplicities are 1 for an extension, a_c-1 for another
character in the same category, and a_j for another category.

A rank in [0,N) is drawn using secrets.randbelow / SecureRandom and BigInteger.
Every next character, in ASCII order, owns an interval of size equal to its
completion count. Induction partitions [0,N) into exactly one rank for each
valid word. Therefore each word has probability 1/N. Zero means infeasible;
one is a deterministic consequence of the user's rules. There is no password
rejection, repair or shuffle after sampling. Integer rejection masks excess
bits, rejects values >=N, has no attempt cap and has expected attempts <2.

## Exact elimination of most run states

The direct recurrence passed independent exhaustive tests, but its caches
consumed excessive time/memory. The implementation evaluates the same language
using an algebraic last-run decomposition, with exact signed integer arithmetic.

Let y_i mark a character from category i and a_i be the number of characters.
For one particular character, B_i=y_i+...+y_i^R represents its allowed nonempty
runs. Last-run decomposition gives G_i=B_i*(F-G_i), hence

    H_i = B_i/(1+B_i) = (y_i-y_i^(R+1))/(1-y_i^(R+1))
    G_i = H_i*F
    F = 1 + sum(a_i*G_i).

G_i counts nonempty words ending with one particular character of category i.
Writing q=R+1 gives the finite coefficient recurrence

    G_i(r,d) = F(r-1, down(d,i,1))
             - F(r-q, down(d,i,q))
             + G_i(r-q, down(d,i,q)),

where negative lengths contribute zero. `down` subtracts from the category's
remaining minimum, saturating at zero. Summing coefficients for counts >=d
commutes with each monomial shift, so this works directly with minimum counts.
F(0,d)=1 iff d=0; all G_i(0,d)=0. For r>0,
F(r,d)=sum(a_i*G_i(r,d)). Python/Kotlin cache the F/G tuple together.

For a final category mask E, the nonempty series is

    F_E = sum(i in E, a_i*G_i).

After a previous character of category c already repeated t times, the suffix
series with final mask is

    F_previous,E = ((1-y_c^(q-t))/(1-y_c^q))*F_E
                 + indicator(c in E)*(y_c^q-y_c^(q-t))/(1-y_c^q).

The correction accounts for suffixes consisting entirely of that character;
without it the end-mask boundary would be wrong. The empty-suffix base case is
handled separately. Expanding 1/(1-y^q) requires only shifts up to r, never an
infinite runtime sum. This supplies the exact widths used by rank unranking.
First-position restrictions are handled at the root and when unranking.

Categories of equal size can be permuted in F/G, provided the marked ending
category is remapped too. Endpoint-constrained counts themselves are not
permuted without their masks. A no-run category recurrence is used only when
remaining minima prove no run could exceed R; it is not an approximation or
fallback to the legacy distribution.

## Evidence and gates

`test_advanced.py` uses an independent direct string predicate and exhaustive
ASCII word enumeration. It checks every rank, minima grids, endpoints, runs,
zero/one languages, shared fixtures and huge counts with a multinomial formula.
It also compares the optimized counter to a separate original per-character
state recurrence. Shared fixture counts/ranks use direct enumeration or closed
form, not the production counter. The JVM suite repeats exhaustive enumeration
and shared fixtures, using SecureRandom for integer range checks.

`scripts/benchmark_advanced.py` runs each public case in a fresh process and
reports wall time, process RSS and state count, never a password or prefix.
Android's engine-only benchmark reports actual elapsed time and sampled extra
heap; a passing instrumentation test does not by itself mean the performance
budget passed. Statistical sampling is separate from these exact proofs.

Target: typical <200 ms; hard configurations <=2 s and <=128 MiB extra heap on
the reference phone. Desktop timings are not a substitute for phone evidence.
If this gate fails, stop before preset/UI integration and report the results
for a revised technical decision. No artificial attempt limit or approximation
may conceal an unsatisfied performance gate.
