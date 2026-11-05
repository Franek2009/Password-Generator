# Preset and preference compatibility

Preset records contain only a whitelisted active-mode generator configuration.
They never contain a generated password, rank, completion count, clipboard,
history, theme or language. The advanced object has strict field/type/range
validation; alphabets are canonicalized by deduplicating and sorting ASCII.

Version 1 comes from `presets`; version 2 is written to `presets_v2`. When the
new key is absent, legacy records are read and given disabled advanced defaults
in memory. Reading alone never rewrites them. The first successful save/delete
writes the complete version-2 collection to the new key, leaving the old key
untouched for downgrade compatibility. Further edits in one version do not
synchronize with the other.

If `presets_v2` exists, it is authoritative even if corrupt; silently returning
to the legacy collection could resurrect deleted entries. Invalid records are
skipped individually and reported. Unknown future root versions block writing.
Both implementations protect built-in IDs/names and reject extra configuration
fields. Android bounds JSON nesting before parsing to avoid recursive parser
failure. Python handles parser recursion errors without replacing stored data.

Structural validation and cheap contradictions are checked during reading.
Exact feasibility is checked in a cancellable background task before applying
or saving an advanced preset. A failed application preserves the current mode,
controls and result. A lost custom-dictionary path or Android URI permission is
an error, with no substitution. Applying any valid preset clears the result and
never starts generation or automatic copying.

Preset save/delete waits for the storage result before updating the in-memory
collection. Python checks QSettings synchronization status; Android checks
SharedPreferences commit on an IO dispatcher. A failed write is reported. No
cross-platform preset import, export or synchronization is implemented.

Advanced preferences use `advanced_rules_v1`, separate from the legacy settings.
Malformed saved rules are reported and left intact during startup. In-progress
invalid text remains visible for correction and is not persisted over the last
valid rule object. Disabling advanced mode remains possible with invalid text;
it persists the last valid draft with advanced mode disabled. Ordinary mode
ignores that invalid draft. Valid inactive rule drafts can still be saved in a
random-mode preset. Expanding/collapsing the section is independent of opting in.
