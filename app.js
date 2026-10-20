'use strict';
const $ = (id) => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => structuredClone(value);
const uid = prefix => prefix + '-' + crypto.randomUUID();
const routes = [['dashboard','Pulpit serwisowy'],['panels','Centrale i harmonogram'],['faults','Zgłoszenia serwisowe'],['protocols','Protokoły i historia'],['settings','Konfiguracja'],['backups','Kopie i import'],['audit','Rejestr zmian']];
let db, dbRevision, service, configRevision, version, databaseName;
let route = 'dashboard', selectedPanel = '', selectedProtocol = '', filters = {}, busy = false, editor = null, dirty = false;
function localDateTime(value = new Date()) { return new Date(value.getTime() - value.getTimezoneOffset() * 60000).toISOString().slice(0,16); }
const today = () => localDateTime().slice(0,10);
function nextDate(panel) {
    if (!panel.lastInspection || !Number.isFinite(Number(panel.intervalMonths)) || Number(panel.intervalMonths) < 1) return '';
    const [year,month,day] = panel.lastInspection.slice(0,10).split('-').map(Number);
    const target = new Date(year, month - 1 + Number(panel.intervalMonths), 1);
    const last = new Date(target.getFullYear(),target.getMonth()+1,0).getDate();
    target.setDate(Math.min(day,last));
    return localDateTime(target).slice(0,10);
}
function daysUntil(value) { return Math.round((Date.parse(value.slice(0,10)+'T12:00:00Z')-Date.parse(today()+'T12:00:00Z'))/86400000); }
function due(panel) {
    const date = nextDate(panel);
    if (!date) return {label:'Brak przeglądu',tone:'amber',rank:-100000,date:''};
    const days = daysUntil(date);
    return {label:days<0?'Po terminie':days<=service.reminderDays?'Zbliża się':'W terminie',tone:days<0?'red':days<=service.reminderDays?'amber':'green',rank:days,date};
}
const badge = (label,tone='') => `<span class="badge ${esc(tone)}">${esc(label)}</span>`;
const button = (label,action,id='',className='') => `<button type="button" class="${esc(className)}" data-action="${esc(action)}" data-id="${esc(id)}">${esc(label)}</button>`;
const panelName = id => { const p = db.panels.find(p=>p.id===id); return p ? `${p.id} · ${p.location}` : id+' (brak w ewidencji)'; };
function heading(title,subtitle,actions='') { return `<div class="page-heading"><div><h1>${esc(title)}</h1><p class="lead">${esc(subtitle)}</p></div><div class="actions">${actions}</div></div>`; }
function table(headers,rows,empty='Brak danych do wyświetlenia.') { return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}" class="empty">${esc(empty)}</td></tr>`}</tbody></table></div>`; }
function field(name,label,value='',type='text',extra='',full=false) { return `<div class="field ${full?'full':''}"><label for="f-${esc(name)}">${esc(label)}</label>${type==='textarea'?`<textarea id="f-${esc(name)}" name="${esc(name)}" ${extra}>${esc(value)}</textarea>`:`<input id="f-${esc(name)}" name="${esc(name)}" type="${type}" value="${esc(value)}" ${extra}>`}</div>`; }
function options(values,value) { return values.map(v=>{ const [id,label]=Array.isArray(v)?v:[v,v]; return `<option value="${esc(id)}" ${id===value?'selected':''}>${esc(label)}</option>`; }).join(''); }
function select(name,label,values,value='',extra='') { return `<div class="field"><label for="f-${esc(name)}">${esc(label)}</label><select id="f-${esc(name)}" name="${esc(name)}" ${extra}>${options(values,value)}</select></div>`; }
function details(values) { return `<dl class="detail-list">${values.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v||'—')}</dd>`).join('')}</dl>`; }
function toolbar(statuses,placeholder='Szukaj…') { return `<div class="toolbar"><input id="search" aria-label="Szukaj" placeholder="${esc(placeholder)}" value="${esc(filters.search||'')}"><select id="filter" aria-label="Filtr">${options([['','Wszystkie'],...statuses],filters.status||'')}</select></div>`; }
function matches(record) { return !filters.search || JSON.stringify(record).toLocaleLowerCase('pl').includes(filters.search.toLocaleLowerCase('pl')); }
function notice(message,error=false) { $('notification').innerHTML = `<div class="${error?'error':'notice'}">${esc(message)}</div>`; }
async function api(path, method='GET', data) {
    let response;
    try { response = await fetch(path, {method, headers:{'X-SSP-Client':'local',...(data===undefined?{}:{'Content-Type':'application/json'})}, body:data===undefined?undefined:JSON.stringify(data), signal:AbortSignal.timeout(20000)}); }
    catch(e) { throw new Error('Brak połączenia z lokalnym serwerem. Sprawdź okno Uruchom.bat. Formularz pozostaje otwarty.'); }
    let result;
    try { result=await response.json(); } catch(e) { throw new Error('Nieprawidłowa odpowiedź serwera.'); }
    if (!response.ok) throw new Error(result.error || 'Nie udało się wykonać operacji.');
    return result;
}
async function persist(candidate,mode) {
    const result=await api('/api/database','PUT',{revision:dbRevision,database:candidate,...(mode?{mode}:{})});
    db=result.database; dbRevision=result.revision;
    $('storage-status').textContent=`SSP Polon ${version} · ${databaseName} · Zapisano ${new Date().toLocaleTimeString('pl-PL')} · Offline`;
}
function renderNav() { $('navigation').innerHTML=routes.map(([id,label])=>`<button data-action="navigate" data-id="${id}" class="${route===id?'active':''}" ${route===id?'aria-current="page"':''}>${esc(label)}</button>`).join(''); }
function navigate(target) { route=target; filters={}; selectedPanel='';selectedProtocol=''; render(); }
function render() {
    renderNav();
    $('site-label').textContent=service.site || 'Obsługa i utrzymanie systemów sygnalizacji pożarowej';
    const views={dashboard:renderDashboard,panels:renderPanels,faults:renderFaults,protocols:renderProtocols,settings:renderSettings,backups:renderBackups,audit:renderAudit};
    views[route]();
}
function renderDashboard() {
    const active=db.panels.filter(p=>!p.archived), faults=db.faults.filter(f=>f.status!=='Zamknięte');
    const pending=active.filter(p=>due(p).rank<=service.reminderDays).sort((a,b)=>due(a).rank-due(b).rank);
    const late=faults.filter(f=>f.dueDate&&daysUntil(f.dueDate)<0);
    $('content').innerHTML=heading('Pulpit serwisowy',new Date().toLocaleDateString('pl-PL',{weekday:'long',day:'numeric',month:'long',year:'numeric'}),button('Nowe zgłoszenie','new-fault','','primary'))+
      `<div class="cards">${[['Aktywne centrale',active.length,''],['Otwarte zgłoszenia',faults.length,'red'],['Przeglądy do obsługi',pending.length,'amber'],['Protokoły robocze',db.history.filter(h=>h.protocolStatus==='draft').length,'blue']].map(([label,n,tone])=>`<div class="card"><div class="card-label">${esc(label)}</div><div class="metric">${n}</div>${badge(tone==='amber'?`Horyzont ${service.reminderDays} dni`:'Stan bieżący',tone)}</div>`).join('')}</div>`+
      (late.length?`<div class="notice warning">${late.length} zgłoszeń przekroczyło planowany termin realizacji.</div>`:'')+
      `<div class="grid2"><section><h2>Najbliższe przeglądy</h2>${table(['Centrala','Termin','Stan',''],pending.slice(0,8).map(p=>`<tr><td>${button(p.id,'panel-card',p.id,'link')}<br><span class="muted">${esc(p.location)}</span></td><td>${esc(nextDate(p)||'Nie ustalono')}</td><td>${badge(due(p).label,due(p).tone)}</td><td>${button('Przegląd','new-inspection',p.id,'small')}</td></tr>`),'Brak zaległych lub zbliżających się przeglądów.')}</section><section><h2>Zgłoszenia wymagające obsługi</h2>${faultTable(faults.sort((a,b)=>priorityRank(b)-priorityRank(a)||a.date.localeCompare(b.date)).slice(0,8),true)}</section></div>`+
      (!active.length?`<div class="panel"><h2>Zacznij od ewidencji</h2><p>Dodaj pierwszą centralę lub zaimportuj bazę poprzedniej wersji.</p>${button('Dodaj centralę','new-panel','','primary')} ${button('Import bazy','navigate','backups')}</div>`:'');
}
function renderPanels() {
    if(selectedPanel) return renderPanelCard(selectedPanel);
    const rows=db.panels.filter(p=>matches(p)&&(!filters.status? !p.archived: filters.status==='Archiwum'?p.archived:!p.archived&&due(p).label===filters.status));
    $('content').innerHTML=heading('Centrale i harmonogram','Ewidencja urządzeń, stan techniczny i terminy obsługi.',button('Dodaj centralę','new-panel','','primary'))+
      toolbar(['Po terminie','Zbliża się','Brak przeglądu','W terminie','Archiwum'],'Kod, model, obiekt, numer seryjny…')+
      table(['Centrala','Lokalizacja','Stan techniczny','Ostatni przegląd','Następny termin',''],rows.map(p=>`<tr><td>${button(p.id,'panel-card',p.id,'link')}<br>${esc(p.model)}</td><td>${esc(p.location)}<br><span class="muted">${esc(p.spot)}</span></td><td>${badge(p.archived?'Archiwum':p.condition,p.condition==='Wymaga serwisu'?'red':'')}</td><td>${esc(p.lastInspection||'—')}</td><td>${esc(nextDate(p)||'—')}<br>${badge(due(p).label,due(p).tone)}</td><td><div class="actions">${button('Edytuj','edit-panel',p.id,'small')}${!p.archived?button('Przegląd','new-inspection',p.id,'small'):''}</div></td></tr>`));
}
function renderPanelCard(id) {
    const p=db.panels.find(p=>p.id===id);if(!p){selectedPanel='';return renderPanels();}
    const faults=db.faults.filter(f=>f.panelId===id), history=db.history.filter(h=>h.panelId===id);
    $('content').innerHTML=heading(p.id,p.location,button('Powrót','navigate','panels')+button('Edytuj','edit-panel',id)+(!p.archived?button('Nowy przegląd','new-inspection',id,'primary'):''))+
      `<div class="grid2"><section class="panel"><h2>Dane techniczne</h2>${details([['Model',p.model],['Dokładne miejsce',p.spot],['Nr seryjny',p.serialNo],['Stan',p.condition],['Interwał',p.intervalMonths+' miesięcy'],['Ostatni przegląd',p.lastInspection],['Kolejny termin',nextDate(p)],['Uwagi',p.notes]])}</section><section class="panel"><h2>Obsługa urządzenia</h2><p>${faults.filter(f=>f.status!=='Zamknięte').length} otwartych zgłoszeń · ${history.length} wpisów historii</p><div class="actions">${!p.archived?button('Zgłoś usterkę','new-fault',id)+button('Protokół serwisu','new-protocol',id):''}${button(p.archived?'Przywróć do ewidencji':'Archiwizuj centralę','archive-panel',id,'danger')}</div><p class="hint">Archiwizacja zachowuje historię. Najpierw zamknij otwarte zgłoszenia i protokoły robocze.</p></section></div><h2>Zgłoszenia centrali</h2>${faultTable(faults)}<h2 class="section-title">Protokoły i historia</h2>${protocolTable(history)}`;
}
const priorityRank = f => ['Niski','Normalny','Wysoki','Krytyczny'].indexOf(f.priority);
function faultTable(rows,compact=false) {
    return table(compact?['Zgłoszenie','Priorytet','']:['Zgłoszenie / data','Centrala','Priorytet / termin','Odpowiedzialny','Status',''],rows.map(f=>`<tr><td>${button(f.id,'edit-fault',f.id,'link')}<br>${esc(f.desc.slice(0,110))}${f.desc.length>110?'…':''}${!compact?`<br><span class="muted">${esc(f.date)}</span>`:''}</td>${!compact?`<td>${button(f.panelId,'panel-card',f.panelId,'link')}</td>`:''}<td>${badge(f.priority||'Normalny',priorityRank(f)>=2?'red':'')}<br>${!compact?esc(f.dueDate||'—'):''}${f.status!=='Zamknięte'&&f.dueDate&&daysUntil(f.dueDate)<0?'<br>'+badge('Po terminie','red'):''}</td>${!compact?`<td>${esc(f.assignee||'Nie przypisano')}</td><td>${badge(f.status,f.status==='Zamknięte'?'green':'amber')}</td>`:''}<td>${f.status!=='Zamknięte'?button('Obsłuż','service-fault',f.id,'small'):button('Szczegóły','edit-fault',f.id,'small')}</td></tr>`));
}
function renderFaults() {
    const rows=db.faults.filter(f=>matches(f)&&(!filters.status||f.status===filters.status)).sort((a,b)=>b.date.localeCompare(a.date));
    $('content').innerHTML=heading('Zgłoszenia serwisowe','Od zgłoszenia usterki do udokumentowanego zakończenia naprawy.',button('Nowe zgłoszenie','new-fault','','primary'))+toolbar(['Nowe','W trakcie','Oczekujące','Zamknięte'],'Opis, centrala, odpowiedzialny…')+faultTable(rows);
}
function protocolLabel(h) { return h.protocolStatus==='draft'?'Roboczy':h.protocolStatus==='final'?'Zatwierdzony':'Wpis historyczny'; }
function protocolTable(rows) {
    return table(['Numer / data','Centrala','Rodzaj','Wykonawca','Wynik / stan',''],rows.slice().sort((a,b)=>b.date.localeCompare(a.date)).map(h=>`<tr><td>${button(h.protocolNo||'Szkic — bez numeru','view-protocol',h.id,'link')}<br><span class="muted">${esc(h.date)}</span></td><td>${esc(h.panelId)}</td><td>${esc(h.type)}</td><td>${esc(h.technician||h.contractor)}</td><td>${badge(h.result||'Nie określono',h.result==='Pozytywny'?'green':h.result?'red':'')}<br>${badge(protocolLabel(h),h.protocolStatus==='draft'?'amber':'')}</td><td>${h.protocolStatus==='draft'?button('Edytuj','edit-protocol',h.id,'small'):button('Dokument','view-protocol',h.id,'small')}</td></tr>`));
}
function renderProtocols() {
    if(selectedProtocol) return renderProtocolView(selectedProtocol);
    const rows=db.history.filter(h=>matches(h)&&(!filters.status||h.protocolStatus===filters.status)&&(!filters.from||h.date.slice(0,10)>=filters.from)&&(!filters.to||h.date.slice(0,10)<=filters.to));
    $('content').innerHTML=heading('Protokoły i historia','Szkice robocze, zatwierdzone dokumenty i wpisy z poprzedniej wersji.',button('Nowy protokół','new-protocol','','primary'))+
      toolbar([['draft','Robocze'],['final','Zatwierdzone'],['legacy','Wpisy historyczne']],'Numer protokołu, opis, wykonawca…')+
      `<div class="toolbar"><label>Od <input id="date-from" type="date" value="${esc(filters.from||'')}"></label><label>Do <input id="date-to" type="date" value="${esc(filters.to||'')}"></label><span class="hint">${rows.length} wpisów</span></div>`+protocolTable(rows);
}
function documentHTML(h) {
    const p=h.panelSnapshot||db.panels.find(p=>p.id===h.panelId)||{id:h.panelId};
    const s=h.serviceSnapshot||service;
    return `<article class="protocol-preview">${h.protocolStatus!=='final'?`<div class="draft-mark">${h.protocolStatus==='draft'?'DOKUMENT ROBOCZY — NIEZATWIERDZONY':'WYDRUK WPISU HISTORYCZNEGO — dane firmy i centrali według aktualnej ewidencji'}</div>`:''}
      <div class="document-head"><div><strong>${esc(s.company||'Firma / jednostka serwisowa — nie uzupełniono')}</strong><br>${esc(s.address)}<br>${s.taxId?'NIP: '+esc(s.taxId):''}<br>${esc([s.phone,s.email].filter(Boolean).join(' · '))}</div><div><strong>${esc(s.site||'Obiekt — nie uzupełniono')}</strong><br>${esc(s.siteAddress)}</div></div>
      <h1>Protokół: ${esc(h.type)}</h1><p><strong>${esc(h.protocolNo||'Szkic bez numeru')}</strong> · Data wykonania: ${esc(h.date)}</p>
      ${details([['Centrala / model',`${p.id||''} / ${p.model||''}`],['Lokalizacja',[p.location,p.spot].filter(Boolean).join(' — ')],['Numer seryjny',p.serialNo],['Wykonawca',h.technician||h.contractor],['Zgłoszenie',h.faultId],['Uzupełnienie protokołu',h.referenceProtocolNo],['Zakres',h.scope]])}
      ${(h.checklist||[]).length?'<h3>Kontrole i pomiary — zadeklarowany zakres</h3>'+table(['Czynność','Wynik','Pomiar / uwagi'],h.checklist.map(c=>`<tr><td>${esc(c.label)}</td><td>${esc(c.result||'Nie oceniono')}</td><td class="preline">${esc(c.note)}</td></tr>`)):''}
      <h3>Opis prac i ustalenia</h3><div class="preline">${esc(h.desc||'—')}</div><h3>Wynik: ${esc(h.result||'Nie określono')}</h3>
      <h3>Zalecenia i ograniczenia</h3><div class="preline">${esc(h.recom||'Brak wpisanych zaleceń.')}</div>
      <h3>Części i materiały</h3><div class="preline">${esc(h.parts||'Nie odnotowano.')}</div><p>Czas pracy: ${esc(h.hours||0)} godz.</p>
      ${h.type==='Przegląd'&&h.result==='Pozytywny'&&Number.isFinite(p.intervalMonths)?`<p>Planowany kolejny przegląd: <strong>${esc(nextDate({...p,lastInspection:h.date}))}</strong> (interwał ${esc(p.intervalMonths)} mies.)</p>`:''}
      <div class="signatures"><div>${esc(h.technician||h.contractor||'Wykonawca')}<br>Data i podpis wykonawcy</div><div>${esc(h.recipient||'Przedstawiciel obiektu')}<br>Data i podpis odbiorcy</div></div>
      <p class="hint">Dokument obejmuje zakres opisany powyżej. Podpisy należy złożyć na wydruku. ${h.finalizedAt?'Zatwierdzono w aplikacji: '+esc(h.finalizedAt):''}</p></article>`;
}
function renderProtocolView(id) {
    const h=db.history.find(h=>h.id===id);if(!h){selectedProtocol='';return renderProtocols();}
    $('content').innerHTML=heading(h.protocolNo||'Protokół roboczy',protocolLabel(h),button('Powrót','navigate','protocols')+(h.protocolStatus==='draft'?button('Edytuj','edit-protocol',id,'primary')+button('Usuń szkic','delete-draft',id,'danger'):button('Protokół uzupełniający','followup-protocol',id))+button('Drukuj / PDF','print-protocol',id))+documentHTML(h);
}
function settingsFields(s) {
    return `<div class="form-grid">${field('company','Firma / jednostka serwisowa',s.company)}${field('taxId','NIP',s.taxId)}${field('address','Adres firmy',s.address)}${field('phone','Telefon',s.phone)}${field('email','E-mail',s.email,'email')}${field('site','Nazwa obiektu',s.site)}${field('siteAddress','Adres obiektu',s.siteAddress)}${field('protocolPrefix','Prefiks numeracji',s.protocolPrefix,'text','required pattern="[A-Za-z0-9_-]{1,16}"')}${field('inspectionMonths','Domyślny interwał przeglądów (mies.)',s.inspectionMonths,'number','required min="1" max="120"')}${field('reminderDays','Wyprzedzenie przypomnień (dni)',s.reminderDays,'number','required min="1" max="365"')}${field('technicians','Technicy — jeden w każdym wierszu',s.technicians.join('\n'),'textarea','',true)}${field('checklist','Szablon kontroli przeglądu — jedna czynność w wierszu',s.checklist.join('\n'),'textarea','',true)}</div>`;
}
function renderSettings() {
    $('content').innerHTML=heading('Konfiguracja serwisu','Dane zapisywane w config.json. Zatwierdzone dokumenty zachowują wcześniejsze dane.')+
      `<div class="panel"><h2>${esc(service.company||'Nie uzupełniono firmy')}</h2>${details([['Obiekt',service.site],['Adres',service.address],['Numeracja',service.protocolPrefix+'/ROK/0001'],['Domyślny interwał',service.inspectionMonths+' miesięcy'],['Technicy',service.technicians.join(', ')],['Lista kontrolna',service.checklist.length+' czynności']])}<p class="hint">Szablon listy kontrolnej dostosuj do dokumentacji urządzeń i procedur obiektu. Nie jest on potwierdzeniem zgodności z normą. Zmiana szablonu dotyczy nowych szkiców.</p>${button('Edytuj konfigurację','edit-settings','','primary')}</div>`;
}
async function renderBackups() {
    $('content').innerHTML=heading('Kopie zapasowe i import','Przechowujemy 30 ostatnich kopii bazy; dodatkowo plik .bak zawiera poprzedni zapis.')+
      `<div class="panel"><div class="actions">${button('Eksportuj bazę JSON','export','','primary')}${button('Utwórz kopię teraz','backup')}${button('Importuj / przywróć bazę','import','','danger')}</div><p class="hint">Import zastępuje bieżącą bazę po potwierdzeniu. Przed zmianą powstaje kopia. Konfigurację firmy kopiuj osobno razem z config.json. Kopie w tym samym folderze nie chronią przed awarią dysku.</p></div><div id="backup-list">Odczytywanie kopii…</div>`;
    try { const items=await api('/api/backups');if(!$('backup-list'))return;$('backup-list').innerHTML=table(['Plik','Rozmiar',''],items.map(x=>`<tr><td>${esc(x.name)}</td><td>${Math.ceil(x.size/1024)} KB</td><td>${button('Pobierz','download-backup',x.name,'small')}</td></tr>`),'Nie utworzono jeszcze kopii.'); }
    catch(e){if($('backup-list'))$('backup-list').textContent=e.message;}
}
function renderAudit() {
    $('content').innerHTML=heading('Rejestr zmian','Lokalny dziennik ostatnich 1000 zapisów. Nie jest to dziennik uwierzytelnionych użytkowników.')+table(['Czas','Operacja','Zmiany'],(db.audit||[]).slice().reverse().map(a=>`<tr><td>${esc(a.date)}</td><td>${esc(a.action)}</td><td class="preline">${esc((a.details||[]).join('\n'))}</td></tr>`));
}
function modal(kind,title,html,record=null,actions='') {
    editor={kind,record};dirty=false;$('editor-title').textContent=title;$('editor-fields').innerHTML=html;
    $('form-error').textContent='';$('editor-actions').innerHTML=button('Anuluj','close-modal')+(actions||'<button type="submit" class="primary">Zapisz</button>');$('editor').showModal();
}
function closeModal(force=false) {
    if(busy)return;
    if(!force&&dirty&&!confirm('Odrzucić niezapisane zmiany w formularzu?'))return;
    $('editor').close();editor=null;dirty=false;
}
function activePanels() { return db.panels.filter(p=>!p.archived).map(p=>[p.id,panelName(p.id)]); }
function openPanel(id) {
    const p=db.panels.find(p=>p.id===id)||{id:'',model:'Polon 6000',location:'',spot:'',serialNo:'',intervalMonths:service.inspectionMonths,lastInspection:'',condition:'Niezweryfikowana',notes:''};
    modal('panel',id?'Edycja centrali':'Nowa centrala',`<div class="form-grid">${field('id','Kod centrali',p.id,'text',`required maxlength="120" ${id?'readonly':''}`)}${field('model','Model',p.model,'text','required')}${field('location','Budynek / lokalizacja',p.location,'text','required')}${field('spot','Dokładne miejsce',p.spot)}${field('serialNo','Numer seryjny',p.serialNo)}${field('intervalMonths','Interwał przeglądów (mies.)',p.intervalMonths,'number','required min="1" max="120"')}${field('lastInspection','Ostatni pozytywny przegląd',p.lastInspection.replace(' ','T'),'datetime-local')}${select('condition','Stan techniczny',Array.from(new Set(['Niezweryfikowana','Sprawna','Wymaga serwisu','W trakcie naprawy','Wyłączona',p.condition])),p.condition)}${field('notes','Uwagi techniczne',p.notes,'textarea','',true)}</div>`,id?p:null);
}
function openFault(id,panelId='') {
    if(!activePanels().length&&!id){notice('Najpierw dodaj aktywną centralę.',true);return;}
    const f=db.faults.find(f=>f.id===id)||{id:uid('A'),date:localDateTime(),panelId:panelId||activePanels()[0]?.[0],reporter:'',desc:'',status:'Nowe',priority:'Normalny',assignee:'',dueDate:''};
    const panels=activePanels();if(!panels.some(([id])=>id===f.panelId))panels.push([f.panelId,panelName(f.panelId)]);
    modal('fault',id?'Zgłoszenie '+id:'Nowe zgłoszenie',`<div class="form-grid">${field('date','Data zgłoszenia',f.date.replace(' ','T'),'datetime-local','required')}${select('panelId','Centrala',panels,f.panelId,'required')}${field('reporter','Zgłaszający',f.reporter,'text','required')}${select('priority','Priorytet',['Niski','Normalny','Wysoki','Krytyczny'],f.priority)}${field('assignee','Odpowiedzialny',f.assignee,'text','list="technicians"')}${field('dueDate','Planowany termin',f.dueDate,'date')}${select('status','Status',f.status==='Zamknięte'?['Zamknięte','W trakcie']:['Nowe','W trakcie','Oczekujące'],f.status)}${field('desc','Opis usterki',f.desc,'textarea','required',true)}</div><datalist id="technicians">${options(service.technicians,'')}</datalist><p class="hint">Zamknięcie następuje przez pozytywny zatwierdzony protokół. Zmiana statusu zamkniętego zgłoszenia na „W trakcie” otwiera je ponownie.</p>`,id?f:{...f,_new:true});
}
function openProtocol(id,panelId='',faultId='',inspection=false,sourceId='') {
    if(!activePanels().length){notice('Najpierw dodaj aktywną centralę.',true);return;}
    const old=db.history.find(h=>h.id===id);if(old&&old.protocolStatus!=='draft'){notice('Zatwierdzony dokument jest niezmienny.',true);return;}
    const source=db.history.find(h=>h.id===sourceId), fault=db.faults.find(f=>f.id===faultId);
    const h=old||{id:uid('PROT'),protocolStatus:'draft',protocolNo:'',date:localDateTime(),panelId:panelId||fault?.panelId||source?.panelId||activePanels()[0][0],type:inspection?'Przegląd':fault?'Naprawa':'Serwis',technician:'',recipient:'',scope:'',desc:source?'Uzupełnienie protokołu '+(source.protocolNo||source.id)+'. ':fault?'Obsługa zgłoszenia: '+fault.desc:'',recom:'',result:'',parts:'',hours:0,faultId:faultId||'',relatedProtocolId:source?.id||'',referenceProtocolNo:source?.protocolNo||'',closeFault:false,checklist:service.checklist.map(label=>({label,result:'',note:''}))};
    const linkedFaults=db.faults.filter(f=>f.status!=='Zamknięte'||f.id===h.faultId).map(f=>[f.id,f.id+' · '+f.panelId+' · '+f.desc.slice(0,60)]);
    const html=`<p class="hint">Szkic można zapisać w trakcie pracy. Numer zostanie nadany przy zatwierdzeniu. Zatwierdzonego dokumentu nie można edytować.</p><div class="form-grid">${select('panelId','Centrala',activePanels(),h.panelId,'required')}${select('type','Rodzaj prac',['Przegląd','Naprawa','Serwis','Wymiana akumulatorów/podzespołów','Kontrola'],h.type)}${field('date','Data wykonania',h.date.replace(' ','T'),'datetime-local','required')}${field('technician','Wykonawca / technik',h.technician||h.contractor,'text','list="technicians"')}${field('recipient','Przedstawiciel obiektu / odbiorca',h.recipient)}${select('faultId','Powiązane zgłoszenie',[['','Bez zgłoszenia'],...linkedFaults],h.faultId)}${field('scope','Zakres prac / objęte elementy',h.scope,'textarea','',true)}</div><datalist id="technicians">${options(service.technicians,'')}</datalist><h3>Lista kontrolna</h3><p class="hint">Podaj rzeczywisty wynik i pomiary. „Nie dotyczy” oznacza wyłączenie danej czynności z zakresu.</p>${h.checklist.map((c,i)=>`<div class="check-row"><label for="check-${i}">${esc(c.label)}</label><select id="check-${i}" name="check-${i}" aria-label="Wynik: ${esc(c.label)}">${options([['','Nie oceniono'],'OK','Usterka','Nie dotyczy'],c.result)}</select><textarea name="note-${i}" aria-label="Pomiar i uwagi: ${esc(c.label)}" placeholder="Pomiar / uwagi">${esc(c.note)}</textarea></div>`).join('')}<div class="form-grid section-title">${select('result','Wynik końcowy',[['','Wybierz wynik'],'Pozytywny','Warunkowy','Negatywny'],h.result)}${field('hours','Czas pracy (godz.)',h.hours,'number','min="0" max="10000" step="0.25"')}${field('desc','Opis wykonanych prac i ustalenia',h.desc,'textarea','',true)}${field('recom','Zalecenia / ograniczenia / dalsze działania',h.recom,'textarea','',true)}${field('parts','Części i materiały — nazwa, ilość, parametry',h.parts,'textarea','',true)}</div><label class="checkbox"><input type="checkbox" name="closeFault" ${h.closeFault?'checked':''}>Zamknij powiązane zgłoszenie po pozytywnym zatwierdzeniu</label>`;
    modal('protocol',old?'Edycja protokołu roboczego':'Nowy protokół',html,h,'<button type="submit" name="intent" value="draft">Zapisz szkic</button><button type="submit" name="intent" value="final" class="primary">Zatwierdź protokół</button>');
}
async function saveEditor(event) {
    event.preventDefault();if(busy)return;
    const form=event.currentTarget;if(!form.reportValidity())return;
    const values=Object.fromEntries(new FormData(form)), kind=editor.kind, old=editor.record;
    const candidate=clone(db);
    try {
        if(kind==='panel') {
            values.id=values.id.trim();values.intervalMonths=Number(values.intervalMonths);values.lastInspection=values.lastInspection.replace('T',' ');
            if(!values.id)throw new Error('Podaj kod centrali.');
            if(!old&&candidate.panels.some(p=>p.id.toLocaleLowerCase()===values.id.toLocaleLowerCase()))throw new Error('Centrala o takim kodzie już istnieje.');
            const record={...(old||{}),...values,archived:old?.archived||false};
            if(old)candidate.panels[candidate.panels.findIndex(p=>p.id===old.id)]=record;else candidate.panels.push(record);
        } else if(kind==='fault') {
            const record={...old,...values,date:values.date.replace('T',' ')};delete record._new;
            if(old._new)candidate.faults.push(record);else candidate.faults[candidate.faults.findIndex(f=>f.id===old.id)]=record;
        } else if(kind==='protocol') {
            const final=event.submitter?.value==='final';
            if(final&&!confirm('Zatwierdzić protokół? Otrzyma numer i zostanie zablokowany do edycji. Sprawdź rzeczywisty zakres, wynik i dane wykonawcy.'))return;
            const record={...old};
            for(const key of ['panelId','type','date','technician','recipient','scope','faultId','result','desc','recom','parts'])record[key]=values[key];
            record.date=record.date.replace('T',' ');record.contractor=record.technician;record.hours=Number(values.hours||0);record.closeFault=values.closeFault==='on';record.protocolStatus=final?'final':'draft';
            record.checklist=old.checklist.map((c,i)=>({...c,result:values['check-'+i],note:values['note-'+i]}));
            if(record.faultId&&db.faults.find(f=>f.id===record.faultId)?.panelId!==record.panelId)throw new Error('Wybrane zgłoszenie dotyczy innej centrali.');
            const index=candidate.history.findIndex(h=>h.id===record.id);if(index<0)candidate.history.push(record);else candidate.history[index]=record;
        }
        busy=true;form.querySelectorAll('button,input,select,textarea').forEach(b=>b.disabled=true);
        if(kind==='settings') {
            const updated={...service,...values,inspectionMonths:Number(values.inspectionMonths),reminderDays:Number(values.reminderDays),technicians:values.technicians.split('\n').map(s=>s.trim()).filter(Boolean),checklist:values.checklist.split('\n').map(s=>s.trim()).filter(Boolean)};
            const result=await api('/api/config','PUT',{revision:configRevision,service:updated});service=result.service;configRevision=result.revision;
        } else await persist(candidate);
        busy=false;closeModal(true);render();notice(kind==='protocol'&&event.submitter?.value==='final'?'Protokół zatwierdzony. Dokument jest dostępny w historii.':'Zapisano zmiany na dysku.');
    } catch(e) { $('form-error').textContent=e.message; }
    finally {busy=false;form.querySelectorAll('button,input,select,textarea').forEach(b=>b.disabled=false);}
}
function download(data,filename) {
    const blob=new Blob([typeof data==='string'?data:JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function importFile(file) {
    if(!file)return;
    if(file.size>20*1024*1024)throw new Error('Limit importu wynosi 20 MB.');
    const bytes=new Uint8Array(await file.arrayBuffer());
    const encoding=bytes[0]===255&&bytes[1]===254?'utf-16le':bytes[0]===254&&bytes[1]===255?'utf-16be':'utf-8';
    const imported=JSON.parse(new TextDecoder(encoding).decode(bytes));
    if(!['panels','faults','history'].every(k=>Array.isArray(imported[k])))throw new Error('Plik nie jest bazą SSP.');
    if(!confirm(`Zastąpić całą obecną bazę? Import: ${imported.panels.length} central, ${imported.faults.length} zgłoszeń, ${imported.history.length} wpisów. Przed importem powstanie kopia obecnej bazy.`))return;
    await persist(imported,'replace');render();notice('Baza zaimportowana. Dotychczasowe dane zachowano w kopii zapasowej.');
}
async function action(event) {
    const target=event.target.closest('[data-action]');if(!target||busy)return;
    const {action,id}=target.dataset;
    try {
        if(action==='navigate')return navigate(id);
        if(action==='new-panel'||action==='edit-panel')return openPanel(id);
        if(action==='panel-card'){route='panels';selectedPanel=id;return render();}
        if(action==='new-fault')return openFault('',id);
        if(action==='edit-fault')return openFault(id);
        if(action==='new-inspection')return openProtocol('',id,'',true);
        if(action==='new-protocol')return openProtocol('',id);
        if(action==='service-fault')return openProtocol('','',id);
        if(action==='followup-protocol')return openProtocol('','','',false,id);
        if(action==='edit-protocol')return openProtocol(id);
        if(action==='delete-draft') {
            const h=db.history.find(h=>h.id===id);
            if(!h||h.protocolStatus!=='draft')throw new Error('Można usunąć wyłącznie szkic.');
            if(!confirm('Usunąć niezatwierdzony szkic? Poprzednia wersja bazy pozostanie w kopii.'))return;
            busy=true;const candidate=clone(db);candidate.history=candidate.history.filter(h=>h.id!==id);
            await persist(candidate);selectedProtocol='';render();notice('Usunięto szkic.');
        }
        if(action==='view-protocol'){route='protocols';selectedProtocol=id;return render();}
        if(action==='print-protocol'){const h=db.history.find(h=>h.id===id);$('print-area').innerHTML=documentHTML(h);return window.print();}
        if(action==='edit-settings')return modal('settings','Konfiguracja firmy i serwisu',settingsFields(service));
        if(action==='close-modal')return closeModal();
        if(action==='export')return download(db,`SSP-baza-${today()}.json`);
        if(action==='import')return $('import-file').click();
        if(action==='archive-panel') {
            const p=db.panels.find(p=>p.id===id);
            if(!p.archived&&(db.faults.some(f=>f.panelId===id&&f.status!=='Zamknięte')||db.history.some(h=>h.panelId===id&&h.protocolStatus==='draft')))throw new Error('Najpierw zamknij zgłoszenia i zakończ protokoły robocze tej centrali.');
            if(!confirm(p.archived?'Przywrócić centralę do ewidencji?':'Archiwizować centralę? Jej historia pozostanie dostępna.'))return;
            busy=true;const candidate=clone(db);candidate.panels.find(p=>p.id===id).archived=!p.archived;await persist(candidate);render();notice('Zmieniono status ewidencji.');
        }
        if(action==='backup'){busy=true;const result=await api('/api/backup','POST');if(route==='backups')render();notice(result.name?'Utworzono kopię: '+result.name:'Baza jest pusta i nie ma jeszcze pliku do skopiowania.');}
        if(action==='download-backup'){
            busy=true;const response=await fetch('/api/backups/'+encodeURIComponent(id),{headers:{'X-SSP-Client':'local'},signal:AbortSignal.timeout(20000)});
            if(!response.ok)throw new Error('Nie można pobrać kopii.');
            const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=id;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        }
    } catch(e){notice(e.message,true);} finally {busy=false;}
}
document.addEventListener('click',action);
$('editor-form').addEventListener('submit',saveEditor);
$('editor-form').addEventListener('input',()=>dirty=true);
$('editor-form').addEventListener('change',()=>dirty=true);
$('editor').addEventListener('cancel',e=>{e.preventDefault();closeModal();});
window.addEventListener('beforeunload',e=>{if(dirty||busy){e.preventDefault();e.returnValue='';}});
$('content').addEventListener('input',event=>{
    const id=event.target.id;if(id!=='search')return;
    const position=event.target.selectionStart;filters.search=event.target.value;render();$('search').focus();$('search').setSelectionRange(position,position);
});
$('content').addEventListener('change',event=>{const id=event.target.id;if(id==='filter')filters.status=event.target.value;else if(id==='date-from')filters.from=event.target.value;else if(id==='date-to')filters.to=event.target.value;else return;render();});
$('import-file').addEventListener('change',async event=>{try{if(busy)return;busy=true;await importFile(event.target.files[0]);}catch(e){notice('Import nie powiódł się: '+e.message,true);}finally{busy=false;event.target.value='';}});
async function init() {
    try {
        const [data,config]=await Promise.all([api('/api/database'),api('/api/config')]);
        db=data.database||{panels:[],faults:[],history:[],schemaVersion:2,audit:[]};dbRevision=data.revision;
        service=config.service;configRevision=config.revision;version=config.version;databaseName=config.database;
        render();$('storage-status').textContent=`SSP Polon ${version} · ${databaseName} · ${dbRevision?'Baza odczytana':'Nowa, pusta baza — dodaj centralę lub użyj importu'} · Offline`;
    } catch(e) { $('content').innerHTML=heading('Nie można otworzyć aplikacji','Uruchom program przez Uruchom.bat i sprawdź pliki danych.')+`<div class="error">${esc(e.message)}</div><p>Uszkodzona baza nie zostanie automatycznie zastąpiona. Zachowaj ją przed przywróceniem kopii.</p>`; }
}
init();
