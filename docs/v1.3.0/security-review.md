# Implementation review — advanced generation

This is a developer review checklist with evidence, not an independent audit
or certification. Release metadata, signing, licensing and the release workflow
are unchanged. The owner must still obtain the intended independent audit.

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

Remaining validation includes physical-phone performance and native Windows
execution. An emulator is useful evidence, but is not the reference phone.
