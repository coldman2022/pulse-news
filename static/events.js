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

const calendarRoot = document.querySelector('#events-calendar');
const calendarToggle = document.querySelector('#events-calendar-toggle');
const calendarGrid = document.querySelector('#events-calendar-grid');
const calendarMonthName = document.querySelector('#events-calendar-month');
const calendarMessage = document.querySelector('#events-calendar-status');
const calendarPrevious = document.querySelector('#events-month-prev');
const calendarNext = document.querySelector('#events-month-next');
const calendarClear = document.querySelector('#events-calendar-clear');
let calendarOffset = 0;
let selectedEventDay = '';
const calendarToday = new Date();
const isoDay = (y, m, d) => [y, String(m + 1).padStart(2, '0'), String(d).padStart(2, '0')].join('-');


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

function renderCalendar(){
  if (calendarRoot.hidden) return;
  const first=new Date(calendarToday.getFullYear(),calendarToday.getMonth()+calendarOffset,1);
  const year=first.getFullYear(),month=first.getMonth();
  const days=new Date(year,month+1,0).getDate();
  calendarMonthName.textContent=first.toLocaleDateString('uk-UA',{month:'long',year:'numeric'});
  calendarPrevious.disabled=calendarOffset<=0;
  calendarNext.disabled=calendarOffset>=11;
  calendarGrid.replaceChildren();
  for (const label of ['Пн','Вт','Ср','Чт','Пт','Сб','Нд']){
    calendarGrid.append(element('span','events-weekday',label));
  }
  const leading=(first.getDay()+6)%7;
  for(let i=0;i<leading;i++)calendarGrid.append(element('span','events-calendar-spacer'));
  const regional=curatedEvents.filter(e=>e.region===eventRegion);
  for(let day=1;day<=days;day++){
    const key=isoDay(year,month,day);
    const matches=regional.filter(event=>event.start<=key&&event.end>=key);
    const button=element('button','events-calendar-day',String(day));
    button.type='button';
    button.dataset.date=key;
    button.setAttribute('aria-label',day+' '+first.toLocaleDateString('uk-UA',{month:'long'})+', '+matches.length+' подій');
    button.setAttribute('aria-pressed',String(selectedEventDay===key));
    if(key===eventDay())button.classList.add('is-today');
    if(selectedEventDay===key)button.classList.add('is-selected');
    if(matches.length)button.classList.add('has-events');
    if(key<eventDay()||!matches.length)button.disabled=true;
    if(matches.length){
      const dot=element('span','events-calendar-count',String(matches.length));
      dot.setAttribute('aria-hidden','true');
      button.append(dot);
      button.addEventListener('click',()=>{
        selectedEventDay=key;
        renderCalendar();
        renderEvents();
      });
    }
    calendarGrid.append(button);
  }
  calendarMessage.textContent=selectedEventDay
    ?'Події на '+eventDateLabel(selectedEventDay)+'. Натисніть «Усі дати», щоб скинути фільтр.'
    :'Натисніть дату з позначкою, щоб побачити події цього дня.';
}
calendarToggle.addEventListener('click',()=>{
  calendarRoot.hidden=!calendarRoot.hidden;
  calendarToggle.setAttribute('aria-expanded',String(!calendarRoot.hidden));
  if(!calendarRoot.hidden)renderCalendar();
});
calendarPrevious.addEventListener('click',()=>{calendarOffset=Math.max(0,calendarOffset-1);renderCalendar();});
calendarNext.addEventListener('click',()=>{calendarOffset=Math.min(11,calendarOffset+1);renderCalendar();});
calendarClear.addEventListener('click',()=>{
  selectedEventDay='';
  renderCalendar();
  renderEvents();
});

function renderEvents() {
  const events = curatedEvents.filter(item => item.region === eventRegion &&
    (!selectedEventDay || (item.start <= selectedEventDay && item.end >= selectedEventDay)));
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
    const organizer = element('span', 'event-organizer', event.organizer || '');
    organizer.title = event.organizer || '';
    bottom.append(organizer);
    const action = element('a', 'event-action', 'Програма та участь ↗');
    action.href = safeEventUrl(event.url);
    action.target = '_blank';
    action.rel = 'noopener noreferrer';
    action.setAttribute('aria-label', 'Програма та участь: ' + event.title);
    bottom.append(action);
    card.append(top, title, description, location, bottom);
    eventTrack.append(card);
  }
  if (!events.length) eventTrack.append(element('p', 'event-empty', selectedEventDay
    ? 'На цю дату немає подій. Оберіть іншу або скиньте календар.'
    : 'Немає найближчих подій для цього регіону.'));
  eventSection.hidden = false;
  eventTrack.scrollLeft = 0;
  requestAnimationFrame(updateEventArrows);
  renderCalendar();
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
    selectedEventDay = '';
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
