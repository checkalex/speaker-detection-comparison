# Speaker detection, measured

A static, presentation-ready evaluation of **pyannote Precision-3** and **NVIDIA Nemotron 3 Diarization**, based on three English animation excerpts evaluated on 29 October 2026.

Published report: **https://checkalex.github.io/speaker-detection-comparison/**

## Findings

| Recording | Precision-3 DER | NVIDIA DER | Reference speaker count |
| --- | ---: | ---: | ---: |
| Dave the Barbarian | 36.06% | 47.24% | 11 |
| Pizza Delivery | 43.80% | 45.11% | 5 |
| Veronica Having Bad Luck | 69.08% | 67.60% | 8 |
| Weighted overall | **47.69%** | 52.30% | |

Dave exceeds NVIDIA's documented eight-speaker capacity. On the two clips within that limit, the weighted results are nearly tied: **55.91% for Precision-3 versus 55.88% for NVIDIA**. This exploratory pilot does not establish a broad winner or justify replacing the existing baseline.

The reference uses human-assigned character names with subtitle export timestamps, not independent speech-boundary annotation. Only Dave's two chorus intervals explicitly annotate simultaneous voices. The report makes these limitations visible alongside the results.

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

`build_charts.py` requires Matplotlib and NumPy. The report is a frozen study: if source results change, update the written numerical summary and conclusion alongside the charts. Browser verification should include desktop, mobile, all three recording tabs, event selection, time-slider interaction and printing.

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
