#!/usr/bin/env python3
"""Create standalone, shareable figures from the published measurements."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).parent / 'site'
DATA = json.loads((ROOT / 'data/comparison.json').read_text())
ORANGE, TEAL, INK, MUTED, GRID = '#d85b32', '#267b79', '#20282b', '#707879', '#e7e9e5'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'text.color': INK,
                     'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': INK,
                     'svg.fonttype': 'none', 'savefig.transparent': True})


def clean(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis='both', length=0, pad=12)
    ax.set_axisbelow(True)


def save(fig, name):
    for extension in ['svg', 'png']:
        path = ROOT / 'assets' / f'{name}.{extension}'
        fig.savefig(path, bbox_inches='tight', dpi=190)
        if extension == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
    plt.close(fig)


def quality():
    count = len(DATA['clips'])
    fig, ax = plt.subplots(figsize=(11.8, 1.15 * count + .8))
    labels = [clip['title'] for clip in DATA['clips']]
    for i, clip in enumerate(DATA['clips']):
        y = count - 1 - i
        a, b = (clip['results'][m]['der_percent'] for m in ['pyannote', 'nemotron'])
        ax.plot([a, b], [y, y], color='#cfd5d1', linewidth=4, zorder=1, solid_capstyle='round')
        for value, color, offset in [(a, ORANGE, .19), (b, TEAL, -.22)]:
            ax.scatter(value, y, s=90, color=color, edgecolor='white', linewidth=1.5, zorder=3)
            ax.text(value, y + offset, f'{value:.2f}%', color=color, fontsize=11, fontweight='bold', ha='center')
    ax.set_yticks(list(reversed(range(count))), labels)
    ax.set_xlim(0, 90)
    ax.set_ylim(-.6, count - .4)
    ax.set_xticks([0, 20, 40, 60, 80], ['0%', '20%', '40%', '60%', '80%'])
    ax.grid(axis='x', color=GRID, linewidth=1)
    ax.set_xlabel('Diarization error rate · lower is better', labelpad=18, fontsize=10)
    clean(ax)
    fig.subplots_adjust(left=.26, right=.96, bottom=.14, top=.96)
    save(fig, 'quality-by-clip')


def subtitle_accuracy(mobile=False):
    count = len(DATA['clips'])
    fig, ax = plt.subplots(figsize=(4.5 if mobile else 11.8, (1.2 if mobile else 1.15) * count + .8))
    for index, clip in enumerate(DATA['clips']):
        y = count - 1 - index
        a, b = (clip['results'][model]['subtitle_accuracy']['accuracy_percent'] for model in ['pyannote', 'nemotron'])
        if mobile:
            ax.text(0, y + .39, clip['title'], fontsize=9, fontweight='bold')
        ax.plot([a, b], [y, y], color='#cfd5d1', linewidth=3 if mobile else 4, zorder=1, solid_capstyle='round')
        for value, color, offset in [(a, ORANGE, .17), (b, TEAL, -.22)]:
            ax.scatter(value, y, s=52 if mobile else 90, color=color, edgecolor='white', linewidth=1.2, zorder=3)
            ax.text(value, y + offset, f'{value:.2f}%', color=color, fontsize=9 if mobile else 11,
                    fontweight='bold', ha='center')
    ax.set_yticks([] if mobile else list(reversed(range(count))), [] if mobile else [clip['title'] for clip in DATA['clips']])
    ax.set_xlim(0, 104)
    ax.set_ylim(-.6, count - .3)
    ax.set_xticks([0, 25, 50, 75, 100], ['0%', '25%', '50%', '75%', '100%'])
    ax.grid(axis='x', color=GRID, linewidth=.7 if mobile else 1)
    ax.set_xlabel('Correct subtitle speaker assignments · higher is better', labelpad=18, fontsize=8 if mobile else 10)
    fig.legend(handles=[Line2D([], [], marker='o', linestyle='none', color=color, label=label)
                        for color, label in [(ORANGE, 'Precision-3'), (TEAL, 'NVIDIA')]],
               loc='upper center', bbox_to_anchor=(.5 if mobile else .61, 1.02), ncol=2,
               frameon=False, fontsize=9 if mobile else 11)
    clean(ax)
    fig.subplots_adjust(left=.06 if mobile else .26, right=.96, bottom=.12 if mobile else .14, top=.97)
    save(fig, 'subtitle-accuracy-mobile' if mobile else 'subtitle-accuracy')


def errors():
    fig, ax = plt.subplots(figsize=(11.8, 2.8))
    keys = ['missed_speech_seconds', 'speaker_confusion_seconds', 'false_speech_seconds']
    colors = ['#c58c66', '#66768a', '#c3c9c3']
    for y, model in [(1, 'pyannote'), (0, 'nemotron')]:
        left = 0
        for key, color in zip(keys, colors):
            points = DATA['aggregate_errors'][model][key]['der_points']
            ax.barh(y, points, left=left, height=.36, color=color, edgecolor='white', linewidth=2)
            ax.text(left + points / 2, y, f'{points:.2f}', ha='center', va='center', color='white' if key != 'false_speech_seconds' else INK,
                    fontsize=11, fontweight='bold')
            left += points
        ax.text(left + 1.3, y, f'{left:.2f}%', fontsize=12, va='center', fontweight='bold')
    ax.set_yticks([1, 0], ['Precision-3', 'NVIDIA'])
    ax.set_xlim(0, 70)
    ax.set_xticks([0, 20, 40, 60], ['0', '20', '40', '60'])
    ax.set_ylim(-.6, 1.6)
    ax.grid(axis='x', color=GRID)
    ax.set_xlabel('Contribution to total DER · percentage points', labelpad=16, fontsize=10)
    clean(ax)
    fig.subplots_adjust(left=.15, right=.96, bottom=.3, top=.94)
    save(fig, 'error-breakdown')


def speaker_counts():
    fig, ax = plt.subplots(figsize=(11.8, 1.05 * len(DATA['clips']) + .8))
    y = np.arange(len(DATA['clips']))
    for offset, key, color, label in [(-.23, 'reference', INK, 'Reference'), (0, 'pyannote', ORANGE, 'Precision-3'), (.23, 'nemotron', TEAL, 'NVIDIA')]:
        values = [c['speakers'] if key == 'reference' else c['results'][key]['detected_speakers'] for c in DATA['clips']]
        bars = ax.barh(y + offset, values, height=.18, color=color, label=label, zorder=2)
        for bar, value in zip(bars, values):
            ax.text(value + .15, bar.get_y() + bar.get_height() / 2, str(value), va='center', fontsize=11, color=color, fontweight='bold')
    ax.set_yticks(y, [clip['title'] for clip in DATA['clips']])
    ax.invert_yaxis()
    ax.set_xticks([0, 4, 8, 12])
    ax.set_xlim(0, 12)
    ax.grid(axis='x', color=GRID)
    ax.set_xlabel('Distinct speaker labels across the whole clip', labelpad=16, fontsize=10)
    clean(ax)
    fig.subplots_adjust(left=.26, right=.96, bottom=.14, top=.96)
    save(fig, 'speaker-counts')


def mobile_figures():
    count = len(DATA['clips'])
    fig, ax = plt.subplots(figsize=(4.5, 1.2 * count + .8))
    for i, clip in enumerate(DATA['clips']):
        y = count - 1 - i
        a, b = (clip['results'][m]['der_percent'] for m in ['pyannote', 'nemotron'])
        ax.text(0, y + .39, clip['title'], fontsize=9, fontweight='bold')
        ax.plot([a, b], [y, y], color='#cfd5d1', linewidth=3)
        for value, color, offset in [(a, ORANGE, .15), (b, TEAL, -.2)]:
            ax.scatter(value, y, s=52, color=color, edgecolor='white', linewidth=1, zorder=3)
            ax.text(value, y + offset, f'{value:.2f}%', color=color, fontsize=9, fontweight='bold', ha='center')
    ax.set_xlim(0, 90)
    ax.set_ylim(-.5, count - .3)
    ax.set_yticks([])
    ax.set_xticks([0, 20, 40, 60, 80], ['0%', '20%', '40%', '60%', '80%'])
    ax.tick_params(labelsize=8)
    ax.grid(axis='x', color=GRID, linewidth=.7)
    clean(ax)
    fig.subplots_adjust(left=.06, right=.96, bottom=.08, top=.97)
    save(fig, 'quality-mobile')

    fig, ax = plt.subplots(figsize=(4.5, 2.4))
    keys = ['missed_speech_seconds', 'speaker_confusion_seconds', 'false_speech_seconds']
    for y, model in [(1, 'pyannote'), (0, 'nemotron')]:
        ax.text(0, y + .28, 'Precision-3' if model == 'pyannote' else 'NVIDIA', fontsize=9, fontweight='bold')
        left = 0
        for key, color in zip(keys, ['#c58c66', '#66768a', '#c3c9c3']):
            value = DATA['aggregate_errors'][model][key]['der_points']
            ax.barh(y, value, left=left, height=.32, color=color, edgecolor='white', linewidth=1)
            ax.text(left + value / 2, y, f'{value:.2f}', ha='center', va='center', color='white' if key != keys[-1] else INK, fontsize=8)
            left += value
        ax.text(left + .9, y, f'{left:.2f}%', fontsize=9, va='center', fontweight='bold')
    ax.set_xlim(0, 70)
    ax.set_ylim(-.45, 1.6)
    ax.set_yticks([])
    ax.set_xticks([0, 20, 40, 60])
    ax.tick_params(labelsize=8)
    clean(ax)
    fig.subplots_adjust(left=.03, right=.99, bottom=.15, top=.97)
    save(fig, 'errors-mobile')

    fig, ax = plt.subplots(figsize=(4.5, 1.2 * count + .8))
    for index, clip in enumerate(DATA['clips']):
        y = count - 1 - index
        ax.text(0, y + .39, clip['title'], fontsize=9, fontweight='bold')
        for offset, key, color in [(.15, 'reference', INK), (0, 'pyannote', ORANGE), (-.15, 'nemotron', TEAL)]:
            value = clip['speakers'] if key == 'reference' else clip['results'][key]['detected_speakers']
            ax.barh(y + offset, value, height=.11, color=color)
            ax.text(value + .15, y + offset, str(value), va='center', fontsize=8, fontweight='bold', color=color)
    ax.set_xlim(0, 12)
    ax.set_ylim(-.5, count - .3)
    ax.set_yticks([])
    ax.set_xticks([0, 4, 8, 12])
    ax.tick_params(labelsize=8)
    ax.grid(axis='x', color=GRID, linewidth=.7)
    clean(ax)
    fig.subplots_adjust(left=.03, right=.96, bottom=.08, top=.97)
    save(fig, 'speakers-mobile')


if __name__ == '__main__':
    subtitle_accuracy()
    subtitle_accuracy(mobile=True)
    quality()
    errors()
    speaker_counts()
    mobile_figures()
    print('Created SVG and PNG figures in', ROOT / 'assets')
