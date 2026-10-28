'use strict';
/* Monobank bank quotes; no date is displayed in the Pulse header. */
(() => {
  const bar = document.querySelector('#fx-bar');
  if (!bar) return;
  const rows = {PLN:document.querySelector('#fx-pln'), USD:document.querySelector('#fx-usd')};
  const formatter = new Intl.NumberFormat('uk-UA',{minimumFractionDigits:2,maximumFractionDigits:2});
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
  function paint(data) {
    if (!data || data.source !== 'Monobank' || !['ok','cached'].includes(data.status) || !data.rates) throw new Error('No recent rates');
    for (const code of ['PLN','USD']) {
      const rate = data.rates[code];
      if (!rate || !valid(rate.uah) || !['sell','cross'].includes(rate.kind)) throw new Error('Invalid currency data');
    }
    for (const code of ['PLN','USD']) {
      const rate = data.rates[code];
      const node = rows[code];
      node.textContent=formatter.format(rate.uah)+' ₴';
      const description=rate.kind==='sell' ? 'курс продажу Monobank' : 'крос-курс Monobank';
      node.closest('.fx-quote').setAttribute('aria-label','1 '+code+' — '+formatter.format(rate.uah)+' гривні, '+description);
      node.closest('.fx-quote').title=description;
    }
  }
  async function refresh() {
    try {
      const response=await fetch('./currency.json',{cache:'no-store'});
      if(!response.ok) throw new Error('Currency data unavailable');
      paint(await response.json());
    } catch {
      rows.PLN.textContent='—';rows.USD.textContent='—';
    }
  }
  refresh();
  setInterval(refresh,30*60*1000);
})();
