# Architecture Notes

- [ ] Multilingual STT options (investigation only):
  - Browser-native Web Speech `lang` switching (lowest effort, Chrome-dependent).
  - Server-side STT service fallback for non-Chrome/unsupported locales.
  - Hybrid approach: browser-first with server fallback on unsupported language/runtime.

- [ ] Frontend framework migration study:
  - Current app is Flask templates + vanilla JS.
  - Evaluate migration cost to React (routing/state/componentization/build tooling).
  - Propose incremental migration path if complexity justifies it.
