'use strict';

(() => {
  const data = window.COMPARISON;
  if (!data) return;
  const $ = selector => document.querySelector(selector);
  const colors = {reference: '#dce6c9', pyannote: '#f29773', nemotron: '#89cebf'};
  const names = {reference: 'Reference', pyannote: 'Precision-3', nemotron: 'NVIDIA'};
  const fixed = (value, places = 2) => Number(value).toFixed(places);
  const time = (seconds, decimals = 0) => {
    const rounded = Number(seconds.toFixed(decimals));
    const minutes = Math.floor(rounded / 60);
    const remainder = (rounded - minutes * 60).toFixed(decimals);
    return `${minutes}:${remainder.padStart(decimals ? decimals + 3 : 2, '0')}`;
  };

  const subtitleSummary = data.subtitle_accuracy_summary.all;
  $('#subtitle-score-rows').innerHTML = data.clips.map(clip => {
    const p = clip.results.pyannote.subtitle_accuracy, n = clip.results.nemotron.subtitle_accuracy;
    return `<tr><th>${clip.title}</th><td>${p.scored_cues}</td><td>${p.correct_cues} · ${fixed(p.accuracy_percent)}%</td><td>${n.correct_cues} · ${fixed(n.accuracy_percent)}%</td><td>${p.incorrect_cues} / ${n.incorrect_cues}</td></tr>`;
  }).join('') + `<tr class="total-row"><th>All five recordings</th><td>${subtitleSummary.pyannote.scored_cues}</td><td>${subtitleSummary.pyannote.correct_cues} · ${fixed(subtitleSummary.pyannote.accuracy_percent)}%</td><td>${subtitleSummary.nemotron.correct_cues} · ${fixed(subtitleSummary.nemotron.accuracy_percent)}%</td><td>${subtitleSummary.pyannote.incorrect_cues} / ${subtitleSummary.nemotron.incorrect_cues}</td></tr>`;

  $('.clip-tabs').innerHTML = data.clips.map(clip => `<button type="button" data-clip="${clip.id}" data-testid="select-${clip.id}" aria-pressed="false">${clip.id === 'friends' ? 'Friends: Funniest' : clip.id === 'christmas' ? 'Friends: Christmas' : clip.id === 'veronica' ? 'Veronica' : clip.title}</button>`).join('');

  $('#clip-cards').innerHTML = data.clips.map((clip, index) => {
    const p = clip.results.pyannote, n = clip.results.nemotron;
    const winner = p.der_percent < n.der_percent ? 'pyannote' : 'nemotron';
    return `<article class="clip-card"><div class="clip-card-top"><span class="clip-index">0${index + 1}</span><span>${time(clip.duration)} · ${clip.speakers} reference voices</span></div>
      <h3>${clip.title}</h3><p class="clip-context">${clip.context}</p>${clip.reference_note ? `<p class="clip-reference-note"><strong>Reference caveat</strong> ${clip.reference_note}</p>` : ''}
      <p class="clip-subtitle-accuracy"><strong>Correct subtitle lines</strong><span class="precision-text">Precision-3 ${fixed(p.subtitle_accuracy.accuracy_percent)}%</span><span class="nvidia-text">NVIDIA ${fixed(n.subtitle_accuracy.accuracy_percent)}%</span></p>
      <div class="clip-scores">${['pyannote', 'nemotron'].map(model => `<div class="clip-score-label"><span><i class="dot ${model === 'pyannote' ? 'precision' : 'nvidia'}"></i>${names[model]} DER</span><strong class="${model === 'pyannote' ? 'precision-text' : 'nvidia-text'}">${fixed(clip.results[model].der_percent)}<span>%</span></strong></div><div class="clip-track"><span class="${model === 'pyannote' ? 'precision-fill' : 'nvidia-fill'}" style="width:${clip.results[model].der_percent}%"></span></div>`).join('')}</div>
      <div class="speaker-tally"><span>Speaker labels<br>Reference / Precision-3 / NVIDIA</span><strong>${clip.speakers} / ${p.detected_speakers} / ${n.detected_speakers}</strong></div>
      <div class="clip-card-footer"><span class="winner-tag ${winner === 'nemotron' ? 'nvidia-winner' : ''}">${names[winner]} lower DER</span><button class="clip-explore" type="button" data-explore="${clip.id}" data-testid="explore-${clip.id}">Inspect overlap ↗</button></div></article>`;
  }).join('');

  const state = {clipId: 'dave', mode: 'focus', start: 197, end: 208, position: 201, allEvents: false, playing: false};
  let animation = null, lastFrame = 0;
  const currentClip = () => data.clips.find(clip => clip.id === state.clipId);
  const activeAt = (series, position) => {
    const run = series.find(([start, end]) => position >= start && position < end);
    return run ? run[2] : 0;
  };
  const peakIn = (series, start, end) => Math.max(0, ...series.filter(([a, b]) => a < end && b > start).map(run => run[2]));
  const longestEvent = clip => clip.overlap_events.find(event => event.annotated) ||
    [...clip.overlap_events].sort((a, b) => (b.end - b.start) - (a.end - a.start))[0];

  function stopAnimation() {
    state.playing = false;
    if (animation) cancelAnimationFrame(animation);
    animation = null;
    $('#animate-button').textContent = '▶';
    $('#animate-button').setAttribute('aria-label', 'Animate the timeline');
  }

  function setRange(mode, event) {
    const clip = currentClip();
    state.mode = mode;
    if (mode === 'full') {
      state.start = 0;
      state.end = clip.duration;
    } else if (event) {
      state.start = Math.max(0, event.start - 1.5);
      state.end = Math.min(clip.duration, event.end + 1.5);
    } else if (clip.id === 'dave') {
      state.start = 197;
      state.end = 208;
    } else {
      const focus = longestEvent(clip);
      state.start = focus ? Math.max(0, focus.start - 3) : 0;
      state.end = focus ? Math.min(clip.duration, focus.end + 3) : Math.min(clip.duration, 20);
    }
    state.position = event ? (event.start + event.end) / 2 : state.start + (state.end - state.start) / 2;
    if (clip.id === 'dave' && mode === 'focus' && !event) state.position = 201;
    const slider = $('#time-slider');
    slider.min = state.start;
    slider.max = state.end;
    slider.value = state.position;
    $('#window-start').textContent = time(state.start, 1);
    $('#window-end').textContent = time(state.end, 1);
    document.querySelectorAll('[data-window]').forEach(button => {
      const active = button.dataset.window === mode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }

  function drawTimeline() {
    const clip = currentClip();
    const host = $('#activity-chart');
    const width = Math.max(280, host.clientWidth);
    const mobile = width < 560;
    const left = mobile ? 74 : 104;
    const right = width - 14;
    const plotWidth = right - left;
    const height = 252;
    const laneHeight = 72;
    const x = seconds => left + (seconds - state.start) / (state.end - state.start) * plotWidth;
    const maximum = Math.max(5, ...Object.values(clip.activity).map(series => peakIn(series, state.start, state.end)));
    const unitHeight = 43 / maximum;
    const tickCount = mobile ? 3 : 6;
    const parts = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="timeline-svg-title timeline-svg-description"><title id="timeline-svg-title">${clip.title}: simultaneous speaker activity</title><desc id="timeline-svg-description">Reference and detector speaker counts over time. The height of each step indicates simultaneous speaker labels, with ${maximum} the highest scale value. Use the time slider to inspect exact counts.</desc><defs><clipPath id="timeline-clip"><rect x="${left}" y="0" width="${plotWidth}" height="226"/></clipPath></defs>`];
    clip.activity.reference.filter(([a, b, count]) => count >= 2 && a < state.end && b > state.start).forEach(([a, b]) => {
      parts.push(`<rect class="reference-band" x="${x(Math.max(a, state.start))}" y="0" width="${x(Math.min(b, state.end)) - x(Math.max(a, state.start))}" height="222"/>`);
    });
    for (let i = 0; i <= tickCount; i++) {
      const seconds = state.start + (state.end - state.start) * i / tickCount;
      const xp = x(seconds);
      parts.push(`<line class="chart-grid" x1="${xp}" x2="${xp}" y1="0" y2="222"/><text class="axis-label" x="${xp}" y="244" text-anchor="${i === 0 ? 'start' : i === tickCount ? 'end' : 'middle'}">${time(seconds, state.end - state.start > 30 ? 0 : 1)}</text>`);
    }
    ['reference', 'pyannote', 'nemotron'].forEach((key, index) => {
      const base = (index + 1) * laneHeight - 7;
      const label = mobile && key === 'reference' ? 'Reference' : names[key];
      parts.push(`<text class="lane-label" x="0" y="${base - 24}" style="fill:${colors[key]};font-size:${mobile ? 9 : 11}px">${label}</text>`);
      [0, maximum].forEach(count => {
        const yp = base - count * unitHeight;
        parts.push(`<text class="count-axis" x="${left - 9}" y="${yp + 3}" text-anchor="end" style="font-size:${mobile ? 8 : 10}px">${count}</text><line class="lane-zero" x1="${left}" x2="${right}" y1="${yp}" y2="${yp}"/>`);
      });
      const runs = clip.activity[key].filter(([a, b]) => a < state.end && b > state.start);
      let line = '', area = `M${left},${base}`;
      runs.forEach(([a, b, count], i) => {
        const xa = x(Math.max(a, state.start)), xb = x(Math.min(b, state.end));
        const yp = base - count * unitHeight;
        line += `${i === 0 ? 'M' : 'L'}${xa},${yp} L${xb},${yp} `;
        area += `L${xa},${yp} L${xb},${yp} `;
        if (count >= 2) {
          parts.push(`<rect x="${xa}" y="${base + 4}" width="${Math.max(.3, xb - xa)}" height="3" rx="1" fill="${colors[key]}" opacity=".8"><title>${names[key]}: ${count} labels, ${time(a, 2)}–${time(b, 2)}</title></rect>`);
        }
      });
      area += `L${right},${base} Z`;
      parts.push(`<g clip-path="url(#timeline-clip)"><path class="count-area" d="${area}" fill="${colors[key]}"/><path class="count-line" d="${line}" stroke="${colors[key]}"/></g>`);
    });
    parts.push(`<line id="timeline-cursor" class="cursor-line" x1="${x(state.position)}" x2="${x(state.position)}" y1="0" y2="225"/><rect id="timeline-hit-area" x="${left}" y="0" width="${plotWidth}" height="225" fill="transparent" style="cursor:crosshair"/></svg>`);
    host.innerHTML = parts.join('');
    host.dataset.plotLeft = left;
    host.dataset.plotRight = right;
    const hit = $('#timeline-hit-area');
    hit.addEventListener('pointermove', event => {
      if (state.playing) return;
      const svg = host.querySelector('svg');
      const box = svg.getBoundingClientRect();
      const xp = (event.clientX - box.left) * width / box.width;
      setPosition(state.start + Math.max(0, Math.min(1, (xp - left) / plotWidth)) * (state.end - state.start));
    });
    updateCursor();
  }

  function updateCursor() {
    const host = $('#activity-chart');
    const left = Number(host.dataset.plotLeft), right = Number(host.dataset.plotRight);
    const xp = left + (state.position - state.start) / (state.end - state.start) * (right - left);
    const line = $('#timeline-cursor');
    if (line) { line.setAttribute('x1', xp); line.setAttribute('x2', xp); }
    $('#cursor-time').textContent = time(state.position, 2);
    $('#time-slider').value = state.position;
    $('#time-slider').setAttribute('aria-valuetext', time(state.position, 2));
    for (const key of ['reference', 'pyannote', 'nemotron']) {
      $(`#cursor-${key}`).textContent = activeAt(currentClip().activity[key], state.position);
    }
  }

  function setPosition(position) {
    state.position = Math.max(state.start, Math.min(state.end, position));
    updateCursor();
  }

  function renderEvents() {
    const clip = currentClip();
    const events = clip.overlap_events;
    const visible = state.allEvents ? events : events.slice(0, 6);
    $('#event-count').textContent = `${events.length} interval${events.length === 1 ? '' : 's'}`;
    $('#event-rows').innerHTML = visible.map((event, index) => `<tr><td><button type="button" class="event-jump" data-event-index="${index}" data-testid="jump-overlap-event-${index}">${time(event.start, 2)}–${time(event.end, 2)} ↗</button></td><td><span class="overlap-peak">${event.reference.peak}</span></td><td><span class="overlap-peak" style="color:${event.pyannote.peak >= 2 ? colors.pyannote : '#a5bbb0'}">${event.pyannote.peak}</span></td><td><span class="overlap-peak" style="color:${event.nemotron.peak >= 2 ? colors.nemotron : '#a5bbb0'}">${event.nemotron.peak}</span></td><td>${event.annotated ? (clip.confirmed_overlap_reference ? 'Annotated overlap' : 'Subtitle intervals overlap') : 'No overlap annotation'}</td></tr>`).join('') || '<tr><td colspan="5">No overlap intervals were flagged.</td></tr>';
    const more = $('#show-events');
    more.hidden = events.length <= 6;
    more.textContent = state.allEvents ? 'Show fewer events' : `Show all ${events.length} events`;
    document.querySelectorAll('[data-event-index]').forEach(button => button.addEventListener('click', () => {
      stopAnimation();
      setRange('focus', events[Number(button.dataset.eventIndex)]);
      drawTimeline();
    }));
  }

  function renderClip() {
    const clip = currentClip();
    document.querySelectorAll('[data-clip]').forEach(button => {
      const active = button.dataset.clip === clip.id;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    const isChorus = clip.id === 'dave';
    $('#timeline-kicker').textContent = `${clip.title.toUpperCase()} / ${isChorus ? 'FIVE-VOICE CHORUS' : 'MODEL-FLAGGED OVERLAP'}`;
    $('#timeline-title').innerHTML = isChorus ? 'Five voices in the reference.<br>Fewer in the predictions.' : 'Inspect the moments<br>flagged by the models.';
    const total = clip.annotated_overlap_seconds;
    const firstInsight = total > 0 ? `<div><div class="insight-label">${isChorus ? 'Annotated overlap' : 'Subtitle overlap'}</div><div class="insight-value">${fixed(total)}s</div><p class="insight-caption">${isChorus ? 'Two chorus passages, with five reference characters singing together.' : 'Overlapping subtitle intervals. Listen to verify whether the voices actually overlap.'}</p></div>` : `<div><div class="insight-label">Human overlap reference</div><div class="insight-value">Unannotated</div><p class="insight-caption">The reference has no explicitly labeled overlaps. Model flags need listening review.</p></div>`;
    $('#overlap-insight').innerHTML = firstInsight + ['pyannote', 'nemotron'].map(model => {
      const seconds = total > 0 ? clip.results[model].annotated_overlap_detected_seconds : clip.results[model].overlap.seconds;
      const caption = total > 0 ? `${fixed(100 * seconds / total, 1)}% of ${isChorus ? 'annotated' : 'subtitle'} overlap marked with ≥2 labels. This does not verify speaker identities.` : `Total time with ≥2 predicted labels across the full ${time(clip.duration)} recording.`;
      return `<div><div class="insight-label">${names[model]} · ${total > 0 ? (isChorus ? 'within the chorus' : 'within subtitle overlap') : 'predicted overlap'}</div><div class="insight-value ${model === 'pyannote' ? 'precision-text' : 'nvidia-text'}">${fixed(seconds)}s</div><p class="insight-caption">${caption}</p></div>`;
    }).join('');
    $('#overlap-note').textContent = isChorus ? 'The two annotated intervals are 3:19.43–3:22.60 and 3:22.67–3:25.60. Candy, Mrs. Bogmelon, Oswidge, Faffy and Fang each have a reference row. Model-only flags outside those intervals are not independently verified. Event rows are clickable and show peak simultaneous counts inside each interval.' : total > 0 ? 'Subtitle display intervals overlap briefly here, but simultaneous speech was not independently annotated. Check the audio before treating those intervals as confirmed overlap. Model-only flags are also candidates for listening review.' : 'No overlap annotation does not prove that voices never overlap. These intervals are the union of model flags and are candidates for manual listening review, not confirmed false alarms. A peak of 1 means the system did not mark overlapping labels within that interval.';
    renderEvents();
    drawTimeline();
  }

  function chooseClip(identifier, scroll = false) {
    stopAnimation();
    state.clipId = identifier;
    state.allEvents = false;
    setRange('focus');
    renderClip();
    if (scroll) $('#overlap').scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }

  document.querySelectorAll('[data-clip]').forEach(button => button.addEventListener('click', () => chooseClip(button.dataset.clip)));
  document.querySelectorAll('[data-explore]').forEach(button => button.addEventListener('click', () => chooseClip(button.dataset.explore, true)));
  document.querySelectorAll('[data-window]').forEach(button => button.addEventListener('click', () => {
    stopAnimation();
    setRange(button.dataset.window);
    drawTimeline();
  }));
  $('#time-slider').addEventListener('input', event => { stopAnimation(); setPosition(Number(event.target.value)); });
  $('#show-events').addEventListener('click', () => { state.allEvents = !state.allEvents; renderEvents(); });
  $('#animate-button').addEventListener('click', () => {
    if (state.playing) { stopAnimation(); return; }
    state.playing = true;
    if (state.position >= state.end - .1) state.position = state.start;
    $('#animate-button').textContent = 'Ⅱ';
    $('#animate-button').setAttribute('aria-label', 'Pause the timeline');
    lastFrame = performance.now();
    const frame = stamp => {
      if (!state.playing) return;
      // Replay any window in roughly 12 seconds; this is a visualization, not audio playback.
      state.position += (stamp - lastFrame) / 1000 * Math.max(1, (state.end - state.start) / 12);
      lastFrame = stamp;
      if (state.position >= state.end) { setPosition(state.end); stopAnimation(); return; }
      updateCursor();
      animation = requestAnimationFrame(frame);
    };
    animation = requestAnimationFrame(frame);
  });
  $('.print-action').addEventListener('click', () => { stopAnimation(); window.print(); });
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(drawTimeline, 120);
  });
  setRange('focus');
  renderClip();
})();
