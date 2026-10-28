'use strict';
/* Official NBU reference rates. No guessed values and no automatic trading quotes. */
(() => {
  const bar = document.querySelector('#fx-bar');
  if (!bar) return;
  const update = document.querySelector('#fx-date');
  const rows = {PLN:document.querySelector('#fx-pln'), USD:document.querySelector('#fx-usd')};
  const formatter = new Intl.NumberFormat('uk-UA',{minimumFractionDigits:2,maximumFractionDigits:2});
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
  function paint(data) {
    if (!data || !['ok','cached'].includes(data.status) || !data.rates) throw new Error('No recent rates');
    const dates = [];
    for (const code of ['PLN','USD']){
      const rate=data.rates[code];
      if (!rate || !valid(rate.uah) || !/^\d{4}-\d{2}-\d{2}$/.test(rate.date)) throw new Error('Invalid currency data');
      dates.push(rate.date);
    }
    for (const code of ['PLN','USD']) {
      const rate = data.rates[code];
      const node = rows[code];
      node.textContent=formatter.format(rate.uah)+' ₴';
      node.closest('.fx-quote').setAttribute('aria-label','1 '+code+' дорівнює '+formatter.format(rate.uah)+' гривні, офіційний курс НБУ на '+rate.date);
    }
    const stamp = dates[0]===dates[1]?dates[0]:dates.join(' / ');
    const date = dates[0]===dates[1] ? new Date(dates[0]+'T12:00:00Z') : null;
    update.textContent=(data.status==='cached'?'Збережений курс НБУ · ':'НБУ · ')+
      (date?date.toLocaleDateString('uk-UA',{day:'numeric',month:'short'}):stamp);
    update.title='Офіційний довідковий курс НБУ, не курс купівлі чи продажу. Дата: '+stamp;
  }
  async function refresh(){
    try{
      const response=await fetch('./currency.json',{cache:'no-store'});
      if(!response.ok)throw new Error('currency data failed');
      paint(await response.json());
    }catch{
      rows.PLN.textContent='—';rows.USD.textContent='—';
      update.textContent='НБУ · недоступно';
      update.title='Не вдалося отримати офіційні курси';
    }
  }
  refresh();
  setInterval(refresh,30*60*1000);
})();
