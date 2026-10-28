'use strict';
/* Hand-curated, organizer-verified event data. No client-side event scraping. */
const eventSection = document.querySelector('#events-section');
const eventTrack = document.querySelector('#events-track');
const eventFilters = [...document.querySelectorAll('[data-events-region]')];
const eventPrev = document.querySelector('#events-prev');
const eventNext = document.querySelector('#events-next');
let curatedEvents = [];
const embeddedEvents = /* PULSE_BUILD_EVENTS_JSON */ [];
const accessibleCountries = {
  'Польща': 'PL', 'Німеччина': 'EU', 'Чехія': 'EU', 'Словаччина': 'EU',
  'Румунія': 'EU', 'Італія': 'EU', 'Угорщина': 'EU', 'Австрія': 'EU'
};
let eventRegion = 'PL';

function eventDay() {
  const now = new Date();
  return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0')].join('-');
}
function eventDateLabel(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  const date = new Date(year, month - 1, day, 12);
  return date.toLocaleDateString('uk-UA', { day: 'numeric', month: 'short' });
}
function eventRange(event) {
  if (event.start === event.end) return eventDateLabel(event.start);
  const [sy, sm, sd] = event.start.split('-');
  const [ey, em, ed] = event.end.split('-');
  if (sy === ey && sm === em) return sd.replace(/^0/, '') + '–' + ed.replace(/^0/, '') + ' ' + eventDateLabel(event.end).split(' ').slice(1).join(' ');
  return eventDateLabel(event.start) + ' – ' + eventDateLabel(event.end);
}
function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value) node.textContent = value;
  return node;
}
function safeEventUrl(raw) {
  try {
    const url = new URL(raw);
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
function eventIsValid(event) {
  return event && /^\d{4}-\d{2}-\d{2}$/.test(event.start || '') &&
    /^\d{4}-\d{2}-\d{2}$/.test(event.end || '') && event.start <= event.end &&
    event.end >= eventDay() && accessibleCountries[event.country] === event.region &&
    ['AI', 'Product', 'Design'].includes(event.topic) && safeEventUrl(event.url) &&
    ['free', 'paid', 'mixed', 'unknown'].includes(event.fee) &&
    typeof event.title === 'string' && typeof event.city === 'string';
}
function updateEventArrows() {
  const overflow = eventTrack.scrollWidth - eventTrack.clientWidth;
  eventPrev.disabled = overflow <= 2 || eventTrack.scrollLeft <= 2;
  eventNext.disabled = overflow <= 2 || eventTrack.scrollLeft >= overflow - 2;
}
function renderEvents() {
  const events = curatedEvents.filter(item => item.region === eventRegion);
  eventFilters.forEach(button => {
    const active = button.dataset.eventsRegion === eventRegion;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  eventTrack.replaceChildren();
  for (const event of events) {
    const card = element('article', 'event-card');
    card.dataset.topic = event.topic;
    const top = element('div', 'event-top');
    const date = element('time', 'event-date', eventRange(event));
    date.dateTime = event.start;
    const fee = element('span', 'event-fee event-fee--' + event.fee, event.fee_label || 'Ціну уточнюйте');
    top.append(date, fee);
    const title = element('h3', 'event-title', event.title);
    const description = element('p', 'event-description', event.description || '');
    const location = element('p', 'event-location', event.city + ' · ' + event.country);
    const bottom = element('div', 'event-bottom');
    bottom.append(element('span', 'event-organizer', event.organizer || ''));
    const action = element('a', 'event-action', 'Програма та участь ↗');
    action.href = safeEventUrl(event.url);
    action.target = '_blank';
    action.rel = 'noopener noreferrer';
    action.setAttribute('aria-label', 'Програма та участь: ' + event.title);
    bottom.append(action);
    card.append(top, title, description, location, bottom);
    eventTrack.append(card);
  }
  if (!events.length) eventTrack.append(element('p', 'event-empty', 'Немає найближчих подій для цього регіону.'));
  eventSection.hidden = false;
  eventTrack.scrollLeft = 0;
  requestAnimationFrame(updateEventArrows);
}
async function loadCuratedEvents() {
  // Embedded at build time, so a failed second request never removes the slider.
  curatedEvents = embeddedEvents.filter(eventIsValid)
    .sort((a, b) => a.start.localeCompare(b.start));
  renderEvents();
  try {
    const response = await fetch('./events.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('Events data unavailable');
    const data = await response.json();
    const incoming = (Array.isArray(data.events) ? data.events : [])
      .filter(eventIsValid).sort((a, b) => a.start.localeCompare(b.start));
    if (incoming.length || !curatedEvents.length) {
      curatedEvents = incoming;
      renderEvents();
    }
  } catch (error) {
    console.warn('Pulse events: using local event data', error);
  }
}
eventFilters.forEach(button => {
  button.addEventListener('click', () => {
    eventRegion = button.dataset.eventsRegion;
    renderEvents();
  });
});
[eventPrev, eventNext].forEach((button, index) => button.addEventListener('click', () => {
  const first = eventTrack.querySelector('.event-card');
  eventTrack.scrollBy({ left: (index ? 1 : -1) * ((first?.getBoundingClientRect().width || 310) + 12), behavior: 'smooth' });
}));
eventTrack.addEventListener('scroll', updateEventArrows, { passive: true });
window.addEventListener('resize', updateEventArrows);
loadCuratedEvents();
