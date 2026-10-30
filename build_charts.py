#!/usr/bin/env python3
"""Create standalone, shareable figures from the published measurements."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
        fig.savefig(ROOT / 'assets' / f'{name}.{extension}', bbox_inches='tight', dpi=190)
    plt.close(fig)


def quality():
    fig, ax = plt.subplots(figsize=(11.8, 4.1))
    labels = ['Dave the Barbarian', 'Pizza Delivery', 'Veronica Having Bad Luck']
    for i, clip in enumerate(DATA['clips']):
        y = 2 - i
        a, b = (clip['results'][m]['der_percent'] for m in ['pyannote', 'nemotron'])
        ax.plot([a, b], [y, y], color='#cfd5d1', linewidth=4, zorder=1, solid_capstyle='round')
        for value, color, offset in [(a, ORANGE, .19), (b, TEAL, -.22)]:
            ax.scatter(value, y, s=90, color=color, edgecolor='white', linewidth=1.5, zorder=3)
            ax.text(value, y + offset, f'{value:.2f}%', color=color, fontsize=11, fontweight='bold', ha='center')
    ax.set_yticks([2, 1, 0], labels)
    ax.set_xlim(0, 80)
    ax.set_ylim(-.6, 2.6)
    ax.set_xticks([0, 20, 40, 60, 80], ['0%', '20%', '40%', '60%', '80%'])
    ax.grid(axis='x', color=GRID, linewidth=1)
    ax.set_xlabel('Diarization error rate · lower is better', labelpad=18, fontsize=10)
    clean(ax)
    fig.subplots_adjust(left=.24, right=.96, bottom=.2, top=.94)
    save(fig, 'quality-by-clip')


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
    ax.set_xlim(0, 65)
    ax.set_xticks([0, 20, 40, 60], ['0', '20', '40', '60'])
    ax.set_ylim(-.6, 1.6)
    ax.grid(axis='x', color=GRID)
    ax.set_xlabel('Contribution to total DER · percentage points', labelpad=16, fontsize=10)
    clean(ax)
    fig.subplots_adjust(left=.15, right=.96, bottom=.3, top=.94)
    save(fig, 'error-breakdown')


def speaker_counts():
    fig, ax = plt.subplots(figsize=(11.8, 3.8))
    y = np.arange(3)
    for offset, key, color, label in [(-.23, 'reference', INK, 'Reference'), (0, 'pyannote', ORANGE, 'Precision-3'), (.23, 'nemotron', TEAL, 'NVIDIA')]:
        values = [c['speakers'] if key == 'reference' else c['results'][key]['detected_speakers'] for c in DATA['clips']]
        bars = ax.barh(y + offset, values, height=.18, color=color, label=label, zorder=2)
        for bar, value in zip(bars, values):
            ax.text(value + .15, bar.get_y() + bar.get_height() / 2, str(value), va='center', fontsize=11, color=color, fontweight='bold')
    ax.set_yticks(y, ['Dave the Barbarian', 'Pizza Delivery', 'Veronica Having Bad Luck'])
    ax.invert_yaxis()
    ax.set_xticks([0, 4, 8, 12])
    ax.set_xlim(0, 12)
    ax.grid(axis='x', color=GRID)
    ax.set_xlabel('Distinct speaker labels across the whole clip', labelpad=16, fontsize=10)
    clean(ax)
    fig.subplots_adjust(left=.24, right=.96, bottom=.2, top=.94)
    save(fig, 'speaker-counts')


def mobile_figures():
    fig, ax = plt.subplots(figsize=(4.5, 4.4))
    for i, clip in enumerate(DATA['clips']):
        y = 2 - i
        a, b = (clip['results'][m]['der_percent'] for m in ['pyannote', 'nemotron'])
        ax.text(0, y + .39, clip['title'], fontsize=9, fontweight='bold')
        ax.plot([a, b], [y, y], color='#cfd5d1', linewidth=3)
        for value, color, offset in [(a, ORANGE, .15), (b, TEAL, -.2)]:
            ax.scatter(value, y, s=52, color=color, edgecolor='white', linewidth=1, zorder=3)
            ax.text(value, y + offset, f'{value:.2f}%', color=color, fontsize=9, fontweight='bold', ha='center')
    ax.set_xlim(0, 82)
    ax.set_ylim(-.5, 2.7)
    ax.set_yticks([])
    ax.set_xticks([0, 20, 40, 60, 80], ['0%', '20%', '40%', '60%', '80%'])
    ax.tick_params(labelsize=8)
    ax.grid(axis='x', color=GRID, linewidth=.7)
    clean(ax)
    fig.subplots_adjust(left=.06, right=.96, bottom=.12, top=.97)
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
    ax.set_xlim(0, 65)
    ax.set_ylim(-.45, 1.6)
    ax.set_yticks([])
    ax.set_xticks([0, 20, 40, 60])
    ax.tick_params(labelsize=8)
    clean(ax)
    fig.subplots_adjust(left=.03, right=.99, bottom=.15, top=.97)
    save(fig, 'errors-mobile')

    fig, ax = plt.subplots(figsize=(4.5, 4.7))
    for index, clip in enumerate(DATA['clips']):
        y = 2 - index
        ax.text(0, y + .39, clip['title'], fontsize=9, fontweight='bold')
        for offset, key, color in [(.15, 'reference', INK), (0, 'pyannote', ORANGE), (-.15, 'nemotron', TEAL)]:
            value = clip['speakers'] if key == 'reference' else clip['results'][key]['detected_speakers']
            ax.barh(y + offset, value, height=.11, color=color)
            ax.text(value + .15, y + offset, str(value), va='center', fontsize=8, fontweight='bold', color=color)
    ax.set_xlim(0, 12)
    ax.set_ylim(-.5, 2.7)
    ax.set_yticks([])
    ax.set_xticks([0, 4, 8, 12])
    ax.tick_params(labelsize=8)
    ax.grid(axis='x', color=GRID, linewidth=.7)
    clean(ax)
    fig.subplots_adjust(left=.03, right=.96, bottom=.12, top=.97)
    save(fig, 'speakers-mobile')


if __name__ == '__main__':
    quality()
    errors()
    speaker_counts()
    mobile_figures()
    print('Created SVG and PNG figures in', ROOT / 'assets')
