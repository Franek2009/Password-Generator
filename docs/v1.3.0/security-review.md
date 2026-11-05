# Final technical review — v1.3.0

The final release review examined the advanced-generation implementation and
its verification evidence. No blocking defect was identified; runtime code and
public interfaces were left unchanged. Signing, licensing and the release
workflow remain unchanged. The owner accepted Windows/Android manual results
and emulator performance as the release criteria.

* The classic generator and passphrase generator retain their original algorithms.
  Advanced generation uses `secrets.randbelow` / `SecureRandom`, with exact integer
  arithmetic. No floats, modulo reduction, password repair, password rejection
  caps or noncryptographic PRNG enter the advanced sampling path.
* Uniformity is justified by a rank-to-string bijection. Optimized completion
  counts are checked against independent enumeration and a direct reference
  recurrence. The algebra and optimization boundaries are documented separately.
* Filters are literal, case-sensitive ASCII intersections/subtractions. Deduped
  characters have equal weight. Disabled pools cannot supply minima or endpoints.
  Zero-count languages are errors; singleton languages are allowed with a warning.
* Counting caches are local to one request and contain rule-derived integer
  states, never actual prefixes or generated results. They are cleared in finally/
  close paths. The implementation does not promise reliable erasure of immutable
  strings or BigInteger/int objects from managed-runtime memory.
* CPU work stays off the main thread. Configuration revisions cancel computation
  and prevent stale publication or automatic copying; mode changes clear results.
  Cancellation is distinct from infeasibility. App/ViewModel shutdown invalidates
  pending requests. Appearance/transcription changes do not regenerate passwords.
* Preset/preferences serialization uses explicit field whitelists. Regression
  tests seed public sentinels and verify that generated results and their fragments
  do not enter persistent settings. Preset writes are checked before list mutation.
* No network communication, telemetry, result logging, history, account, import/
  export or password store was added. Screenshot harnesses use public forced
  examples with no practical password value; benchmark logs contain public rule
  parameters, time/memory/state statistics only.

## Final verification record

* Reviewed Python and Kotlin alphabet compilation, exact completion counting,
  unranking and integer range sampling against the mathematical argument and
  independent exhaustive/rank fixtures. Signed intermediate count arithmetic
  stays exact; optimizations preserve the endpoint/run constraints.
* Reviewed strict preset schemas, lazy v1 migration, no fallback from corrupt v2,
  checked writes, unavailable custom dictionaries and URI errors.
* Reviewed configuration revisions, cancellation/cleanup paths and publication
  guards: switching modes cannot restore an old pending result or auto-copy it.
* Reviewed raw-copy paths and serialization whitelists; no password result,
  fragment, prefix, random rank or completion count is persisted or logged.
* Re-ran the full Python suite for release preparation: [268 passed](evidence/release-python-tests.txt). Existing CI
  covers 22 JVM tests, lint/builds, instrumented UI on API 26/35 and packaged
  Linux startup. See the [verification report](README.md) for evidence links.
* The owner confirmed the latest application builds on Windows and physical
  Android, including the readability fix. No runtime change was made during
  this review, so those application binaries remain applicable.
* Physical-phone timing/memory measurements are deferred by the owner. The
  performance evidence is explicitly from the emulator. Manual screen-reader
  sessions and Android storage-failure injection remain unmeasured.

The review uses the existing rank-bijection argument and executable oracles;
it does not infer uniformity from statistical tests alone. The classic generator
retains its previous composition distribution. No additional features, schema
migration, dependency upgrades or cryptographic replacements were introduced.
