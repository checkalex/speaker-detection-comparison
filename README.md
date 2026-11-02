# Speaker detection, measured

A static, presentation-ready evaluation of **pyannote Precision-3** and **NVIDIA Nemotron 3 Diarization**, updated on 2 November 2026 with five completed English recordings: three animation excerpts and two Friends compilations. Shrek remains excluded while its reviewed reference is pending.

Published report: **https://checkalex.github.io/speaker-detection-comparison/**

## Findings

The primary Checksub workflow measurement is now **correct speaker assignment per subtitle line**. It applies the existing `Subtitles::SetSpeakers` rule to both saved model outputs, on identical reviewed subtitle intervals.

| Recording | Scored lines | Precision-3 correct | NVIDIA correct |
| --- | ---: | ---: | ---: |
| Dave the Barbarian | 106 | 91 (85.85%) | 73 (68.87%) |
| Pizza Delivery | 90 | 80 (88.89%) | 74 (82.22%) |
| Veronica Having Bad Luck | 78 | 39 (50.00%) | 41 (52.56%) |
| Friends: Funniest Moments | 261 | 210 (80.46%) | 179 (68.58%) |
| Friends: Christmas Episodes | 312 | 277 (88.78%) | 260 (83.33%) |
| All five | 847 | **697 (82.29%)** | 627 (74.03%) |

Precision-3 has 150 incorrect line assignments versus NVIDIA's 220. Excluding Christmas, the scores are **78.50% versus 68.60%**; on the three recordings within the eight-speaker limit, **76.69% versus 68.53%**. These measure label agreement after consistent identity naming, not observed editing time.

### Subtitle scoring method

- Preserve individual subtitle lines from `reference.csv`, without merging adjacent same-speaker lines. All 849 intervals were checked against the original Checksub CSV exports.
- Match the current Checksub rule: choose the **single segment** with greatest subtitle overlap, first segment on ties. Do not sum disconnected segments belonging to the same speaker. The Python implementation was checked against the original Ruby method on all **1,694** eligible model/line combinations.
- If there is no overlap, reproduce the editor's default speaker ID 1 (`SPEAKER_00` / `speaker_0`). These fallbacks are reported explicitly: Precision-3 15 (two correct), NVIDIA 69 (27 correct). Requiring supporting detection for a correct assignment gives **82.05% versus 70.84%**, using the same 847-line denominator.
- Use one global one-to-one cluster/name mapping per model and recording, optimized for correct line count with the Hungarian algorithm. This measures best-case grouping agreement after naming clusters. A split or merged identity is penalized; a cluster cannot change its name from line to line. This mapping is separate from DER's duration-based mapping.
- Group reference rows with identical intervals into one subtitle. Exclude Dave's two five-speaker chorus lines from the single-speaker metric, while retaining them in DER and overlap evaluation. This leaves 847 of 849 lines scored.
- Aggregate by total line counts, not the mean of clip percentages. Shrek is unscored and excluded. No inference jobs are submitted.

`site/data/subtitle-accuracy.csv` contains counts and percentages, including the two subsets. `site/data/subtitle-assignments.csv` audits every model/line outcome with anonymous reference IDs, prediction, mapping, exclusion and fallback flags. The detailed named audit stays in the private benchmark run as `subtitle-scores.json`.

### DER remains a separate measurement

| Recording | Precision-3 DER | NVIDIA DER | Reference speaker count |
| --- | ---: | ---: | ---: |
| Dave the Barbarian | 36.06% | 47.24% | 11 |
| Pizza Delivery | 43.80% | 45.11% | 5 |
| Veronica Having Bad Luck | 69.08% | 67.60% | 8 |
| Friends: Funniest Moments | 78.98% | 45.55% | 8 |
| Friends: Christmas Episodes | 56.01% | 25.83% | 9 |
| Weighted overall | 58.34% | **41.38%** | |

NVIDIA leads total DER, mainly through fewer detections outside the subtitle reference. Precision-3 has less wrong-speaker time in every clip: **139.68 seconds total versus 203.66 seconds for NVIDIA**. The measured subtitle-line accuracy supports keeping Precision-3 as the provisional baseline for the current Checksub assignment rule; this is not an overall diarization-quality claim.

Dave and Friends Christmas exceed NVIDIA's documented eight-speaker capacity. On the three clips within that limit, weighted DER is **67.71% for Precision-3 versus 50.59% for NVIDIA**.

All five references are model-assisted and then human-reviewed. The first four began with Checksub’s original speaker assignments; Friends Christmas began with NVIDIA speaker labels. Those initial labels can influence human review. All five retain shared cue times from Checksub’s transcription/alignment pipeline; these timings do not inherently favor either diarizer and were not independently annotated as audible speech boundaries. Only Dave's two chorus intervals explicitly annotate simultaneous voices; the brief overlapping subtitle intervals in Christmas are shown separately as unconfirmed overlap.

## What's included

- An executive summary, provisional conclusion and next steps.
- Standalone SVG and PNG figures created with Matplotlib.
- Responsive comparisons by recording, error type and speaker count.
- An interactive speaker-count timeline with exact overlap-event windows, keyboard-accessible time slider, and optional timeline animation.
- A capacity-aware subset analysis and explanation of DER.
- Subtitle speaker accuracy, correction-proxy counts, fallback analysis and an anonymous per-line audit.
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

# Focused scorer tests, no provider calls
../speaker-detector-benchmark/.venv/bin/python -m unittest -v test_subtitle_accuracy
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
