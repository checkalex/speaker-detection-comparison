# Speaker detection, measured

A static, presentation-ready evaluation of **pyannote Precision-3** and **NVIDIA Nemotron 3 Diarization**, updated on 2 November 2026 with five completed English recordings: three animation excerpts and two Friends compilations. Shrek remains excluded while its reviewed reference is pending.

Published report: **https://checkalex.github.io/speaker-detection-comparison/**

## Findings

| Recording | Precision-3 DER | NVIDIA DER | Reference speaker count |
| --- | ---: | ---: | ---: |
| Dave the Barbarian | 36.06% | 47.24% | 11 |
| Pizza Delivery | 43.80% | 45.11% | 5 |
| Veronica Having Bad Luck | 69.08% | 67.60% | 8 |
| Friends: Funniest Moments | 78.98% | 45.55% | 8 |
| Friends: Christmas Episodes | 56.01% | 25.83% | 9 |
| Weighted overall | 58.34% | **41.38%** | |

NVIDIA leads total DER, mainly through fewer detections outside the subtitle reference. Precision-3 has less wrong-speaker time in every clip: **139.68 seconds total versus 203.66 seconds for NVIDIA**. Keep Precision-3 as the provisional baseline for speaker assignment while validating actual speech boundaries independently.

Dave and Friends Christmas exceed NVIDIA's documented eight-speaker capacity. On the three clips within that limit, weighted DER is **67.71% for Precision-3 versus 50.59% for NVIDIA**.

All five references are model-assisted and then human-reviewed. The first four began with Checksub’s original subtitle exports and speaker assignments, which may favor the Checksub/Precision-3 baseline. Friends Christmas began with NVIDIA speaker labels, which may favor NVIDIA’s measured agreement. All five retain cue times from Checksub’s transcription/alignment pipeline; these timings were not independently supplied by either diarization model. The per-recording cards and methodology explain the potential bias in both directions. Speech boundaries were not independently annotated. Only Dave's two chorus intervals explicitly annotate simultaneous voices; the brief overlapping subtitle intervals in Christmas are shown separately as unconfirmed overlap.

## What's included

- An executive summary, provisional conclusion and next steps.
- Standalone SVG and PNG figures created with Matplotlib.
- Responsive comparisons by recording, error type and speaker count.
- An interactive speaker-count timeline with exact overlap-event windows, keyboard-accessible time slider, and optional timeline animation.
- A capacity-aware subset analysis and explanation of DER.
- Downloadable result CSV, sanitized measurements and activity timelines.
- Print styles for saving the report as PDF.

No source audio, transcript text, API credentials, service job identifiers, or absolute local paths are published. This repository contains only the report, its derived data and build scripts. The report does not send data to external services and uses locally hosted fonts under their included SIL Open Font Licenses.

## Preview

```bash
python3 -m http.server 8767 --bind 127.0.0.1 --directory site
```

Open http://localhost:8767/. The report is also usable directly from `site/index.html`; data is loaded as a local JavaScript file rather than fetched from an API.

## Rebuild

The data builder reads an existing run produced by the separate `speaker-detector-benchmark` tool. It uses that tool's `bench.py` and Python environment to validate references and score results. It does not submit new inference jobs.

```bash
../speaker-detector-benchmark/.venv/bin/python build_data.py \
  ../speaker-detector-benchmark/runs/comparison
python3 build_charts.py
```

`build_charts.py` requires Matplotlib and NumPy. The report is a frozen study: if source results change, update the written numerical summary and conclusion alongside the charts. The builder publishes only its five explicitly selected recordings and computes aggregates from that selection. Browser verification should include desktop, mobile, all five recording tabs, event selection, time-slider interaction and printing.

## Publish

The `main` branch contains the source; GitHub Pages serves the `gh-pages` branch, which contains the `site/` directory only. `.nojekyll` prevents processing of static assets.

```bash
git subtree split --prefix site -b pages-update
git push origin pages-update:gh-pages
git branch -D pages-update
```

Publish only after validating the final source revision. GitHub Pages is public; source recordings and credentials stay in the separate local benchmark folder.

## Sources

- [NVIDIA Nemotron 3 Diarization model card](https://huggingface.co/nvidia/Nemotron-3-Diarization)
- [pyannote Precision-3](https://www.pyannote.ai/precision-3)
- [pyannote overlap and speaker configuration](https://docs.pyannote.ai/tutorials/speaker-configuration)
- [pyannote.metrics diarization scoring](https://pyannote.github.io/pyannote-metrics/reference.html#diarization)

The public model documentation is linked for context. The plotted values are our local pilot measurements, not vendor-published benchmark values.
