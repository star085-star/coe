# Accessibility and Multilingual Design

## Multilingual
* **Input:** operator notes in English, Tanglish (romanised Tamil) and Tamil script. Handled by a short, auditable concept lexicon
  (`src/features/text_features.py`) plus character n-gram TF-IDF, which tolerates typos and unseen spellings. Language is detected and shown.
* **Measured:** accuracy by note language is reported in `reports/error_analysis.md` (Tamil/Tanglish are not worse than English on the synthetic data).
* **UI:** English/Tamil toggle for all labels and cause names; Tamil font fallbacks; `lang` attribute is switched so screen readers pronounce correctly.
* **Not done / honest limits:** Tamil strings were written by the developer, not professionally translated, so a native-speaker review is needed. Recommended-action text is English only. Notes are
  synthetic, real shop-floor language (code-mixing, abbreviations, voice) will be messier. Voice-to-text input is future work.

## Accessibility (WCAG 2.1 AA oriented)
* Semantic landmarks, skip link, tab pattern with arrow-key navigation, real `<table>` with `<caption>`/`scope`, labelled form controls.
* Status never conveyed by colour alone (icons + text: ✔ Verified / ✖ Not effective / ? Inconclusive).
* High-contrast mode, text-size controls (A+/A−), 44 px minimum targets, visible focus ring, `prefers-reduced-motion` respected, `aria-live` for results.
* Low-literacy / glove-friendly: large buttons, selects instead of typing for structured fields, a note is optional.
* **Not yet tested** with a real screen reader or with operators wearing gloves; this is listed as a validation task.
