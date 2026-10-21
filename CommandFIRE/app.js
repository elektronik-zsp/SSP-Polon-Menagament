'use strict';
const $ = (id) => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => structuredClone(value);
const uid = prefix => prefix + '-' + crypto.randomUUID();
const routes = [['dashboard','Pulpit serwisowy'],['search','Szukaj w systemie'],['panels','Centrale i harmonogram'],['schedule','Plan przeglądów'],['faults','Zgłoszenia serwisowe'],['protocols','Protokoły i historia'],['reports','Raporty i koszty'],['settings','Konfiguracja'],['backups','Baza danych'],['audit','Rejestr zmian'],['users','Użytkownicy']];
let searchReturnState=null;
let db, dbRevision, service, configRevision, version, databaseName;
let authToken=sessionStorage.getItem('ssp-auth')||'', currentUser=null, accountUsers=[], availablePermissions={}, roleDefaults={};
const routePermission={dashboard:'dashboard.view',panels:'panels.view',schedule:'panels.view',faults:'faults.view',protocols:'protocols.view',reports:'protocols.view',settings:'settings.view',backups:'backups.view',audit:'audit.view',users:'users.manage'};
const canRoute=id=>id==='search'?['panels.view','faults.view','protocols.view'].some(can):can(routePermission[id]);
const actionPermission={'new-element':'panels.edit','edit-element':'panels.edit','archive-element':'panels.edit','link-similar':'faults.edit','open-similar':'faults.view','panel-card':'panels.view','view-fault':'faults.view','view-protocol':'protocols.view','new-cost':'protocols.edit','reverse-cost':'protocols.edit','print-monthly':'protocols.view','monthly-csv':'protocols.view','costs-csv':'protocols.view','plan-inspection':'panels.edit','print-schedule':'panels.view','new-panel':'panels.edit','edit-panel':'panels.edit','archive-panel':'panels.edit',
 'new-fault':'faults.edit','edit-fault':'faults.edit','log-fault':'faults.edit','new-inspection':'protocols.edit',
 'new-protocol':'protocols.edit','service-fault':'protocols.edit','followup-protocol':'protocols.edit',
 'edit-protocol':'protocols.edit','delete-draft':'protocols.edit','edit-settings':'settings.edit',
 'import':'backups.manage','backup':'backups.manage','export':'backups.manage',
 'edit-user':'users.manage','new-user':'users.manage','reset-user':'users.manage', 'download-backup':'backups.manage','fault-from-check':'faults.edit','document-download':'panels.view','print-panel':'panels.view','print-fault':'faults.view','report-csv':'protocols.view','print-report':'protocols.view'};
const can=(permission)=>Boolean(currentUser?.permissions?.includes(permission));
function showAuth(message='',change=false) {
 searchReturnState=null;viewPreferences=Object.create(null);tableSortState.clear();filters={};
 // Hide notifications from the previous account when login is required.
 stopSynchronization();
 $('sync-feed').hidden=true;$('sync-alert-button').setAttribute('aria-expanded','false');
 $('sync-toast-stack').innerHTML='';syncAlerts=[];unseenAlerts=0;$('sync-count').hidden=true;
 if($('editor').open){$('editor').close();editor=null;dirty=false;activeLock='';}
 document.body.classList.add('login-mode');$('auth-gate').hidden=false;
 $('auth-title').textContent=change?'Wymagana zmiana hasła':'Zaloguj się do CommandFIRE SSP Serwis';
 $('auth-login-fields').hidden=change;$('auth-change-fields').hidden=!change;
 document.querySelectorAll('#auth-login-fields input').forEach(input=>{input.disabled=change;});
 document.querySelectorAll('#auth-change-fields input').forEach(input=>{input.disabled=!change;});
 $('auth-error').textContent=message;$('auth-password').value='';
 if(change){$('auth-old').value='';$('auth-new').value='';$('auth-repeat').value='';}
}
function showApplication() {
 document.body.classList.remove('login-mode');$('auth-gate').hidden=true;
 const person=(currentUser?.displayName||currentUser?.username||'Użytkownik').trim();
 const roleLabels={ADMIN:'Administrator',SERWISANT:'Serwisant',DYSPOZYTOR:'Dyspozytor',ODCZYT:'Tylko odczyt'};
 const role=roleLabels[currentUser?.role]||currentUser?.role||'Użytkownik';
 $('user-label').textContent=person;
 $('user-role').textContent=role;
 $('user-avatar').textContent=person.split(/\s+/).slice(0,2).map(s=>Array.from(s)[0]||'').join('').toLocaleUpperCase('pl-PL')||'U';
 $('session-user').dataset.role=currentUser?.role||'';
 $('session-user').title=`Zalogowany: ${person} (${role})${currentUser?.username?' · login: '+currentUser.username:''}`;
}
async function authenticateUser(event) {
 event.preventDefault();const form=event.currentTarget, change=!$('auth-change-fields').hidden;
 $('auth-error').textContent='';const submit=form.querySelector('[type=submit]');submit.disabled=true;
 try {
   if(change){const newPassword=$('auth-new').value;if(newPassword!==$('auth-repeat').value)throw new Error('Nowe hasła muszą być identyczne.');
     await api('/api/auth/change-password','POST',{oldPassword:$('auth-old').value,newPassword});
     authToken='';sessionStorage.removeItem('ssp-auth');currentUser=null;showAuth('Hasło zmieniono. Zaloguj się ponownie.');return;
   }
   const result=await api('/api/auth/login','POST',{username:$('auth-username').value.trim(),password:$('auth-password').value});
   authToken=result.token;sessionStorage.setItem('ssp-auth',authToken);currentUser=result.user;
   availablePermissions=result.permissions;roleDefaults=result.roles;
   if(currentUser.mustChangePassword){showAuth('',true);return;}
   await loadApplication();
 } catch(e){$('auth-error').textContent=e.message;}
 finally{submit.disabled=false;}
}
async function logout() {
 if(dirty&&!confirm('Masz niezapisane dane. Wylogować się?'))return;
 stopSynchronization();await releaseLock();try{await api('/api/auth/logout','POST',{});}catch(e){}
 authToken='';sessionStorage.removeItem('ssp-auth');currentUser=null;searchReturnState=null;
 if($('editor').open)$('editor').close();editor=null;dirty=false;
 db=null;route='dashboard';showAuth();
}

let route = 'dashboard', selectedPanel = '', selectedProtocol = '', selectedFault = '', filters = {}, busy = false, editor = null, dirty = false;
const lockToken = crypto.randomUUID();
let activeLock = '', lastUserAction = 0, lockReleaseTask = Promise.resolve();

// 2.5.3 — synchronizacja pomiędzy lokalnymi stanowiskami przez wspólny plik.
// Polling metadata is not an editor action. It never calls /api/lock touch.
const SYNC_INTERVAL_MS = 5000;
let syncTimer = null, syncInFlight = false, syncPending = false, syncOnline = true;
let syncGeneration = 0, lastLockSignature = '', syncAlerts = [], unseenAlerts = 0;
function setSyncStatus(message, state='ok') {
    const el=$('sync-indicator');
    if(!el)return;
    $('sync-status-text').textContent=message;
    el.dataset.state=state;
    el.title=state==='ok'?'Połączenie ze wspólną bazą działa. Dane aktualizują się automatycznie.':
       state==='error'?'Brak połączenia ze wspólną bazą. Sprawdź dostęp do dysku sieciowego.':
       'Sprawdzanie synchronizacji lub oczekiwanie na koniec edycji.';
}
function startSynchronization() {
    stopSynchronization();
    syncOnline=true;syncPending=false;lastLockSignature=JSON.stringify(db?.activeSessions||{});
    setSyncStatus('Sprawdzanie…','pending');
    void pollSynchronization();
    syncTimer=setInterval(()=>{void pollSynchronization();},SYNC_INTERVAL_MS);
}
function stopSynchronization() {
    if(syncTimer!==null){clearInterval(syncTimer);syncTimer=null;}
    syncPending=false; syncGeneration++;
}
function showSyncAlert(message) {
    const entry={id:crypto.randomUUID(),text:message,at:new Date().toLocaleTimeString('pl-PL')};
    syncAlerts.unshift(entry);syncAlerts=syncAlerts.slice(0,20);
    unseenAlerts=Math.min(99,unseenAlerts+1);
    const count=$('sync-count');count.hidden=false;count.textContent=String(unseenAlerts);
    renderSyncFeed();
    const toast=document.createElement('div');toast.className='sync-toast';
    toast.textContent=message;$('sync-toast-stack').prepend(toast);
    while($('sync-toast-stack').children.length>3)$('sync-toast-stack').lastElementChild.remove();
    setTimeout(()=>toast.remove(),8000);
}
function renderSyncFeed() {
    const feed=$('sync-feed');if(!feed||feed.hidden)return;
    feed.innerHTML='<strong>Ostatnie powiadomienia</strong>'+(
        syncAlerts.length?syncAlerts.map(a=>`<p><span>${esc(a.at)}</span> ${esc(a.text)}</p>`).join(''):
        '<p>Nie ma jeszcze nowych powiadomień w tej sesji.</p>');
}
function toggleSyncFeed() {
    const feed=$('sync-feed');feed.hidden=!feed.hidden;
    $('sync-alert-button').setAttribute('aria-expanded',String(!feed.hidden));
    if(!feed.hidden){unseenAlerts=0;$('sync-count').hidden=true;renderSyncFeed();}
}
function incomingAlerts(previous,next) {
    if(!previous||!next)return;
    const oldFaults=new Map((previous.faults||[]).map(f=>[f.id,f]));
    const oldPanels=new Map((previous.panels||[]).map(p=>[p.id,p]));
    const oldProtocols=new Map((previous.history||[]).map(h=>[h.id,h]));
    const messages=[];
    for(const f of next.faults||[]) {
        const before=oldFaults.get(f.id);
        if(!before)messages.push(`Nowe zgłoszenie ${faultNumber(f)} · ${f.panelId}`);
        else {
            if(before.status!==f.status)messages.push(`Zgłoszenie ${faultNumber(f)}: ${before.status} → ${f.status}`);
            if((f.timeline||[]).length>(before.timeline||[]).length)messages.push(`Nowy wpis w historii zgłoszenia ${faultNumber(f)}`);
        }
    }
    for(const p of next.panels||[]) {
        const before=oldPanels.get(p.id);
        if(!before)messages.push(`Dodano centralę ${p.id} · ${p.location}`);
        else if(before.condition!==p.condition)messages.push(`Centrala ${p.id}: stan ${p.condition}`);
    }
    for(const h of next.history||[]) {
        const before=oldProtocols.get(h.id);
        if(h.protocolStatus==='final'&&before?.protocolStatus!=='final')
            messages.push(`Zatwierdzono ${h.type==='Przegląd'?'przegląd':'protokół'} ${h.protocolNo||h.inspectionNo||h.id}`);
    }
    // Avoid flooding the operator after a large import.
    messages.slice(0,5).forEach(showSyncAlert);
    if(messages.length>5)showSyncAlert(`Pozostałe zmiany: ${messages.length-5}. Otwórz odpowiednią zakładkę.`);
}
function updateVisibleLocks(locks) {
    const signature=JSON.stringify(locks||{});
    if(lastLockSignature===signature)return;
    lastLockSignature=signature;
    if(db)db.activeSessions=locks||{};
    if(activeLock&&!locks?.[activeLock]&&editor?.kind!=='user') {
        $('form-error').textContent='Blokada edycji wygasła lub została zwolniona. Zapis może zostać odrzucony — zachowaj tekst i otwórz formularz ponownie.';
    }
    // Never replace the content being edited or a field currently receiving input.
    if(!editor?.open && !$('editor').open && !busy &&
       !['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName))render();
}
async function pollSynchronization() {
    if(syncInFlight || !currentUser || !db || !authToken)return;
    syncInFlight=true;
    const generation=syncGeneration, token=authToken;
    try {
        const meta=await api('/api/sync');
        if(generation!==syncGeneration||token!==authToken||!currentUser)return;
        if(!syncOnline){syncOnline=true;showSyncAlert('Przywrócono połączenie ze wspólną bazą.');}
        updateVisibleLocks(meta.locks);
        if(meta.revision!==dbRevision||meta.configRevision!==configRevision||syncPending) {
            if($('editor').open||busy||activeLock){
                syncPending=true;
                setSyncStatus('Zmiany oczekują','pending');
                return;
            }
            const previous=db;
            const epoch=syncGeneration;
            const [incoming,settings]=await Promise.all([api('/api/database'),api('/api/config')]);
            if(epoch!==syncGeneration||token!==authToken||!currentUser)return;
            if($('editor').open||busy||activeLock){syncPending=true;return;}
            // In case an own save/load won the race, don't restore an older snapshot.
            if(db!==previous){syncPending=true;return;}
            incomingAlerts(previous,incoming.database);
            db=incoming.database;dbRevision=incoming.revision;
            service=settings.service;configRevision=settings.revision;
            version=settings.version;databaseName=settings.database;
            syncPending=false;syncGeneration++;
            render();
            $('storage-status').textContent=`CommandFIRE SSP Serwis ${version} · ${databaseName} · Automatycznie zsynchronizowano ${new Date().toLocaleTimeString('pl-PL')}`;
        }
        if(!syncPending)setSyncStatus('Połączenie OK');
    } catch(e) {
        if(generation!==syncGeneration||token!==authToken)return;
        if(!currentUser)return; // auth error has already displayed the login screen.
        syncOnline=false;setSyncStatus('Brak połączenia','error');
        // Never fall back to a local database; a write will still be checked server-side.
    } finally {syncInFlight=false;}
}


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
const faultIsActive = f => !['Zakończone','Anulowane'].includes(f.status);
const faultTone = status => status==='Zakończone'?'green':status==='Anulowane'?'':status==='W realizacji'?'blue':'amber';
const faultStatuses = ['Nowe','W realizacji','Zakończone','Anulowane'];
const badge = (label,tone='') => `<span class="badge ${esc(tone)}">${esc(label)}</span>`;
const button = (label,action,id='',className='') => (actionPermission[action]&&!can(actionPermission[action]))?'':`<button type="button" class="${esc(className)}" data-action="${esc(action)}" data-id="${esc(id)}">${esc(label)}</button>`;
const panelName = id => { const p = db.panels.find(p=>p.id===id); return p ? `${p.id} · ${p.location}` : id+' (brak w ewidencji)'; };
function heading(title,subtitle,actions='') { return `<div class="page-heading"><div><h1>${esc(title)}</h1><p class="lead">${esc(subtitle)}</p></div><div class="actions">${actions}</div></div>`; }
const tableSortState = new Map();
const tableCollator = new Intl.Collator('pl', {numeric:true, sensitivity:'base'});
function sortTableElement(element, column, direction) {
    const body=element.tBodies[0];
    const rows=Array.from(body.rows).filter(row=>!row.querySelector('td.empty'));
    const value=row=>{
        const cell=row.cells[column];
        return (cell?.dataset.sortValue ?? cell?.innerText ?? cell?.textContent ?? '').trim();
    };
    rows.sort((a,b)=>{
        const x=value(a),y=value(b);
        // Missing values remain at the bottom in either direction.
        const missing=v=>!v||v==='—'||v==='Nie przypisano';
        if(missing(x)!==missing(y))return missing(x)?1:-1;
        return tableCollator.compare(x,y)*(direction==='ascending'?1:-1);
    });
    rows.forEach(row=>body.appendChild(row));
    element.querySelectorAll('thead th').forEach((th,i)=>{
        const button=th.querySelector('[data-action="sort-table"]');
        if(!button)return;
        th.setAttribute('aria-sort',i===column?direction:'none');
        button.querySelector('.sort-indicator').textContent=i===column?(direction==='ascending'?'▲':'▼'):'↕';
    });
}
function table(headers,rows,empty='Brak danych do wyświetlenia.') {
    const key=JSON.stringify([route,selectedPanel,selectedFault,headers]);
    const template=document.createElement('template');
    template.innerHTML=`<div class="table-wrap"><table data-sort-key="${esc(key)}"><thead><tr>${headers.map((h,i)=>h&&h!=='Operacje'?`<th scope="col" aria-sort="none"><button type="button" class="table-sort" data-action="sort-table" data-column="${i}" title="Sortuj: ${esc(h)}">${esc(h)} <span class="sort-indicator" aria-hidden="true">↕</span></button></th>`:`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}" class="empty">${esc(empty)}</td></tr>`}</tbody></table></div>`;
    const state=tableSortState.get(key);
    if(state)sortTableElement(template.content.querySelector('table'),state.column,state.direction);
    return template.innerHTML;
}
function field(name,label,value='',type='text',extra='',full=false) { return `<div class="field ${full?'full':''}"><label for="f-${esc(name)}">${esc(label)}</label>${type==='textarea'?`<textarea id="f-${esc(name)}" name="${esc(name)}" ${extra}>${esc(value)}</textarea>`:`<input id="f-${esc(name)}" name="${esc(name)}" type="${type}" value="${esc(value)}" ${extra}>`}</div>`; }
function options(values,value) { return values.map(v=>{ const [id,label]=Array.isArray(v)?v:[v,v]; return `<option value="${esc(id)}" ${id===value?'selected':''}>${esc(label)}</option>`; }).join(''); }
function select(name,label,values,value='',extra='') { return `<div class="field"><label for="f-${esc(name)}">${esc(label)}</label><select id="f-${esc(name)}" name="${esc(name)}" ${extra}>${options(values,value)}</select></div>`; }
function details(values) { return `<dl class="detail-list">${values.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v||'—')}</dd>`).join('')}</dl>`; }
function toolbar(statuses,placeholder='Szukaj…') { return `<div class="toolbar"><input id="search" aria-label="Szukaj" placeholder="${esc(placeholder)}" value="${esc(filters.search||'')}"><select id="filter" aria-label="Filtr">${options([['','Wszystkie'],...statuses],filters.status||'')}</select></div>`; }
function matches(record) { return !filters.search || JSON.stringify({...record,documents:(record.documents||[]).map(d=>({name:d.name}))}).toLocaleLowerCase('pl').includes(filters.search.toLocaleLowerCase('pl')); }
function notice(message,error=false) { $('notification').innerHTML = `<div class="${error?'error':'notice'}">${esc(message)}</div>`; }
async function api(path, method='GET', data) {
    let response;
    try { response = await fetch(path, {method, headers:{'X-SSP-Client':'local',...(authToken?{'X-SSP-Session':authToken}:{}),...(data===undefined?{}:{'Content-Type':'application/json'})}, body:data===undefined?undefined:JSON.stringify(data), signal:AbortSignal.timeout(20000)}); }
    catch(e) { throw new Error('Brak połączenia z lokalnym serwerem. Sprawdź okno Uruchom.bat. Formularz pozostaje otwarty.'); }
    let result;
    try { result=await response.json(); } catch(e) { throw new Error('Nieprawidłowa odpowiedź serwera.'); }
    if (!response.ok) {if(response.status===401 && authToken && path!=='/api/auth/login'){stopSynchronization();authToken='';sessionStorage.removeItem('ssp-auth');currentUser=null;showAuth('Sesja wygasła. Zaloguj się ponownie.');}throw new Error(result.error || 'Nie udało się wykonać operacji.');}
    return result;
}
async function persist(candidate,mode) {
    const result=await api('/api/database','PUT',{revision:dbRevision,base:db,database:candidate,token:lockToken,...(mode?{mode}:{})});
    db=result.database; dbRevision=result.revision;syncGeneration++;
    $('storage-status').textContent=`CommandFIRE SSP Serwis ${version} · ${databaseName} · Zapisano ${new Date().toLocaleTimeString('pl-PL')} · Baza współdzielona`;
}
async function refreshDatabase() {
    if($('editor').open)throw new Error('Najpierw zamknij formularz, aby nie utracić niezapisanych danych.');
    const [response, settings] = await Promise.all([api('/api/database'),api('/api/config')]);
    db=response.database;dbRevision=response.revision;
    service=settings.service;configRevision=settings.revision;version=settings.version;databaseName=settings.database;
    syncGeneration++;syncPending=false;
}
async function acquireLock(resource) {
    await lockReleaseTask;
    if (activeLock) throw new Error('Najpierw zamknij poprzedni formularz.');
    const result=await api('/api/lock','POST',{action:'claim',resource,token:lockToken});
    activeLock=resource;lastUserAction=Date.now();
    try {await refreshDatabase();} catch(e) {await releaseLock();throw e;}
    return result;
}
async function releaseLock() {
    if (!activeLock) return lockReleaseTask;
    const resource=activeLock;activeLock='';
    lockReleaseTask=lockReleaseTask.then(async()=>{
        try { await api('/api/lock','POST',{action:'release',resource,token:lockToken}); }
        catch(e) { notice('Nie udało się zwolnić blokady. Wygaśnie po 30 minutach: '+e.message,true); }
    });
    return lockReleaseTask;
}
async function lockedEditor(resource, fn) {
    await acquireLock(resource);
    try {fn();} catch(e) {await releaseLock();throw e;}
}
function lockLabel(resource) {
    const item=db?.activeSessions?.[resource];
    return item ? `Edytuje: ${item.owner}` : '';
}
async function touchLock() {
    if(!activeLock || Date.now()-lastUserAction<45000)return;
    lastUserAction=Date.now();
    try {await api('/api/lock','POST',{action:'touch',resource:activeLock,token:lockToken});}
    catch(e) {if($('editor')?.open)$('form-error').textContent=e.message;}
}
function renderNav() { $('navigation').innerHTML=routes.filter(([id])=>canRoute(id)).map(([id,label])=>`<button data-action="navigate" data-id="${id}" class="${route===id?'active':''}" ${route===id?'aria-current="page"':''}>${esc(label)}</button>`).join(''); }
const rememberedRoutes=new Set(['panels','schedule','faults','protocols','reports']);
const preferenceFields=new Set(['search','status','from','to','month','panel','plan','attention','stage','assignee']);
let viewPreferences=Object.create(null),preferencesSessionOnly=false;
function preferenceStorageKey(){return currentUser?.id&&databaseName?'commandfire-views-v1:'+currentUser.id+':'+databaseName:'';}
function defaultViewFilters(id){return id==='reports'?{month:today().slice(0,7)}:{};}
function saveViewPreferences(){
    const key=preferenceStorageKey();if(!key)return;
    const sorts=[...tableSortState].filter(([key])=>{try{return rememberedRoutes.has(JSON.parse(key)[0]);}catch{return false;}}).slice(-100);
    try{localStorage.setItem(key,JSON.stringify({version:1,filters:viewPreferences,sorts}));preferencesSessionOnly=false;}
    catch{preferencesSessionOnly=true;}
}
function detailViewIsOpen(){return Boolean(route==='panels'&&selectedPanel||route==='faults'&&selectedFault||route==='protocols'&&selectedProtocol);}
function rememberViewFilters(){
    if(!rememberedRoutes.has(route)||detailViewIsOpen())return;
    viewPreferences[route]=Object.fromEntries(Object.entries(filters).filter(([key,value])=>preferenceFields.has(key)&&typeof value==='string'&&value.length<=300));
    saveViewPreferences();
}
function loadViewPreferences(){
    viewPreferences=Object.create(null);tableSortState.clear();preferencesSessionOnly=false;
    const key=preferenceStorageKey();if(!key)return;
    try{
        const raw=localStorage.getItem(key);if(!raw)return;
        if(raw.length>200000)return;
        const data=JSON.parse(raw);if(data?.version!==1)return;
        for(const id of rememberedRoutes){const saved=data.filters?.[id];if(saved&&typeof saved==='object'&&!Array.isArray(saved))
            viewPreferences[id]=Object.fromEntries(Object.entries(saved).filter(([key,value])=>preferenceFields.has(key)&&typeof value==='string'&&value.length<=300));}
        if(Array.isArray(data.sorts))for(const entry of data.sorts.slice(-100)){
            if(!Array.isArray(entry)||entry.length!==2)continue;
            const [key,state]=entry;if(typeof key!=='string'||key.length>4000||!state)continue;
            let parsed;try{parsed=JSON.parse(key);}catch{continue;}
            if(!Array.isArray(parsed)||parsed.length!==4||!rememberedRoutes.has(parsed[0])||!Array.isArray(parsed[3]))continue;
            if(!Number.isInteger(state.column)||state.column<0||state.column>=parsed[3].length||!['ascending','descending'].includes(state.direction))continue;
            tableSortState.set(key,{column:state.column,direction:state.direction});
        }
    }catch{preferencesSessionOnly=true;}
}
function restoredViewFilters(id){return Object.hasOwn(viewPreferences,id)?clone(viewPreferences[id]):defaultViewFilters(id);}
function resetCurrentView(){
    if(!rememberedRoutes.has(route))return;
    delete viewPreferences[route];filters=defaultViewFilters(route);
    for(const key of tableSortState.keys())try{if(JSON.parse(key)[0]===route)tableSortState.delete(key);}catch{tableSortState.delete(key);}
    saveViewPreferences();render();
}
function addViewResetControl(){
    if(!rememberedRoutes.has(route)||detailViewIsOpen())return;
    const note=preferencesSessionOnly?'Ustawienia są zachowane tylko w bieżącej sesji przeglądarki.':'Filtry i sortowanie są zapamiętywane na tym komputerze, osobno dla konta i bazy.';
    const control=button('Resetuj widok','reset-view','','small').replace('<button ','<button title="'+esc(note+' Przywróć domyślne filtry i sortowanie tej zakładki.')+'" ');
    $('content').innerHTML=$('content').innerHTML.replace('<div class="toolbar">','<div class="toolbar">'+control);
}

function navigate(target) { if(!canRoute(target))return;rememberViewFilters();searchReturnState=null; route=target; filters=rememberedRoutes.has(target)?restoredViewFilters(target):{}; selectedPanel='';selectedProtocol='';selectedFault=''; render(); }
function render() {
    renderNav();
    $('site-label').textContent=service.site || 'Obsługa i utrzymanie systemów sygnalizacji pożarowej';
    if(!canRoute(route))route=routes.find(([key])=>canRoute(key))?.[0]||'dashboard';
    const views={dashboard:renderDashboard,search:renderGlobalSearch,panels:renderPanels,schedule:renderSchedule,faults:renderFaults,protocols:renderProtocols,reports:renderReports,settings:renderSettings,backups:renderBackups,audit:renderAudit,users:renderUsers};
    views[route]();
    addViewResetControl();
    if(searchReturnState&&(selectedPanel||selectedFault||selectedProtocol))$('content').innerHTML='<div class="search-return">'+button('← Wróć do wyników wyszukiwania','search-back')+'</div>'+$('content').innerHTML;
}
function faultNumber(f) { return f?.number || f?.id || '—'; }
function numberRule(kind) {
    const defaults={fault:{prefix:'ZG',start:1,digits:4,annual:true},inspection:{prefix:'PRZ',start:1,digits:4,annual:true},protocol:{prefix:service.protocolPrefix||'SSP',start:1,digits:4,annual:true}};
    return {...defaults[kind],...(service.numbering?.[kind]||{})};
}
function exampleNumber(kind) {
    const r=numberRule(kind);
    return `${r.prefix}/${r.annual?today().slice(0,4)+'/':''}${String(r.start).padStart(r.digits,'0')}`;
}
function barChart(items) {
    const max=Math.max(1,...items.map(i=>i.value));
    return `<div class="bar-chart">${items.map(i=>`<div class="bar-row"><div class="bar-caption">${esc(i.label)}</div><div class="bar-track"><div class="bar-fill ${esc(i.tone||'blue')}" style="width:${Math.max(0,Math.min(100,100*i.value/max))}%"></div></div><strong>${Number(i.value)}</strong></div>`).join('')}</div>`;
}
function monthlyChart() {
    const months=Array.from({length:6},(_,i)=>{
        const d=new Date();d.setDate(1);d.setMonth(d.getMonth()-5+i);
        return {key:`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`,label:d.toLocaleDateString('pl-PL',{month:'short'}),faults:0,protocols:0};
    });
    for(const f of db.faults) {const m=months.find(m=>m.key===String(f.date||'').slice(0,7));if(m)m.faults++;}
    for(const h of db.history) {const m=months.find(m=>m.key===String(h.date||'').slice(0,7));if(m&&h.protocolStatus==='final')m.protocols++;}
    const high=Math.max(1,...months.flatMap(m=>[m.faults,m.protocols]));
    return `<div class="chart-legend"><span class="legend-dot red"></span> Zgłoszenia <span class="legend-dot blue"></span> Zatwierdzone protokoły</div><div class="month-chart">${months.map(m=>`<div class="month-group"><div class="month-bars"><div class="month-bar red" style="height:${100*m.faults/high}%" title="${esc(m.key)}: ${m.faults} zgłoszeń"><small>${m.faults||''}</small></div><div class="month-bar blue" style="height:${100*m.protocols/high}%" title="${esc(m.key)}: ${m.protocols} protokołów"><small>${m.protocols||''}</small></div></div><span>${esc(m.label)}</span></div>`).join('')}</div><p class="hint">Liczba zgłoszeń i zatwierdzonych protokołów według daty w dokumentach — ostatnie sześć miesięcy.</p>`;
}
function renderDashboard() {
    const panels=db.panels.filter(p=>!p.archived);
    const open=db.faults.filter(faultIsActive);
    const drafts=db.history.filter(h=>h.protocolStatus==='draft');
    const overdue=open.filter(f=>f.dueDate&&daysUntil(f.dueDate)<0);
    const inspectionLate=panels.filter(p=>due(p).label==='Po terminie');
    const inspectionSoon=panels.filter(p=>due(p).label==='Zbliża się');
    const attention=panels.map(p=>{
        const related=open.filter(f=>f.panelId===p.id), reasons=[], d=due(p);
        if(['Wymaga serwisu','W trakcie naprawy','Wyłączona'].includes(p.condition))reasons.push(p.condition);
        else if(p.condition==='Niezweryfikowana')reasons.push('Stan niezweryfikowany');
        if(d.label==='Po terminie')reasons.push('Zaległy przegląd');
        if(d.label==='Brak przeglądu')reasons.push('Brak daty przeglądu');
        if(d.label==='Zbliża się')reasons.push('Przegląd wkrótce');
        if(related.length)reasons.push(related.length+' aktywne zgłosz.');
        const urgent=related.some(f=>f.priority==='Krytyczny'||f.dueDate&&daysUntil(f.dueDate)<0)||d.label==='Po terminie'||['Wymaga serwisu','Wyłączona'].includes(p.condition);
        return {panel:p,related,reasons,d,urgent,sort:(urgent?0:1)*100000+(d.rank||0)};
    }).filter(x=>x.reasons.length).sort((a,b)=>a.sort-b.sort);
    const stats=[['Centrale w ewidencji',panels.length,''],['Wymagają uwagi',attention.length,'red'],['Otwarte zgłoszenia',open.length,'amber'],['Przeglądy po terminie',inspectionLate.length,'red'],['Przeglądy wkrótce',inspectionSoon.length,'amber'],['Protokoły robocze',drafts.length,'blue']];
    const activeStatuses=faultStatuses.map((status,i)=>({label:status,value:db.faults.filter(f=>f.status===status).length,tone:['amber','blue','green','gray'][i]}));
    const inspectionStatuses=[{label:'Po terminie',value:inspectionLate.length,tone:'red'}, {label:'Zbliża się',value:inspectionSoon.length,tone:'amber'}, {label:'W terminie',value:panels.filter(p=>due(p).label==='W terminie').length,tone:'green'}, {label:'Brak daty',value:panels.filter(p=>!nextDate(p)).length,tone:'gray'}];
    const listed=open.slice().sort((a,b)=>Number(b.priority==='Krytyczny')-Number(a.priority==='Krytyczny') || Number(b.dueDate&&daysUntil(b.dueDate)<0)-Number(a.dueDate&&daysUntil(a.dueDate)<0) || priorityRank(b)-priorityRank(a)).slice(0,12);
    $('content').innerHTML=heading('Pulpit serwisowy',`Stan systemów SSP · ${new Date().toLocaleDateString('pl-PL',{day:'numeric',month:'long',year:'numeric'})}`,button('Odśwież dane','refresh')+button('Nowe zgłoszenie','new-fault','','primary'))+
      `<div class="cards cards-six">${stats.map(([label,count,tone])=>`<div class="card"><div class="card-label">${esc(label)}</div><div class="metric ${esc(tone)}">${count}</div></div>`).join('')}</div>`+
      (overdue.length?`<div class="notice warning"><strong>${overdue.length} zgłoszeń po terminie realizacji.</strong> Otwórz zgłoszenia i zaplanuj działania.</div>`:'')+
      `<section class="panel dashboard-priority"><div class="section-row"><div><h2>Centrale i obiekty wymagające interwencji lub uwagi</h2><p class="hint">Uwzględniono stan techniczny, terminy przeglądów i otwarte zgłoszenia.</p></div>${button('Cała ewidencja','navigate','panels','small')}</div>`+
      table(['Centrala / model','Obiekt / miejsce','Powód uwagi','Następny przegląd','Otwarte',''],attention.map(({panel:p,reasons,d,related,urgent})=>`<tr class="${urgent?'urgent-row':''}"><td>${button(p.id,'panel-card',p.id,'link')}<br><span class="muted">${esc(p.model)}</span></td><td><strong>${esc(p.location)}</strong><br><span class="muted">${esc(p.spot)}</span></td><td>${reasons.map(r=>badge(r,urgent?'red':'amber')).join(' ')}</td><td>${esc(d.date||'Nie ustalono')}<br>${badge(d.label,d.tone)}</td><td>${related.length}</td><td>${button('Szczegóły','panel-card',p.id,'small')}</td></tr>`),'Wszystkie centrale mają prawidłowe terminy i nie zgłoszono uwag.')+'</section>'+
      `<div class="grid2 dashboard-charts"><section class="panel"><h2>Struktura zgłoszeń</h2>${barChart(activeStatuses)}</section><section class="panel"><h2>Stan terminów przeglądów</h2>${barChart(inspectionStatuses)}</section></div>`+
      `<section class="panel"><h2>Aktywność serwisowa — ostatnie 6 miesięcy</h2>${monthlyChart()}</section>`+
      `<section class="panel"><div class="section-row"><h2>Zgłoszenia do obsługi</h2>${button('Wszystkie zgłoszenia','navigate','faults','small')}</div>${table(['Nr zgłoszenia','Centrala / obiekt','Opis','Zgłaszający','Priorytet','Status / termin',''],listed.map(f=>{const p=panels.find(p=>p.id===f.panelId);return `<tr><td>${button(faultNumber(f),'view-fault',f.id,'link')}</td><td>${button(f.panelId,'panel-card',f.panelId,'link')}<br><span class="muted">${esc(p?.location||'—')}</span></td><td>${esc(f.desc.slice(0,110))}</td><td>${esc(f.reporter||'—')}</td><td data-sort-value="${priorityRank(f)}">${badge(f.priority,priorityRank(f)>=2?'red':'')}</td><td>${badge(f.status,faultTone(f.status))}<br>${esc(f.dueDate||'Brak terminu')}</td><td>${button('Historia','view-fault',f.id,'small')}</td></tr>`;}),'Brak otwartych zgłoszeń.')}</section>`+
      (!panels.length?`<div class="panel"><h2>Rozpocznij od ewidencji</h2>${button('Dodaj centralę','new-panel','','primary')} ${currentUser?.role==='ADMIN'?button('Import bazy','navigate','backups'):''}</div>`:'');
}

function searchFold(value){return String(value??'').toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l');}
function systemSearch(query,kind=''){
    const text=searchFold(query).trim(),tokens=text.split(/\s+/).filter(Boolean);
    if(text.length<2)return [];
    const hits=[];
    const add=(type,row,title,panelId,date,status,fields)=>{
        if(kind&&type!==kind)return;
        const values=[title,panelId,date,status,...fields].filter(v=>v!==null&&v!==undefined).map(String);
        const folded=values.map(searchFold),haystack=folded.join(' ');
        if(!tokens.every(t=>haystack.includes(t)))return;
        const titleKey=searchFold(title);
        const score=titleKey===text?100:titleKey.startsWith(text)?70:titleKey.includes(text)?50:tokens.every(t=>titleKey.includes(t))?40:10;
        const field=values.find((v,i)=>i>=4&&tokens.some(t=>folded[i].includes(t)))||values[4]||title;
        const index=Math.max(0,searchFold(field).indexOf(tokens[0]));const start=Math.max(0,index-45);
        const excerpt=(start?'…':'')+field.slice(start,start+180)+(field.length>start+180?'…':'');
        hits.push({kind:type,id:row.id,title,panelId,date,status,excerpt,score});
    };
    if(can('panels.view'))for(const p of db.panels)add('panel',p,p.id,p.id,p.lastInspection,p.archived?'Archiwum':p.condition,
        [p.model,p.location,p.spot,p.serialNo,p.coverage,p.serviceContact,p.notes,p.inspectionPlanDate,p.inspectionPlanAssignee,p.inspectionPlanNote,...(p.documents||[]).map(d=>d.name),...(p.elements||[]).flatMap(e=>[e.address,e.type,e.location,e.notes])]);
    if(can('faults.view'))for(const f of db.faults)add('fault',f,faultNumber(f),f.panelId,f.date,f.status,
        [f.desc,f.reporter,f.assignee,f.elementAddress,f.elementType,f.elementLocation,f.priority,f.workStage,f.cause,f.resolution,f.verification,...(f.timeline||[]).flatMap(e=>[e.author,e.performedBy,e.text])]);
    if(can('protocols.view')){
        for(const h of db.history)add('protocol',h,h.protocolNo||h.inspectionNo||'Szkic / wpis historyczny',h.panelId,h.date,protocolLabel(h),
            [h.inspectionNo,h.type,h.technician,h.contractor,h.recipient,h.scope,h.desc,h.recom,h.parts,h.result,...(h.checklist||[]).flatMap(c=>[c.label,c.note])]);
        const protocols=new Map(db.history.map(h=>[h.id,h]));
        for(const c of db.costs||[]){const h=protocols.get(c.protocolId);add('cost',c,(c.reversesId?'Korekta':'Koszt')+' · '+(h?.protocolNo||'Wpis historyczny'),h?.panelId||'',c.date,c.category,[c.description,c.reference,c.createdBy,money(c.amountGrosz),h?.protocolNo]);}
    }
    return hits.sort((a,b)=>b.score-a.score||String(b.date||'').localeCompare(String(a.date||''))||a.title.localeCompare(b.title,'pl',{numeric:true}));
}
function renderGlobalSearch(){
    const query=filters.search||'',hits=systemSearch(query,filters.kind||'');
    const kinds=[['','Wszystkie rodzaje'],...(can('panels.view')?[['panel','Centrale']]:[]),...(can('faults.view')?[['fault','Zgłoszenia']]:[]),...(can('protocols.view')?[['protocol','Protokoły'],['cost','Koszty']]:[])];
    const labels={panel:'Centrala',fault:'Zgłoszenie',protocol:'Protokół',cost:'Koszt'};
    $('content').innerHTML=heading('Szukaj w systemie','Numery dokumentów, adresy elementów, opisy prac i dane zgłaszającego. Skrót: Ctrl+K.')+
      `<div class="toolbar"><input id="search" type="search" maxlength="300" aria-label="Szukaj w całym systemie" placeholder="Np. ZG/2026/0042, czujka, nazwisko…" value="${esc(query)}"><select id="search-kind" aria-label="Rodzaj wyniku">${options(kinds,filters.kind||'')}</select><span class="hint">${hits.length} wyników${hits.length>100?' · pokazano 100 najlepiej dopasowanych':''}</span></div>`+
      `<p class="hint">Wpisz co najmniej 2 znaki. Wszystkie wpisane słowa muszą wystąpić w rekordzie. Możesz pomijać polskie znaki. Przeszukujemy też historię czynności i nazwy załączników; zawartość plików nie jest przeszukiwana.</p>`+
      (query.trim().length<2?'<section class="panel"><p class="muted">Wpisz numer, opis lub nazwisko, aby rozpocząć wyszukiwanie.</p></section>':table(['Rodzaj','Numer / nazwa','Centrala','Stan / data','Dopasowany fragment',''],hits.slice(0,100).map(h=>`<tr><td>${badge(labels[h.kind])}</td><td>${button(h.title,'search-open',JSON.stringify({kind:h.kind,id:h.id}),'link')}</td><td>${esc(h.panelId)}</td><td>${esc(h.status||'—')}<br><span class="muted">${esc(h.date||'—')}</span></td><td class="search-excerpt">${esc(h.excerpt)}</td><td>${button('Otwórz','search-open',JSON.stringify({kind:h.kind,id:h.id}),'small')}</td></tr>`),'Brak wyników. Spróbuj krótszego opisu albo innego numeru.'));
}

function renderPanels() {
    if(selectedPanel) return renderPanelCard(selectedPanel);
    const rows=db.panels.filter(p=>matches(p)&&(!filters.status? !p.archived: filters.status==='Archiwum'?p.archived:!p.archived&&due(p).label===filters.status));
    $('content').innerHTML=heading('Centrale i harmonogram','Ewidencja urządzeń, stan techniczny i terminy obsługi.',button('Dodaj centralę','new-panel','','primary'))+
      toolbar(['Po terminie','Zbliża się','Brak przeglądu','W terminie','Archiwum'],'Kod, model, obiekt, numer seryjny…')+
      table(['Centrala','Lokalizacja','Stan techniczny','Ostatni przegląd','Następny termin',''],rows.map(p=>`<tr><td>${button(p.id,'panel-card',p.id,'link')}<br>${esc(p.model)}</td><td>${esc(p.location)}<br><span class="muted">${esc(p.spot)}</span></td><td>${badge(p.archived?'Archiwum':p.condition,p.condition==='Wymaga serwisu'?'red':'')}</td><td>${esc(p.lastInspection||'—')}</td><td>${esc(nextDate(p)||'—')}<br>${badge(due(p).label,due(p).tone)}</td><td><div class="actions">${button('Edytuj','edit-panel',p.id,'small')}${!p.archived?button('Przegląd','new-inspection',p.id,'small'):''}</div></td></tr>`));
}
function scheduleRows() {
    return db.panels.filter(p=>!p.archived && matches(p)
        && (!filters.month || (p.inspectionPlanDate||nextDate(p)||'').slice(0,7)===filters.month)
        && (!filters.plan || (filters.plan==='unplanned'?!p.inspectionPlanDate:
            filters.plan==='late'?Boolean(p.inspectionPlanDate&&p.inspectionPlanDate<today()):
            filters.plan==='overdue'?due(p).label==='Po terminie':Boolean(p.inspectionPlanDate))))
        .sort((a,b)=>(a.inspectionPlanDate||nextDate(a)||'9999').localeCompare(b.inspectionPlanDate||nextDate(b)||'9999')||a.id.localeCompare(b.id));
}
function scheduleTable(rows,printing=false) {
    return table(['Centrala / obiekt','Termin z interwału','Uzgodniona wizyta','Wykonawca','Uwagi',''],rows.map(p=>{
        const late=p.inspectionPlanDate&&nextDate(p)&&p.inspectionPlanDate>nextDate(p);
        return `<tr><td>${printing?esc(p.id):button(p.id,'panel-card',p.id,'link')}<br>${esc(p.location)}</td><td>${esc(nextDate(p)||'Brak danych')}<br>${badge(due(p).label,due(p).tone)}</td><td>${esc(p.inspectionPlanDate||'Nie zaplanowano')}${p.inspectionPlanDate&&p.inspectionPlanDate<today()?'<br>'+badge('Wizyta po terminie','red'):''}${late?'<br>'+badge('Wizyta po terminie z interwału','amber'):''}</td><td>${esc(p.inspectionPlanAssignee||'—')}</td><td class="preline">${esc(p.inspectionPlanNote||'—')}</td><td>${printing?'':button('Zaplanuj / zmień','plan-inspection',p.id,'small')+button('Wykonaj przegląd','new-inspection',p.id,'small')}</td></tr>`;
    }));
}
function renderSchedule() {
    const rows=scheduleRows(),active=db.panels.filter(p=>!p.archived);
    $('content').innerHTML=heading('Plan przeglądów','Data uzgodnionej wizyty nie zmienia terminu wynikającego z ostatniego pozytywnego przeglądu.',button('Drukuj plan / PDF','print-schedule'))+
      `<div class="cards"><div class="card"><div class="card-label">Aktywne centrale</div><div class="metric">${active.length}</div></div><div class="card"><div class="card-label">Zaplanowane wizyty</div><div class="metric">${active.filter(p=>p.inspectionPlanDate).length}</div></div><div class="card"><div class="card-label">Bez planu wizyty</div><div class="metric">${active.filter(p=>!p.inspectionPlanDate).length}</div></div><div class="card"><div class="card-label">Przeglądy po terminie</div><div class="metric">${active.filter(p=>due(p).label==='Po terminie').length}</div></div></div>`+
      `<div class="toolbar"><input id="search" aria-label="Szukaj" placeholder="Centrala, obiekt, wykonawca…" value="${esc(filters.search||'')}"><label>Miesiąc <input id="schedule-month" type="month" value="${esc(filters.month||'')}"></label><select id="plan-filter" aria-label="Stan planu">${options([['','Wszystkie'],['planned','Zaplanowane'],['unplanned','Bez planu'],['late','Wizyta po terminie'],['overdue','Przegląd po terminie']],filters.plan||'')}</select><span class="hint">${rows.length} central w widoku</span></div>`+
      `<p class="hint">Miesiąc odnosi się do daty wizyty, a przy braku planu — do terminu z interwału. Liczniki obejmują wszystkie aktywne centrale. Po wykonaniu wizyty zatwierdź protokół utworzony z aktualnego planu.</p>`+scheduleTable(rows);
}
function openInspectionPlan(id) {
    const p=db.panels.find(p=>p.id===id);if(!p||p.archived)throw new Error('Wybierz aktywną centralę.');
    modal('inspection-plan','Plan przeglądu — '+p.id,`<p class="hint">Termin z interwału: <strong>${esc(nextDate(p)||'Brak ostatniego pozytywnego przeglądu')}</strong>. Uzgodniona wizyta nie przesuwa tego terminu. Aby odwołać plan, zaznacz pole poniżej.</p><div class="form-grid">${field('inspectionPlanDate','Data uzgodnionej wizyty',p.inspectionPlanDate||'','date')}${field('inspectionPlanAssignee','Wykonawca',p.inspectionPlanAssignee||'','text','maxlength="250" list="plan-technicians"')}${field('inspectionPlanNote','Zakres / ustalenia organizacyjne',p.inspectionPlanNote||'','textarea','maxlength="2000"',true)}</div><datalist id="plan-technicians">${options(service.technicians,'')}</datalist><label class="checkbox"><input type="checkbox" name="cancelPlan">Odwołaj zaplanowaną wizytę</label>`,p);
}
function renderPanelCard(id) {
    const p=db.panels.find(p=>p.id===id);if(!p){selectedPanel='';return renderPanels();}
    const faults=db.faults.filter(f=>f.panelId===id), history=db.history.filter(h=>h.panelId===id);
    $('content').innerHTML=heading(p.id,p.location+(lockLabel('panels/'+id)?' · '+lockLabel('panels/'+id):''),button('Powrót','navigate','panels')+button('Edytuj','edit-panel',id)+button('Drukuj kartę / PDF','print-panel',id)+(!p.archived?button('Nowy przegląd','new-inspection',id,'primary'):''))+
      `<div class="grid2"><section class="panel"><h2>Dane techniczne</h2>${details([['Model',p.model],['Dokładne miejsce',p.spot],['Nr seryjny',p.serialNo],['Stan',p.condition],['Interwał',p.intervalMonths+' miesięcy'],['Ostatni przegląd',p.lastInspection],['Kolejny termin',nextDate(p)],['Uzgodniona wizyta',p.inspectionPlanDate],['Wykonawca wizyty',p.inspectionPlanAssignee],['Ustalenia wizyty',p.inspectionPlanNote],['Obsługiwany obszar',p.coverage],['Kontakt do serwisu',p.serviceContact],['Uwagi',p.notes]])}</section><section class="panel"><h2>Obsługa urządzenia</h2><p>${faults.filter(faultIsActive).length} otwartych zgłoszeń · ${history.length} wpisów historii</p><div class="actions">${!p.archived?button('Zaplanuj przegląd','plan-inspection',id)+button('Zgłoś usterkę','new-fault',id)+button('Protokół serwisu','new-protocol',id):''}${button(p.archived?'Przywróć do ewidencji':'Archiwizuj centralę','archive-panel',id,'danger')}</div><p class="hint">Archiwizacja zachowuje historię. Najpierw zamknij otwarte zgłoszenia i protokoły robocze.</p></section></div>${elementTable(p)}<section class="panel"><h2>Dokumentacja centrali</h2><p class="hint">Załączniki są częścią bazy i kopii zapasowych. Dodawaj je przez edycję centrali.</p>${table(['Dokument',''],(p.documents||[]).map(d=>`<tr><td>${esc(d.name)}</td><td>${button('Pobierz','document-download',p.id+'|'+d.id,'small')}</td></tr>`),'Brak dokumentów.')}</section><h2>Zgłoszenia centrali</h2>${faultTable(faults)}<h2 class="section-title">Protokoły i historia</h2>${protocolTable(history)}${can('protocols.view')?`<section class="panel"><h2>Historia kosztów centrali</h2>${costTable((db.costs||[]).filter(c=>history.some(h=>h.id===c.protocolId)))}</section>`:''}`;
}
const priorityRank = f => ['Niski','Normalny','Wysoki','Krytyczny'].indexOf(f.priority);
function faultTable(rows,compact=false) {
    return table(compact?['Zgłoszenie','Zgłaszający','Priorytet','']:['Zgłoszenie / data','Centrala','Zgłaszający','Priorytet / termin','Odpowiedzialny','Status',''],rows.map(f=>`<tr><td>${button(faultNumber(f),'view-fault',f.id,'link')}<br>${esc(f.desc.slice(0,110))}${f.desc.length>110?'…':''}${!compact?`<br><span class="muted">${esc(f.date)}</span>`:''}</td>${!compact?`<td>${button(f.panelId,'panel-card',f.panelId,'link')}</td>`:''}<td>${esc(f.reporter||'—')}</td><td data-sort-value="${priorityRank(f)}">${badge(f.priority||'Normalny',priorityRank(f)>=2?'red':'')}<br>${!compact?esc(f.dueDate||'—'):''}${faultIsActive(f)&&f.dueDate&&daysUntil(f.dueDate)<0?'<br>'+badge('Po terminie','red'):''}</td>${!compact?`<td>${esc(f.assignee||'Nie przypisano')}</td><td>${badge(f.status,faultTone(f.status))}${f.workStage?'<br>'+esc(f.workStage):''}</td>`:''}<td><div class="actions">${button('Historia','view-fault',f.id,'small')}${faultIsActive(f)?button('Dodaj wpis','log-fault',f.id,'small'):''}</div></td></tr>`));
}
function filteredFaults() {
    return db.faults.filter(f=>matches(f)&&(!filters.status||f.status===filters.status)
        &&(!filters.stage||f.workStage===filters.stage)
        &&(!filters.assignee||f.assignee===filters.assignee)
        &&(!filters.from||f.date.slice(0,10)>=filters.from)&&(!filters.to||f.date.slice(0,10)<=filters.to)
        &&(!filters.attention||(filters.attention==='overdue'?faultIsActive(f)&&f.dueDate&&daysUntil(f.dueDate)<0:
            filters.attention==='unassigned'?faultIsActive(f)&&!f.assignee?.trim():faultIsActive(f))))
        .sort((a,b)=>b.date.localeCompare(a.date));
}
function renderFaults() {
    if(selectedFault)return renderFaultDetail(selectedFault);
    const rows=filteredFaults();
    $('content').innerHTML=heading('Zgłoszenia serwisowe','Każde zgłoszenie ma własną historię czynności i zmian statusu.',button('Nowe zgłoszenie','new-fault','','primary'))+toolbar(faultStatuses,'Opis, centrala, zgłaszający, odpowiedzialny…')+
      `<div class="toolbar"><select id="fault-attention" aria-label="Wymagające uwagi">${options([['','Wszystkie sprawy'],['active','Otwarte'],['overdue','Otwarte po terminie'],['unassigned','Otwarte bez odpowiedzialnego']],filters.attention||'')}</select><select id="fault-stage" aria-label="Etap prac">${options([['','Wszystkie etapy'],'Diagnoza','Naprawa','Oczekiwanie na części','Oczekiwanie na serwis','Weryfikacja'],filters.stage||'')}</select><select id="fault-assignee" aria-label="Odpowiedzialny">${options([['','Wszyscy odpowiedzialni'],...Array.from(new Set(db.faults.map(f=>f.assignee).filter(Boolean))).sort()],filters.assignee||'')}</select><label>Od <input id="date-from" type="date" value="${esc(filters.from||'')}"></label><label>Do <input id="date-to" type="date" value="${esc(filters.to||'')}"></label><span class="hint">${rows.length} zgłoszeń</span></div>`+faultTable(rows);
}
function renderFaultDetail(id) {
    const f=db.faults.find(f=>f.id===id);if(!f){selectedFault='';return renderFaults();}
    const linked=db.history.filter(h=>h.faultId===f.id);
    const events=f.timeline||[];
    const timeline=events.length?events.map((e,i)=>`<article class="timeline-entry"><div class="timeline-marker" aria-hidden="true"></div><div class="timeline-card"><div class="timeline-head"><strong>${esc(e.author||'System')}</strong><time datetime="${esc(e.at)}">${esc(e.at ? new Date(e.at.replace(' ','T')).toLocaleString('pl-PL') : '—')}</time></div>${e.fromStatus!==undefined&&e.toStatus!==undefined?`<div class="timeline-transition">${badge(e.fromStatus,faultTone(e.fromStatus))}<span aria-hidden="true">→</span>${badge(e.toStatus,faultTone(e.toStatus))}</div>`:''}${e.performedBy?`<div class="hint">Czynności wykonał(a): ${esc(e.performedBy)}</div>`:''}<p class="preline">${esc(e.text)}</p>${e.type==='protocol'?badge('Protokół') : e.type==='action'?badge('Czynność serwisowa','blue'):e.type==='updated'?badge('Zmiana danych'):e.type==='migration'?badge('Migracja'):badge('System')}</div></article>`).join(''):`<div class="panel"><p class="muted">Brak zapisanych działań. Zgłoszenie pochodzi ze starszej wersji lub nie było jeszcze modyfikowane. Wcześniejszych czynności nie można odtworzyć.</p></div>`;
    $('content').innerHTML=heading('Zgłoszenie '+faultNumber(f),panelName(f.panelId)+(lockLabel('faults/'+id)?' · '+lockLabel('faults/'+id):''),button('Powrót do zgłoszeń','navigate','faults')+button('Edytuj dane','edit-fault',id)+button('Drukuj / PDF','print-fault',id)+button('Dodaj wpis / zmień status','log-fault',id,'primary'))+
      `<div class="fault-summary">${badge(f.status,faultTone(f.status))} ${badge(f.priority,priorityRank(f)>=2?'red':'')} <span class="muted">Zarejestrowano: ${esc(f.date)}</span></div>`+
      `<div class="grid2"><section class="panel"><h2>Opis zgłoszenia</h2><p class="preline fault-description">${esc(f.desc)}</p>${details([['Zgłaszający',f.reporter],['Centrala',panelName(f.panelId)],['Odpowiedzialny',f.assignee],['Etap prac',f.workStage],['Termin',f.dueDate],['Wystąpienie usterki',f.occurredAt],['Adres elementu / pętla',f.elementAddress],['Typ elementu w chwili zgłoszenia',f.elementType],['Lokalizacja elementu w chwili zgłoszenia',f.elementLocation],['Przyczyna',f.cause],['Sposób usunięcia',f.resolution],['Wynik sprawdzenia',f.verification],['Data zakończenia',f.status==='Zakończone'?f.closedAt:'']])}</section><section class="panel"><h2>Dalsza obsługa</h2><p>Każdy serwisant może dodać diagnozę, informację o brakujących częściach i opis naprawy. Poprzednie wpisy pozostają widoczne.</p><div class="actions">${button('Dodaj czynność / zmień status','log-fault',id,'primary')}${faultIsActive(f)?button('Nowy protokół naprawy','service-fault',id):''}</div><p class="hint">Status „Zakończone” można ustawić po wykonaniu naprawy i opisaniu jej we wpisie albo podczas zatwierdzania pozytywnego protokołu. Anulowanie również wymaga opisu.</p></section></div>`+
      `<section class="timeline-section"><div class="timeline-title"><h2>Historia zgłoszenia</h2><span class="muted">${events.length} wpisów</span></div><div class="timeline">${timeline}</div></section>`+
      `<section class="panel"><h2>Powiązania i nawroty</h2>${f.sourceProtocolId?button('Protokół źródłowy','view-protocol',f.sourceProtocolId,'small'):''}<p>${esc(f.relationType||'')}</p>${faultTable(db.faults.filter(x=>x.id===f.relatedFaultId||x.relatedFaultId===f.id),true)}</section><h2 class="section-title">Powiązane protokoły</h2>${protocolTable(linked)}`;
}
function protocolLabel(h) { return h.protocolStatus==='draft'?'Roboczy':h.protocolStatus==='final'?'Zatwierdzony':'Wpis historyczny'; }
function protocolTable(rows) {
    return table(['Numer / data','Centrala','Rodzaj','Wykonawca','Wynik / stan',''],rows.slice().sort((a,b)=>b.date.localeCompare(a.date)).map(h=>`<tr><td>${button(h.protocolNo||'Szkic — bez numeru','view-protocol',h.id,'link')}${h.inspectionNo?`<br>${badge('Przegląd '+h.inspectionNo,'blue')}`:''}<br><span class="muted">${esc(h.date)}</span></td><td>${esc(h.panelId)}</td><td>${esc(h.type)}</td><td>${esc(h.technician||h.contractor)}</td><td>${badge(h.result||'Nie określono',h.result==='Pozytywny'?'green':h.result?'red':'')}<br>${badge(protocolLabel(h),h.protocolStatus==='draft'?'amber':'')}</td><td>${h.protocolStatus==='draft'?button('Edytuj','edit-protocol',h.id,'small'):button('Dokument','view-protocol',h.id,'small')}</td></tr>`));
}
function renderProtocols() {
    if(selectedProtocol) return renderProtocolView(selectedProtocol);
    const rows=db.history.filter(h=>matches(h)&&(!filters.status||h.protocolStatus===filters.status)&&(!filters.from||h.date.slice(0,10)>=filters.from)&&(!filters.to||h.date.slice(0,10)<=filters.to));
    $('content').innerHTML=heading('Protokoły i historia','Szkice robocze, zatwierdzone dokumenty i wpisy z poprzedniej wersji.',button('Nowy protokół','new-protocol','','primary')+button('Raport / PDF','print-report')+button('Eksport CSV','report-csv'))+
      toolbar([['draft','Robocze'],['final','Zatwierdzone'],['legacy','Wpisy historyczne']],'Numer protokołu, opis, wykonawca…')+
      `<div class="toolbar"><label>Od <input id="date-from" type="date" value="${esc(filters.from||'')}"></label><label>Do <input id="date-to" type="date" value="${esc(filters.to||'')}"></label><span class="hint">${rows.length} wpisów</span></div>`+protocolTable(rows);
}

function faultPrintHTML(f){
 return `<article class="protocol-preview"><h1>Zgłoszenie ${esc(faultNumber(f))}</h1>${details([['Centrala',panelName(f.panelId)],['Data zgłoszenia',f.date],['Zgłaszający',f.reporter],['Status',f.status],['Priorytet',f.priority],['Odpowiedzialny',f.assignee],['Etap prac',f.workStage],['Termin',f.dueDate],['Adres elementu',f.elementAddress],['Typ elementu',f.elementType],['Lokalizacja elementu',f.elementLocation],['Opis',f.desc],['Przyczyna',f.cause],['Sposób usunięcia',f.resolution],['Sprawdzenie',f.verification]])}<h2>Historia czynności</h2>${(f.timeline||[]).map(e=>`<section><strong>${esc(e.at)} · ${esc(e.author)}</strong><p class="preline">${esc(e.text)}</p></section>`).join('')}</article>`;
}
function reportRows(){return db.history.filter(h=>matches(h)&&(!filters.status||h.protocolStatus===filters.status)&&(!filters.from||h.date.slice(0,10)>=filters.from)&&(!filters.to||h.date.slice(0,10)<=filters.to)).sort((a,b)=>a.date.localeCompare(b.date));}
function reportHTML(){const rows=reportRows();return `<article class="protocol-preview"><h1>Raport prac SSP</h1><p>${esc(service.site)} · Okres: ${esc(filters.from||'początek ewidencji')} – ${esc(filters.to||today())}</p><p>Wpisów: ${rows.length}; zatwierdzonych: ${rows.filter(h=>h.protocolStatus==='final').length}; przeglądów: ${rows.filter(h=>h.type==='Przegląd').length}; wyników negatywnych: ${rows.filter(h=>h.result==='Negatywny').length}</p>${table(['Dokument','Data','Centrala','Rodzaj','Wykonawca','Wynik'],rows.map(h=>`<tr>${[h.protocolNo||'Szkic',h.date,h.panelId,h.type,h.technician||h.contractor,h.result].map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`))}</article>`;}
function exportReportCSV(){csvDownload([['Numer','Data','Centrala','Rodzaj','Wykonawca','Wynik','Stan','Opis'],...reportRows().map(h=>[h.protocolNo,h.date,h.panelId,h.type,h.technician||h.contractor,h.result,protocolLabel(h),h.desc])],'CommandFIRE-raport-'+today()+'.csv');}

const costCategories=['Części','Robocizna','Dojazd','Inne'];
function parseMoneyGrosz(value){
    const text=String(value||'').trim().replace(',','.');
    if(!/^(0|[1-9]\d{0,8})(\.\d{1,2})?$/.test(text))throw new Error('Podaj kwotę z maksymalnie dwoma miejscami po przecinku.');
    const [whole,fraction='']=text.split('.');const amount=Number(whole)*100+Number(fraction.padEnd(2,'0'));
    if(!Number.isSafeInteger(amount)||amount<=0||amount>10000000000)throw new Error('Kwota: od 0,01 do 100 000 000 PLN.');
    return amount;
}
const money=value=>new Intl.NumberFormat('pl-PL',{style:'currency',currency:'PLN'}).format(value/100);
function costTable(rows,printing=false){
    const all=rows.slice().sort((a,b)=>b.date.localeCompare(a.date)||(b.createdAt||'').localeCompare(a.createdAt||''));
    const reversed=new Set((db.costs||[]).map(c=>c.reversesId).filter(Boolean));
    return `<p><strong>Suma wpisów: ${esc(money(rows.reduce((sum,c)=>sum+c.amountGrosz,0)))}</strong> · ${rows.length} wpisów${!printing&&rows.length>200?' · pokazano 200 ostatnich; pełna lista w CSV':''}</p>`+
      table(['Data / protokół','Kategoria','Opis / dokument','Kwota brutto','Zapisano przez',''],(printing?all:all.slice(0,200)).map(c=>{
        const h=db.history.find(h=>h.id===c.protocolId),isReversal=Boolean(c.reversesId);
        return `<tr><td>${esc(c.date)}<br>${printing?esc(h?.protocolNo||c.protocolId):button(h?.protocolNo||'Wpis historyczny','view-protocol',c.protocolId,'link')}</td><td>${esc(c.category)}${isReversal?'<br>'+badge('Korekta','amber'):reversed.has(c.id)?'<br>'+badge('Skorygowany'):''}</td><td class="preline">${esc(c.description)}<br><span class="muted">${esc(c.reference||'—')}</span></td><td data-sort-value="${c.amountGrosz}">${esc(money(c.amountGrosz))}</td><td>${esc(c.createdBy||'Import')}<br><span class="muted">${esc(c.createdAt||'—')}</span></td><td>${printing||isReversal||reversed.has(c.id)?'':button('Korekta','reverse-cost',c.id,'small')}</td></tr>`;
    }),'Brak wpisów kosztowych. Brak wpisu nie oznacza zerowego kosztu.');
}
function openCost(protocolId='',reverseId=''){
    const original=(db.costs||[]).find(c=>c.id===reverseId);
    if(reverseId&&(!original||original.amountGrosz<0||(db.costs||[]).some(c=>c.reversesId===reverseId)))throw new Error('Tego wpisu nie można ponownie skorygować.');
    const protocols=db.history.filter(h=>h.protocolStatus==='final'||h.protocolStatus==='legacy');
    if(!protocols.length)throw new Error('Najpierw zatwierdź protokół.');
    modal('cost',original?'Korekta kosztu':'Nowy koszt serwisu',`<p class="hint">Kwoty brutto w PLN. Zapis jest trwały. Korekta odwraca cały wskazany koszt; poprawną kwotę można potem dodać jako nowy wpis. Protokół techniczny pozostaje niezmienny.</p><div class="form-grid">${original?`<div class="full">Odwracany koszt: <strong>${esc(money(original.amountGrosz))}</strong> · ${esc(original.description)}</div>`:select('protocolId','Protokół',protocols.map(h=>[h.id,(h.protocolNo||'Wpis historyczny')+' · '+h.panelId+' · '+h.date]),protocolId||protocols[0].id,'required')}${field('date','Data kosztu / korekty',today(),'date',`required max="${today()}" ${original?`min="${esc(original.date)}"`:''}`)}${!original?select('category','Kategoria',costCategories,'Części')+field('amount','Kwota brutto PLN','','text','required inputmode="decimal" maxlength="20" placeholder="np. 123,45"'):''}${field('reference','Nr faktury / dokumentu wewnętrznego','','text','maxlength="120"')}${field('description',original?'Powód korekty':'Opis kosztu','','textarea','required maxlength="2000"',true)}</div>`,original||null);
}
function monthlyData(){
    const within=day=>!filters.month||String(day||'').slice(0,7)===filters.month;
    const panelOk=id=>!filters.panel||id===filters.panel;
    const history=db.history.filter(h=>h.protocolStatus==='final'&&within(h.date)&&panelOk(h.panelId));
    const faults=db.faults.filter(f=>within(f.date)&&panelOk(f.panelId));
    const byProtocol=new Map(db.history.map(h=>[h.id,h]));
    const costs=(db.costs||[]).filter(c=>within(c.date)&&panelOk(byProtocol.get(c.protocolId)?.panelId));
    const groups=new Map();
    const group=id=>{if(!groups.has(id))groups.set(id,{id,protocols:0,inspections:0,negative:0,hours:0,faults:0,totalGrosz:0,categories:Object.fromEntries(costCategories.map(c=>[c,0]))});return groups.get(id);};
    for(const h of history){const g=group(h.panelId);g.protocols++;g.inspections+=Number(h.type==='Przegląd');g.negative+=Number(h.result==='Negatywny');g.hours+=Number(h.hours||0);}
    for(const f of faults)group(f.panelId).faults++;
    for(const c of costs){const g=group(byProtocol.get(c.protocolId)?.panelId||'Brak powiązania');g.totalGrosz+=c.amountGrosz;g.categories[c.category]+=c.amountGrosz;}
    const confirmed=faults.filter(f=>f.relationType==='Nawrót'&&f.relatedFaultId&&f.status!=='Anulowane');
    // Candidates use exact normalized element addresses. They are not confirmed diagnoses.
    const candidates=new Map();
    for(const f of db.faults){
        if(!panelOk(f.panelId)||f.status==='Anulowane'||f.relationType==='Duplikat'||!f.elementAddress?.trim())continue;
        const address=f.elementAddress.trim().replace(/\s+/g,' ').toLocaleLowerCase('pl');
        const key=JSON.stringify([f.panelId,address]);
        if(!candidates.has(key))candidates.set(key,{panelId:f.panelId,address:f.elementAddress,rows:[]});
        candidates.get(key).rows.push(f);
    }
    const repeated=Array.from(candidates.values()).filter(g=>g.rows.length>=2&&g.rows.some(f=>within(f.date))).sort((a,b)=>b.rows.length-a.rows.length);
    const costProtocolIds=new Set((db.costs||[]).map(c=>c.protocolId));
    return {history,faults,costs,confirmed,repeated,groups:Array.from(groups.values()).sort((a,b)=>b.totalGrosz-a.totalGrosz||a.id.localeCompare(b.id)),
        totalGrosz:costs.reduce((sum,c)=>sum+c.amountGrosz,0),hours:history.reduce((sum,h)=>sum+Number(h.hours||0),0),
        withoutCost:history.filter(h=>!costProtocolIds.has(h.id)).length};
}
function monthlyHTML(printing=false){
    const r=monthlyData(),faultAccess=can('faults.view');
    const summary=`<div class="cards"><div class="card"><div class="card-label">Zatwierdzone prace</div><div class="metric">${r.history.length}</div></div><div class="card"><div class="card-label">Czas prac z protokołów</div><div class="metric">${esc(r.hours.toLocaleString('pl-PL',{maximumFractionDigits:2}))} h</div></div><div class="card"><div class="card-label">Koszty w okresie</div><div class="metric">${esc(money(r.totalGrosz))}</div></div><div class="card"><div class="card-label">Protokoły bez wpisu kosztowego</div><div class="metric">${r.withoutCost}</div></div></div>`;
    const groupTable=table(['Centrala','Prace / przeglądy','Wynik negatywny','Nowe zgłoszenia','Godziny','Części','Robocizna','Dojazd / inne','Suma brutto'],r.groups.map(g=>`<tr><td>${printing?esc(g.id):button(g.id,'panel-card',g.id,'link')}</td><td>${g.protocols} / ${g.inspections}</td><td>${g.negative}</td><td>${faultAccess?g.faults:'Brak dostępu'}</td><td>${esc(g.hours.toLocaleString('pl-PL',{maximumFractionDigits:2}))}</td>${[g.categories['Części'],g.categories['Robocizna'],g.categories['Dojazd']+g.categories['Inne'],g.totalGrosz].map(n=>`<td data-sort-value="${n}">${esc(money(n))}</td>`).join('')}</tr>`));
    const ref=f=>printing?esc(faultNumber(f)):button(faultNumber(f),'view-fault',f.id,'link');
    const repeats=faultAccess?`<h2 class="section-title">Potwierdzone nawroty: ${r.confirmed.length}</h2>${table(['Data nowego zgłoszenia','Centrala','Nawrót','Poprzednia sprawa'],r.confirmed.map(f=>{const old=db.faults.find(x=>x.id===f.relatedFaultId);return `<tr><td>${esc(f.date)}</td><td>${esc(f.panelId)}</td><td>${ref(f)}<br>${esc(f.desc)}</td><td>${old?ref(old):'Brak dostępu'}</td></tr>`;}))}<h2 class="section-title">Powtórzenia adresu elementu do sprawdzenia</h2><p class="hint">Co najmniej dwa nieanulowane zgłoszenia dla tego samego adresu elementu i centrali, z co najmniej jednym zgłoszeniem w wybranym okresie. Porównujemy całą dostępną historię. To wskazówka do analizy, nie potwierdzenie wspólnej przyczyny.</p>${table(['Centrala','Adres elementu','Liczba w historii','Zgłoszenia'],r.repeated.map(g=>`<tr><td>${esc(g.panelId)}</td><td>${esc(g.address)}</td><td>${g.rows.length}</td><td>${g.rows.map(ref).join(' · ')}</td></tr>`))}`:'<p class="hint">Analiza zgłoszeń wymaga uprawnienia do podglądu zgłoszeń.</p>';
    return `<article class="${printing?'protocol-preview':''}">${printing?`<h1>Raport miesięczny SSP</h1><p>Okres: ${esc(filters.month||'Cała historia')} · Centrala: ${esc(filters.panel||'Wszystkie')} · Stan na ${esc(today())}</p>`:''}${summary}<p class="hint">Prace według daty wykonania; zgłoszenia według daty zgłoszenia; koszty według daty wpisanego kosztu lub korekty. Szkice nie są liczone jako wykonane prace. Brak kosztu oznacza brak wpisu, a nie potwierdzone 0 PLN.</p><h2>Zestawienie według central</h2>${groupTable}${repeats}<h2 class="section-title">Historia kosztów w okresie</h2>${costTable(r.costs,printing)}</article>`;
}
function renderReports(){
    const panels=Array.from(new Set([...db.panels.map(p=>p.id),...db.history.map(h=>h.panelId)])).sort();
    $('content').innerHTML=heading('Raporty i koszty','Zestawienia miesięczne, nawroty usterek i rozliczenia serwisu.',button('Dodaj koszt','new-cost','','primary')+button('Drukuj / PDF','print-monthly')+button('Zestawienie CSV','monthly-csv')+button('Koszty CSV','costs-csv'))+
      `<div class="toolbar"><label>Miesiąc <input id="report-month" type="month" value="${esc(filters.month||'')}"></label><select id="report-panel" aria-label="Centrala raportu">${options([['','Wszystkie centrale'],...panels],filters.panel||'')}</select><span class="hint">Wyczyść miesiąc, aby objąć całą historię.</span></div>`+monthlyHTML();
}
function csvDownload(rows,filename){
    const quote=v=>{let s=String(v??'');if(/^[\s]*[=+@-]/.test(s)&&!/^[-]?\d+([.,]\d+)?$/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};
    const text='\ufeff'+rows.map(row=>row.map(quote).join(';')).join('\r\n');
    const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const csvMoney=grosz=>(grosz/100).toFixed(2).replace('.',',');
function exportMonthlyCSV(){const r=monthlyData();csvDownload([['Okres','Centrala','Prace','Przeglądy','Wynik negatywny','Nowe zgłoszenia','Godziny','Części PLN brutto','Robocizna PLN brutto','Dojazd PLN brutto','Inne PLN brutto','Suma PLN brutto'],...r.groups.map(g=>[filters.month||'Cała historia',g.id,g.protocols,g.inspections,g.negative,can('faults.view')?g.faults:'Brak dostępu',g.hours.toFixed(2).replace('.',','),...costCategories.map(c=>csvMoney(g.categories[c])),csvMoney(g.totalGrosz)])],'CommandFIRE-zestawienie-'+(filters.month||'historia')+'.csv');}
function exportCostsCSV(){csvDownload([['Data','Centrala','Protokół','Kategoria','Kwota PLN brutto','Opis','Dokument','Korekta wpisu','Zapisano przez','Zapisano o'],...monthlyData().costs.map(c=>{const h=db.history.find(h=>h.id===c.protocolId);return[c.date,h?.panelId,h?.protocolNo||c.protocolId,c.category,csvMoney(c.amountGrosz),c.description,c.reference,c.reversesId,c.createdBy,c.createdAt];})],'CommandFIRE-koszty-'+(filters.month||'historia')+'.csv');}

function documentHTML(h) {
    const p=h.panelSnapshot||db.panels.find(p=>p.id===h.panelId)||{id:h.panelId};
    const s=h.serviceSnapshot||service;
    return `<article class="protocol-preview">${h.protocolStatus!=='final'?`<div class="draft-mark">${h.protocolStatus==='draft'?'DOKUMENT ROBOCZY — NIEZATWIERDZONY':'WYDRUK WPISU HISTORYCZNEGO — dane firmy i centrali według aktualnej ewidencji'}</div>`:''}
      <div class="document-head"><div><strong>${esc(s.company||'Firma / jednostka serwisowa — nie uzupełniono')}</strong><br>${esc(s.address)}<br>${s.taxId?'NIP: '+esc(s.taxId):''}<br>${esc([s.phone,s.email].filter(Boolean).join(' · '))}</div><div><strong>${esc(s.site||'Obiekt — nie uzupełniono')}</strong><br>${esc(s.siteAddress)}</div></div>
      <h1>Protokół: ${esc(h.type)}</h1><p><strong>Nr protokołu: ${esc(h.protocolNo||'Szkic bez numeru')}</strong>${h.inspectionNo?`<br><strong>Nr przeglądu: ${esc(h.inspectionNo)}</strong>`:''} · Data wykonania: ${esc(h.date)}</p>
      ${details([['Centrala / model',`${p.id||''} / ${p.model||''}`],['Lokalizacja',[p.location,p.spot].filter(Boolean).join(' — ')],['Numer seryjny',p.serialNo],['Wykonawca',h.technician||h.contractor],['Zgłoszenie',faultNumber(db.faults.find(f=>f.id===h.faultId))||h.faultId],['Uzupełnienie protokołu',h.referenceProtocolNo],['Zakres',h.scope]])}
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
    $('content').innerHTML=heading(h.protocolNo||'Protokół roboczy',protocolLabel(h),button('Powrót','navigate','protocols')+(h.protocolStatus==='draft'?button('Edytuj','edit-protocol',id,'primary')+button('Usuń szkic','delete-draft',id,'danger'):button('Protokół uzupełniający','followup-protocol',id))+button('Drukuj / PDF','print-protocol',id))+(h.inspectionPlanSnapshot?`<section class="panel"><h2>Rozliczona wizyta</h2>${details([['Uzgodniona data',h.inspectionPlanSnapshot.inspectionPlanDate],['Planowany wykonawca',h.inspectionPlanSnapshot.inspectionPlanAssignee],['Ustalenia',h.inspectionPlanSnapshot.inspectionPlanNote]])}</section>`:'')+documentHTML(h)+(h.protocolStatus!=='draft'?`<section class="panel"><h2>Koszty serwisu</h2><p class="hint">Rejestr rozliczeń jest oddzielny od zatwierdzonego dokumentu. Kwoty brutto, PLN.</p>${button('Dodaj koszt','new-cost',h.id,'primary')}${costTable((db.costs||[]).filter(c=>c.protocolId===h.id))}</section>`:'')+(h.checklist?.some(c=>c.result==='Usterka')?`<section class="panel"><h2>Usterki wykryte podczas kontroli</h2>${h.checklist.map((c,i)=>c.result==='Usterka'?`<p>${esc(c.label)} — ${esc(c.note)} ${button('Utwórz zgłoszenie','fault-from-check',h.id+'|'+i,'small')}</p>`:'').join('')}</section>`:'');
}
function settingsFields(s) {
    const numbering=[['fault','Zgłoszenia'],['inspection','Przeglądy'],['protocol','Protokoły']].map(([key,label])=>{
        const rule=numberRule(key);
        return `<fieldset class="numbering-series"><legend>${esc(label)}</legend><div class="form-grid">${field('num_'+key+'_prefix','Prefiks',rule.prefix,'text','required maxlength="16" pattern="[A-Za-z0-9_-]{1,16}"')}${field('num_'+key+'_start','Numer początkowy',rule.start,'number','required min="1" max="99999999"')}${field('num_'+key+'_digits','Liczba cyfr',rule.digits,'number','required min="1" max="9"')}${select('num_'+key+'_annual','Tryb numeracji',[['yes','Roczna (z rokiem)'],['no','Ciągła (bez roku)']],rule.annual?'yes':'no')}</div><p class="hint">Przykład: ${esc(exampleNumber(key))}. Zmiana numeracji dotyczy tylko nowych dokumentów.</p></fieldset>`;
    }).join('');
    return `<div class="form-grid">${field('company','Firma / jednostka serwisowa',s.company)}${field('taxId','NIP',s.taxId)}${field('address','Adres firmy',s.address)}${field('phone','Telefon',s.phone)}${field('email','E-mail',s.email,'email')}${field('site','Nazwa obiektu',s.site)}${field('siteAddress','Adres obiektu',s.siteAddress)}${field('inspectionMonths','Domyślny interwał przeglądów (mies.)',s.inspectionMonths,'number','required min="1" max="120"')}${field('reminderDays','Wyprzedzenie przypomnień (dni)',s.reminderDays,'number','required min="1" max="365"')}${field('technicians','Technicy — jeden w każdym wierszu',s.technicians.join('\n'),'textarea','',true)}${field('checklist','Szablon kontroli przeglądu — jedna czynność w wierszu',s.checklist.join('\n'),'textarea','',true)}</div><h3>Numeracja dokumentów</h3><p class="hint">Trzy niezależne serie. Numery nadaje automatycznie serwer w momencie rejestracji zgłoszenia lub zatwierdzenia protokołu.</p><div class="numbering-grid">${numbering}</div>`;
}
function renderSettings() {
    $('content').innerHTML=heading('Konfiguracja serwisu','Wspólne ustawienia zapisane w bazie. Zatwierdzone numery i dokumenty pozostają niezmienne.')+
      `<div class="panel"><h2>${esc(service.company||'Nie uzupełniono firmy')}</h2>${details([['Obiekt',service.site],['Adres',service.address],['Numery zgłoszeń',exampleNumber('fault')],['Numery przeglądów',exampleNumber('inspection')],['Numery protokołów',exampleNumber('protocol')],['Domyślny interwał',service.inspectionMonths+' miesięcy'],['Technicy',service.technicians.join(', ')],['Lista kontrolna',service.checklist.length+' czynności']])}<p class="hint">Przykłady pokazują format serii, a nie numer następnego dokumentu. Zmiany nie przepisują numerów już istniejących. Szablon kontroli dotyczy wyłącznie nowych protokołów.</p>${button('Edytuj konfigurację i numerację','edit-settings','','primary')}</div>`;
}

async function renderUsers() {
 $('content').innerHTML=heading('Użytkownicy i uprawnienia','Kontami zarządza administrator. Zmiana roli, hasła lub zablokowanie konta unieważnia jego sesję.',button('Dodaj użytkownika','new-user','','primary'))+
 '<div id="users-list">Odczytywanie listy użytkowników…</div>';
 try {const result=await api('/api/users');accountUsers=result.users;availablePermissions=result.permissions;roleDefaults=result.roles;
 if(!$('users-list'))return;
 $('users-list').innerHTML=table(['Użytkownik','Rola','Stan','Uprawnienia','Operacje'],accountUsers.map(u=>`<tr><td><strong>${esc(u.displayName)}</strong><br><span class="muted">${esc(u.username)}</span></td><td>${badge(u.role,u.role==='ADMIN'?'blue':'')}</td><td>${badge(u.enabled?'Aktywny':'Zablokowany',u.enabled?'green':'red')}${u.mustChangePassword?'<br>'+badge('Wymagana zmiana hasła','amber'):''}</td><td>${u.permissions.length} uprawnień</td><td>${button('Edytuj','edit-user',u.id,'small')} ${button('Resetuj hasło','reset-user',u.id,'small')}</td></tr>`));
 }catch(e){if($('users-list'))$('users-list').textContent=e.message;}
}
function accountFields(user) {
 const u=user||{username:'',displayName:'',role:'SERWISANT',enabled:true,permissions:roleDefaults.SERWISANT||[]};
 const roleOptions=Object.keys(roleDefaults).map(k=>[k,({ADMIN:'Administrator',SERWISANT:'Serwisant',DYSPOZYTOR:'Dyspozytor',ODCZYT:'Tylko odczyt'})[k]]);
 const list=Object.entries(availablePermissions).filter(([key])=>!['backups.view','backups.manage','users.manage'].includes(key)).map(([key,label])=>`<label class="permission-choice"><input type="checkbox" name="perm_${esc(key)}" data-permission="${esc(key)}" ${u.permissions.includes(key)?'checked':''} ${u.role==='ADMIN'?'disabled':''}><span>${esc(label)}</span></label>`).join('');
 return `<div class="form-grid">${field('username','Login',u.username,'text',user?'readonly':'required pattern="[a-zA-Z0-9._-]{3,40}" maxlength="40"')}${field('displayName','Imię i nazwisko',u.displayName,'text','required maxlength="120"')}${select('role','Rola',roleOptions,u.role)}${select('enabled','Stan konta',[['yes','Aktywne'],['no','Zablokowane']],u.enabled?'yes':'no')}${!user?field('password','Hasło początkowe (min. 12 znaków)','','password','required minlength="12" maxlength="128"',true):''}</div><h3>Dostęp do funkcji</h3><p class="hint">Zaznacz konkretne uprawnienia. Administrator zawsze posiada komplet uprawnień, w tym wyłączny dostęp do zakładki Baza danych i zarządzania użytkownikami. Nowe konto musi zmienić hasło podczas pierwszego logowania.</p><div class="permission-grid">${list}</div>`;
}
function openUser(id) {const u=accountUsers.find(x=>x.id===id);modal('user',u?'Edycja konta '+u.username:'Nowy użytkownik',accountFields(u),u||null);}
function openUserReset(id) {const u=accountUsers.find(x=>x.id===id);if(!u)return;
 modal('user-reset','Reset hasła — '+u.username,`<p class="hint">Nowe hasło będzie tymczasowe. Użytkownik zostanie wylogowany i będzie musiał zmienić je przy kolejnym logowaniu.</p><div class="form-grid">${field('password','Nowe hasło (min. 12 znaków)','','password','required minlength="12" maxlength="128"',true)}</div>`,u);
}
async function renderBackups() {
    if(currentUser?.role!=='ADMIN'){ $('content').innerHTML=heading('Brak dostępu','Operacje na wspólnej bazie danych są zastrzeżone dla administratora.'); return; }
    $('content').innerHTML=heading('Baza danych','Administracja wspólną bazą, eksport, kopie bezpieczeństwa i odtwarzanie. Tylko administrator.')+
      `<div class="database-admin-grid">
        <section class="panel"><h2>Eksport danych</h2><p class="hint">Zapisz aktualne dane w pliku JSON na tym komputerze. Eksport nie zawiera kont i skrótów haseł; jest to eksport danych roboczych, a nie pełna kopia do odzyskiwania kont.</p>${button('Eksportuj dane JSON','export','','primary')}</section>
        <section class="panel"><h2>Kopia bezpieczeństwa</h2><p class="hint">Wykonaj kopię wspólnego pliku na dysku z bazą. Pełne kopie obejmują konta; przechowuj je w miejscu niedostępnym dla nieuprawnionych.</p>${button('Utwórz kopię teraz','backup','','primary')}</section>
        <section class="panel database-danger"><h2>Import i przywracanie</h2><p class="hint">Import zastępuje dane central, zgłoszeń i protokołów. Obecne konta użytkowników pozostają zachowane. Przed importem tworzona jest kopia.</p>${button('Importuj bazę JSON / CFDB','import','','danger')}</section>
      </div><section class="panel"><h2>Pliki kopii</h2><p class="hint">Przechowujemy 30 ostatnich kopii oraz plik .bak z poprzednim zapisem. Kopie na tym samym udziale nie chronią przed awarią dysku sieciowego. Regularnie przechowuj odrębną kopię poza udziałem.</p><div id="backup-list">Odczytywanie kopii…</div></section>`;
    try { const items=await api('/api/backups');if(!$('backup-list'))return;$('backup-list').innerHTML=`<p>Ostatnia poprawna kopia: <strong>${esc(items.find(x=>x.valid)?.modifiedAt||'Brak poprawnej kopii')}</strong></p>`+table(['Plik / data','Rozmiar','Weryfikacja',''],items.map(x=>`<tr><td>${esc(x.name)}<br>${esc(x.modifiedAt)}</td><td>${Math.ceil(x.size/1024)} KB</td><td>${badge(x.valid?'Poprawna':'Uszkodzona',x.valid?'green':'red')}${x.valid?`<br>${x.summary.panels} central · ${x.summary.faults} zgłoszeń · ${x.summary.documents} dokumentów · ${x.summary.elements||0} elementów · ${x.summary.costs||0} kosztów`:''}</td><td>${x.valid?button('Pobierz','download-backup',x.name,'small'):esc(x.error)}</td></tr>`),'Nie utworzono jeszcze kopii.'); }
    catch(e){if($('backup-list'))$('backup-list').textContent=e.message;}
}
function auditDetail(detail) {
    const text=String(detail);
    if(!text.startsWith('Zgłoszenie: '))return esc(text);
    const body=text.slice('Zgłoszenie: '.length);
    const fault=db.faults.find(f=>[f.id,f.number].filter(Boolean).some(value=>body===value||body.startsWith(value+' — ')||body.startsWith(value+' · ')));
    if(!fault)return esc(text);
    const matched=[fault.id,fault.number].filter(Boolean).find(value=>body===value||body.startsWith(value+' — ')||body.startsWith(value+' · '));
    const legacy=matched===fault.id;
    const label=faultNumber(fault);
    const link=can('faults.view')?button(label,'view-fault',fault.id,'link'):esc(label);
    const context=legacy?' · Centrala: '+fault.panelId+(fault.desc?' · '+fault.desc.replace(/\s+/g,' ').slice(0,120):''):'';
    return 'Zgłoszenie: '+link+esc(context+body.slice(matched.length));
}
function renderAudit() {
    $('content').innerHTML=heading('Rejestr zmian','Historia zapisów wraz z zalogowanym użytkownikiem. Starsze wpisy mogą nie mieć autora.')+table(['Czas','Użytkownik','Operacja','Zmiany'],(db.audit||[]).slice().reverse().map(a=>`<tr><td>${esc(a.date)}</td><td>${esc(a.user||'—')}</td><td>${esc(a.action)}</td><td class="preline">${(a.details||[]).map(auditDetail).join('<br>')}</td></tr>`));
}
function modal(kind,title,html,record=null,actions='') {
    editor={kind,record};dirty=false;$('editor-title').textContent=title;$('editor-fields').innerHTML=html;
    $('form-error').textContent='';$('editor-actions').innerHTML=button('Anuluj','close-modal')+(actions||'<button type="submit" class="primary">Zapisz</button>');$('editor').showModal();
}
function closeModal(force=false) {
    if(busy)return;
    if(!force&&dirty&&!confirm('Odrzucić niezapisane zmiany w formularzu?'))return;
    $('editor').close();editor=null;dirty=false;
    void releaseLock().then(()=>{if(syncPending)void pollSynchronization();});
}
function activePanels() { return db.panels.filter(p=>!p.archived).map(p=>[p.id,panelName(p.id)]); }
const elementTypes=['Czujka dymu','Czujka ciepła','Czujka wielosensorowa','ROP','Moduł wejść/wyjść','Sygnalizator','Inny'];
function elementTable(p){
    return `<section class="panel"><div class="section-row"><h2>Elementy centrali</h2>${!p.archived?button('Dodaj element','new-element',p.id,'small'):''}</div><p class="hint">Słownik uzupełniaj stopniowo. Adres musi jednoznacznie wskazywać element w tej centrali, np. pętla i numer. Archiwizacja zachowuje powiązane zgłoszenia.</p>`+
      table(['Adres','Typ','Lokalizacja','Stan',''],(p.elements||[]).map(e=>`<tr><td>${esc(e.address)}</td><td>${esc(e.type||'—')}</td><td>${esc(e.location||'—')}</td><td>${badge(e.archived?'Archiwum':'Aktywny',e.archived?'':'green')}</td><td>${!p.archived?button('Edytuj','edit-element',JSON.stringify({panelId:p.id,id:e.id}),'small')+button(e.archived?'Przywróć':'Archiwizuj','archive-element',JSON.stringify({panelId:p.id,id:e.id}),'small'):''}</td></tr>`))+'</section>';
}
function openElement(panelId,id=''){
    const p=db.panels.find(p=>p.id===panelId);if(!p||p.archived)throw new Error('Wybierz aktywną centralę.');
    const element=(p.elements||[]).find(e=>e.id===id)||{id:uid('EL'),address:'',type:'',location:'',notes:'',archived:false};
    modal('element',id?'Edycja elementu — '+p.id:'Nowy element — '+p.id,`<div class="form-grid">${field('address','Adres (np. pętla 1 / element 42)',element.address,'text','required maxlength="200"')}${field('type','Typ',element.type,'text','maxlength="120" list="element-types"')}${field('location','Lokalizacja / pomieszczenie',element.location,'text','maxlength="500"',true)}${field('notes','Uwagi',element.notes,'textarea','maxlength="2000"',true)}</div><datalist id="element-types">${options(elementTypes,'')}</datalist><p class="hint">Zmiana nazwy lub lokalizacji w słowniku nie nadpisuje danych zapisanych we wcześniejszych zgłoszeniach.</p>`,{panelId,element,isNew:!id});
}
function similarFaults(panelId,elementId,address,description,excludeId=''){
    if(!can('faults.view'))return [];
    const addressKey=searchFold(address).trim().replace(/\s+/g,' ');
    const words=value=>new Set(searchFold(value).match(/[a-z0-9]{3,}/g)||[]);
    const needle=words(description);const results=[];
    for(const f of db.faults){
        if(f.id===excludeId||f.panelId!==panelId||f.status==='Anulowane'||f.relationType==='Duplikat')continue;
        const idMatch=Boolean(elementId&&f.elementId===elementId);
        const addressMatch=Boolean(addressKey&&addressKey===searchFold(f.elementAddress).trim().replace(/\s+/g,' '));
        const candidate=words(f.desc);const common=[...needle].filter(w=>candidate.has(w)).length;
        const ratio=common/Math.max(1,new Set([...needle,...candidate]).size);
        const textMatch=common>=2&&ratio>=0.35;
        if(idMatch||addressMatch||textMatch)results.push({fault:f,score:idMatch?3:addressMatch?2:ratio,
            reason:idMatch?'Ten sam element słownika':addressMatch?'Ten sam adres elementu':'Podobny opis — sprawdź, czy to ta sama sprawa'});
    }
    return results.sort((a,b)=>Number(faultIsActive(b.fault))-Number(faultIsActive(a.fault))||b.score-a.score||b.fault.date.localeCompare(a.fault.date));
}
function faultElementOptions(panelId,selected=''){
    const p=db.panels.find(p=>p.id===panelId);
    const choices=(p?.elements||[]).filter(e=>!e.archived||e.id===selected).map(e=>[e.id,[e.address,e.type,e.location,e.archived?'archiwum':''].filter(Boolean).join(' · ')]);
    if(selected&&!choices.some(([id])=>id===selected))choices.push([selected,'Zapisany element zgłoszenia']);
    return [['','Adres wpisany ręcznie / brak w słowniku'],...choices];
}
function refreshFaultDictionary(panelChanged=false){
    if(editor?.kind!=='fault')return;
    const panelId=$('f-panelId').value,selectElement=$('f-elementId');
    const previous=editor.record;
    const selected=panelChanged?'':selectElement.value;
    selectElement.innerHTML=options(faultElementOptions(panelId,selected),selected);
    if(panelChanged){
        selectElement.value='';$('f-elementAddress').value='';
        $('f-relatedFaultId').value='';$('f-relationType').value='';
    }
    const element=db.panels.find(p=>p.id===panelId)?.elements?.find(e=>e.id===selectElement.value);
    const address=$('f-elementAddress');address.readOnly=Boolean(selectElement.value);
    if(element)address.value=previous.elementId===element.id&&previous.panelId===panelId?previous.elementAddress:element.address;
    $('f-relatedFaultId').innerHTML=options([['','Brak'],...db.faults.filter(f=>f.panelId===panelId&&f.id!==previous.id).map(f=>[f.id,faultNumber(f)+' · '+f.desc.slice(0,70)])],panelChanged?'':$('f-relatedFaultId').value);
    refreshSimilarFaults();
}
function refreshSimilarFaults(){
    if(editor?.kind!=='fault'||!$('similar-faults'))return;
    const hits=similarFaults($('f-panelId').value,$('f-elementId').value,$('f-elementAddress').value,$('f-desc').value,editor.record.id);
    $('similar-faults').innerHTML=hits.length?`<h3>Sprawdź istniejące zgłoszenia (${hits.length})</h3><p class="hint">To podpowiedzi, które nie blokują zapisu. Sprawdź opis przed powiązaniem spraw. Otwieranie istniejącej sprawy odrzuca niezapisany formularz.</p>`+hits.slice(0,5).map(({fault:f,reason})=>`<div class="similar-fault"><div><strong>${esc(faultNumber(f))}</strong> ${badge(f.status,faultTone(f.status))}<span class="hint"> · ${esc(reason)}</span></div><p>${esc(f.desc.slice(0,180))}</p><details><summary>Podgląd szczegółów</summary>${details([['Data',f.date],['Zgłaszający',f.reporter],['Adres',f.elementAddress],['Odpowiedzialny',f.assignee],['Pełny opis',f.desc]])}</details><div class="actions">${button(faultIsActive(f)?'Powiąż jako duplikat':'Powiąż jako nawrót','link-similar',f.id,'small')}${button('Otwórz istniejące','open-similar',f.id,'small')}</div></div>`).join('')+(hits.length>5?'<p class="hint">Pokazano 5 najbardziej zbliżonych spraw.</p>':''):'<p class="hint">Brak podobnych zgłoszeń dla podanego adresu lub opisu.</p>';
}

function openPanel(id) {
    const p=db.panels.find(p=>p.id===id)||{id:'',model:'Polon 6000',location:'',spot:'',serialNo:'',intervalMonths:service.inspectionMonths,lastInspection:'',condition:'Niezweryfikowana',notes:''};
    modal('panel',id?'Edycja centrali':'Nowa centrala',`<div class="form-grid">${field('id','Kod centrali',p.id,'text',`required maxlength="120" ${id?'readonly':''}`)}${field('model','Model',p.model,'text','required')}${field('location','Budynek / lokalizacja',p.location,'text','required')}${field('spot','Dokładne miejsce',p.spot)}${field('serialNo','Numer seryjny',p.serialNo)}${field('intervalMonths','Interwał przeglądów (mies.)',p.intervalMonths,'number','required min="1" max="120"')}${field('lastInspection','Ostatni pozytywny przegląd',p.lastInspection.replace(' ','T'),'datetime-local')}${select('condition','Stan techniczny',Array.from(new Set(['Niezweryfikowana','Sprawna','Wymaga serwisu','W trakcie naprawy','Wyłączona',p.condition])),p.condition)}${field('coverage','Obsługiwany obszar',p.coverage)}${field('serviceContact','Kontakt do serwisu',p.serviceContact)}${field('notes','Uwagi techniczne',p.notes,'textarea','',true)}<div class="full"><label>Dodaj dokumenty (PDF, PNG, JPG, TXT; do 2 MB każdy)<input type="file" id="panel-documents" multiple accept=".pdf,.png,.jpg,.jpeg,.txt"></label><p class="hint">Maks. 20 dokumentów centrali; cała baza do 20 MB.</p>${(p.documents||[]).map(d=>`<label class="checkbox"><input type="checkbox" name="removeDoc_${esc(d.id)}">Usuń ${esc(d.name)}</label>`).join('')}</div></div>`,id?p:null);
}
function openFault(id,panelId='',source=null) {
    if(!activePanels().length&&!id){notice('Najpierw dodaj aktywną centralę.',true);return;}
    const f=db.faults.find(f=>f.id===id)||{id:uid('A'),date:localDateTime(),panelId:panelId||activePanels()[0]?.[0],reporter:'',desc:'',status:'Nowe',priority:'Normalny',assignee:'',dueDate:''};
    if(source){f.desc=source.desc;f.sourceProtocolId=source.id;}
    const panels=activePanels();if(!panels.some(([id])=>id===f.panelId))panels.push([f.panelId,panelName(f.panelId)]);
    modal('fault',id?'Edycja danych zgłoszenia '+faultNumber(f):'Nowe zgłoszenie',`<section class="form-section"><h3>Dane zgłoszenia</h3><div class="form-grid">${field('date','Data zgłoszenia',f.date.replace(' ','T'),'datetime-local','required')}${select('panelId','Centrala',panels,f.panelId,'required')}${field('reporter','Zgłaszający',f.reporter,'text','required')}${select('priority','Priorytet',['Niski','Normalny','Wysoki','Krytyczny'],f.priority)}</div></section><section class="form-section"><h3>Obsługa i identyfikacja usterki</h3><div class="form-grid">${field('assignee','Odpowiedzialny',f.assignee,'text','list="technicians"')}${field('dueDate','Planowany termin',f.dueDate,'date')}${field('occurredAt','Data wystąpienia usterki (jeśli znana)',(f.occurredAt||'').replace(' ','T'),'datetime-local')}${select('elementId','Element ze słownika',faultElementOptions(f.panelId,f.elementId||''),f.elementId||'')}${field('elementAddress','Adres elementu / pętla / strefa',f.elementAddress,'text','maxlength="200"')}${select('relatedFaultId','Powiązane zgłoszenie',[['','Brak'],...db.faults.filter(x=>x.id!==f.id&&x.panelId===f.panelId).map(x=>[x.id,faultNumber(x)+' · '+x.panelId+' · '+x.desc.slice(0,60)])],f.relatedFaultId||'')}${select('relationType','Rodzaj powiązania',['','Nawrót','Duplikat','Powiązane'],f.relationType||'')}${field('desc','Opis usterki',f.desc,'textarea','required',true)}</div></section><datalist id="technicians">${options(service.technicians,'')}</datalist><p class="hint">Status: ${esc(f.status)}. Zmianę statusu i przebieg prac zapisuj przez „Dodaj wpis / zmień status”, aby pozostały w historii.</p>`,id?f:{...f,_new:true});
    $('editor-fields').innerHTML+='<section id="similar-faults" class="similar-faults" aria-live="polite"></section>';
    refreshFaultDictionary();
}
function openFaultActivity(id) {
    const f=db.faults.find(f=>f.id===id);
    if(!f)return notice('Nie znaleziono zgłoszenia.',true);
    modal('fault-activity','Nowy wpis — '+faultNumber(f),`<div class="form-context">${badge(f.status,faultTone(f.status))}<span>${esc(panelName(f.panelId))} · ${esc(f.desc)}</span></div>
    <section class="form-section"><h3>Przebieg prac</h3><p class="hint">Wpis pozostanie w historii wraz z datą i kontem zapisującym. Opisz ustalenia przydatne kolejnemu serwisantowi.</p><div class="form-grid">
    ${field('author','Osoba wykonująca czynności',f.assignee||'','text','required maxlength="250" list="technicians"')}${select('status','Status po wykonaniu czynności',faultStatuses,f.status)}
    ${select('workStage','Etap prac',['','Diagnoza','Naprawa','Oczekiwanie na części','Oczekiwanie na serwis','Weryfikacja'],f.workStage||'')}
    ${field('text','Wykonane czynności / ustalenia / potrzebne części','','textarea','required maxlength="10000" placeholder="Np. Uszkodzona czujka OSD. Brak części — kolejna wizyta z nową czujką."',true)}</div></section>
    <section class="form-section" id="completion-section"><h3>Rozwiązanie zgłoszenia</h3><p class="hint" id="completion-hint"></p><div class="form-grid">
    ${field('cause','Przyczyna usterki',f.cause,'textarea','',true)}${field('resolution','Sposób usunięcia',f.resolution,'textarea','',true)}${field('verification','Wynik sprawdzenia działania',f.verification,'textarea','',true)}</div></section>
    <datalist id="technicians">${options(service.technicians,'')}</datalist><p class="hint">Ponowne otwarcie: wybierz „W realizacji” i opisz powód. Anulowanie również wymaga wpisu.</p>`,f,'<button type="submit" class="primary">Zapisz wpis w historii</button>');
    refreshCompletionFields();
}
function refreshCompletionFields(){
    if(editor?.kind!=='fault-activity')return;
    const completed=$('f-status').value==='Zakończone';
    $('completion-hint').textContent=completed?'Przed zakończeniem uzupełnij wszystkie trzy pola i potwierdź rzeczywisty wynik sprawdzenia.':'Możesz uzupełniać te dane w trakcie pracy. Będą wymagane przy zakończeniu zgłoszenia.';
    for(const name of ['cause','resolution','verification']){
        const input=$('f-'+name);input.required=completed;
        input.setAttribute('aria-required',String(completed));
    }
}

function openProtocol(id,panelId='',faultId='',inspection=false,sourceId='') {
    if(!activePanels().length){notice('Najpierw dodaj aktywną centralę.',true);return;}
    const old=db.history.find(h=>h.id===id);if(old&&old.protocolStatus!=='draft'){notice('Zatwierdzony dokument jest niezmienny.',true);return;}
    const source=db.history.find(h=>h.id===sourceId), fault=db.faults.find(f=>f.id===faultId);
    const h=old||{id:uid('PROT'),protocolStatus:'draft',protocolNo:'',date:localDateTime(),panelId:panelId||fault?.panelId||source?.panelId||activePanels()[0][0],type:inspection?'Przegląd':fault?'Naprawa':'Serwis',technician:'',recipient:'',scope:'',desc:source?'Uzupełnienie protokołu '+(source.protocolNo||source.id)+'. ':fault?'Obsługa zgłoszenia: '+fault.desc:'',recom:'',result:'',parts:'',hours:0,faultId:faultId||'',relatedProtocolId:source?.id||'',referenceProtocolNo:source?.protocolNo||'',closeFault:false,checklist:service.checklist.map(label=>({label,result:'',note:''}))};
    if(!old&&inspection){const plan=db.panels.find(p=>p.id===h.panelId);h.inspectionPlanId=plan?.inspectionPlanId||'';h.technician=plan?.inspectionPlanAssignee||'';}
    const linkedFaults=db.faults.filter(f=>faultIsActive(f)||f.id===h.faultId).map(f=>[f.id,faultNumber(f)+' · '+f.panelId+' · '+f.desc.slice(0,60)]);
    const html=`<p class="hint">Szkic można zapisać w trakcie pracy. Numer zostanie nadany przy zatwierdzeniu. Zatwierdzonego dokumentu nie można edytować.</p><div class="form-grid">${select('panelId','Centrala',activePanels(),h.panelId,'required')}${select('type','Rodzaj prac',['Przegląd','Naprawa','Serwis','Wymiana akumulatorów/podzespołów','Kontrola'],h.type)}${field('date','Data wykonania',h.date.replace(' ','T'),'datetime-local','required')}${field('technician','Wykonawca / technik',h.technician||h.contractor,'text','list="technicians"')}${field('recipient','Przedstawiciel obiektu / odbiorca',h.recipient)}${select('faultId','Powiązane zgłoszenie',[['','Bez zgłoszenia'],...linkedFaults],h.faultId)}${field('scope','Zakres prac / objęte elementy',h.scope,'textarea','',true)}</div><datalist id="technicians">${options(service.technicians,'')}</datalist><h3>Lista kontrolna</h3><p class="hint">Podaj rzeczywisty wynik i pomiary. „Nie dotyczy” oznacza wyłączenie danej czynności z zakresu.</p>${h.checklist.map((c,i)=>`<div class="check-row"><label for="check-${i}">${esc(c.label)}</label><select id="check-${i}" name="check-${i}" aria-label="Wynik: ${esc(c.label)}">${options([['','Nie oceniono'],'OK','Usterka','Nie dotyczy'],c.result)}</select><textarea name="note-${i}" aria-label="Pomiar i uwagi: ${esc(c.label)}" placeholder="Pomiar / uwagi">${esc(c.note)}</textarea></div>`).join('')}<div class="form-grid section-title">${select('result','Wynik końcowy',[['','Wybierz wynik'],'Pozytywny','Warunkowy','Negatywny'],h.result)}${field('hours','Czas pracy (godz.)',h.hours,'number','min="0" max="10000" step="0.25"')}${field('desc','Opis wykonanych prac i ustalenia',h.desc,'textarea','',true)}${field('recom','Zalecenia / ograniczenia / dalsze działania',h.recom,'textarea','',true)}${field('parts','Części i materiały — nazwa, ilość, parametry',h.parts,'textarea','',true)}</div><label class="checkbox"><input type="checkbox" name="closeFault" ${h.closeFault?'checked':''}>Zamknij powiązane zgłoszenie po pozytywnym zatwierdzeniu</label>`;
    modal('protocol',old?'Edycja protokołu roboczego':'Nowy protokół',html,h,'<button type="submit" name="intent" value="draft">Zapisz szkic</button><button type="submit" name="intent" value="final" class="primary">Zatwierdź protokół</button>');
}
async function saveEditor(event) {
    event.preventDefault();if(busy)return;
    const form=event.currentTarget;if(!form.reportValidity())return;
    const values=Object.fromEntries(new FormData(form)), kind=editor.kind, old=editor.record;
    const candidate=clone(db);
    const controls=[...form.querySelectorAll("button,input,select,textarea")].map(control=>[control,control.disabled]);
    busy=true;controls.forEach(([control])=>control.disabled=true);
    try {
        if(kind==='user'||kind==='user-reset') {
            const data=kind==='user-reset'?{action:'reset-password',id:old.id,password:values.password}:
              {action:old?'update':'create',...(old?{id:old.id}:{}),username:old?.username||values.username,
                displayName:values.displayName,role:values.role,enabled:values.enabled==='yes',
                ...(old?{}:{password:values.password}),permissions:Object.keys(availablePermissions).filter(k=>values['perm_'+k]==='on')};
            if(kind==='user'&&data.role==='ADMIN')data.permissions=Object.keys(availablePermissions);
            await api('/api/users','POST',data);busy=false;closeModal(true);await renderUsers();notice('Zapisano zmiany konta.');return;
        }
        if(kind==='element') {
            const p=candidate.panels.find(p=>p.id===old.panelId);
            const element={...old.element,...values};
            for(const key of ['address','type','location','notes'])element[key]=element[key].trim();
            p.elements??=[];
            if(old.isNew)p.elements.push(element);else p.elements[p.elements.findIndex(e=>e.id===element.id)]=element;
        } else if(kind==='cost') {
            const reversing=old?.amountGrosz>0;
            const record={id:uid('COST'),protocolId:reversing?old.protocolId:values.protocolId,
                date:values.date,category:reversing?old.category:values.category,
                description:values.description.trim(),reference:values.reference.trim(),
                amountGrosz:reversing?-old.amountGrosz:parseMoneyGrosz(values.amount),reversesId:reversing?old.id:''};
            candidate.costs??=[];candidate.costs.push(record);
        } else if(kind==='inspection-plan') {
            const p=candidate.panels.find(p=>p.id===old.id);
            if(values.cancelPlan==='on')for(const k of ['inspectionPlanDate','inspectionPlanAssignee','inspectionPlanNote','inspectionPlanId'])p[k]='';
            else {
                if(!values.inspectionPlanDate)throw new Error('Wybierz datę wizyty lub zaznacz odwołanie planu.');
                for(const k of ['inspectionPlanDate','inspectionPlanAssignee','inspectionPlanNote'])p[k]=values[k].trim();
            }
        } else if(kind==='panel') {
            values.id=values.id.trim();values.intervalMonths=Number(values.intervalMonths);values.lastInspection=values.lastInspection.replace('T',' ');
            if(!values.id)throw new Error('Podaj kod centrali.');
            if(!old&&candidate.panels.some(p=>p.id.toLocaleLowerCase()===values.id.toLocaleLowerCase()))throw new Error('Centrala o takim kodzie już istnieje.');
            const record={...(old||{}),...values,archived:old?.archived||false};
            busy=true;
            record.documents=(old?.documents||[]).filter(d=>values['removeDoc_'+d.id]!=='on');
            for(const key of Object.keys(record))if(key.startsWith('removeDoc_'))delete record[key];
            for(const file of $('panel-documents').files){
                if(file.size===0||file.size>2*1024*1024)throw new Error('Dokument musi mieć 1 bajt–2 MB.');
                if(!/\.(pdf|png|jpe?g|txt)$/i.test(file.name))throw new Error('Dozwolone dokumenty: PDF, PNG, JPG, TXT.');
                const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Nie można odczytać dokumentu.'));reader.readAsDataURL(file);});
                record.documents.push({id:uid('DOC'),name:file.name,data});
            }
            if(record.documents.length>20)throw new Error('Maksymalnie 20 dokumentów centrali.');
            if(old)candidate.panels[candidate.panels.findIndex(p=>p.id===old.id)]=record;else candidate.panels.push(record);
        } else if(kind==='fault') {
            const record={...old,...values,date:values.date.replace('T',' '),occurredAt:values.occurredAt.replace('T',' ')};delete record._new;
            if(old._new)candidate.faults.push(record);else candidate.faults[candidate.faults.findIndex(f=>f.id===old.id)]=record;
        } else if(kind==='fault-activity') {
            const f=candidate.faults.find(f=>f.id===old.id);
            if(!f)throw new Error('Nie znaleziono zgłoszenia.');
            const author=values.author.trim(), text=values.text.trim();
            if(!author||!text)throw new Error('Podaj serwisanta i opis czynności.');
            f.status=values.status;
            for(const key of ['cause','resolution','verification','workStage'])f[key]=values[key].trim();
            f.timeline??=[];
            f.timeline.push({id:uid('LOG'),type:'action',author,text,at:''});
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

        if(kind==='settings') {
            const numbering={};
            for(const key of ['fault','inspection','protocol']) {
                numbering[key]={prefix:values['num_'+key+'_prefix'].trim(),start:Number(values['num_'+key+'_start']),digits:Number(values['num_'+key+'_digits']),annual:values['num_'+key+'_annual']==='yes'};
                for(const part of ['prefix','start','digits','annual'])delete values['num_'+key+'_'+part];
            }
            const updated={...service,...values,numbering,protocolPrefix:numbering.protocol.prefix,inspectionMonths:Number(values.inspectionMonths),reminderDays:Number(values.reminderDays),technicians:values.technicians.split('\n').map(s=>s.trim()).filter(Boolean),checklist:values.checklist.split('\n').map(s=>s.trim()).filter(Boolean)};
            const result=await api('/api/config','PUT',{revision:configRevision,service:updated,token:lockToken});service=result.service;configRevision=result.revision;
        } else await persist(candidate);
        if(kind==='fault'&&old._new || kind==='fault-activity') { route='faults'; selectedFault=old.id; filters={}; }
        busy=false;closeModal(true);render();notice(kind==='protocol'&&event.submitter?.value==='final'?'Protokół zatwierdzony. Dokument jest dostępny w historii.':kind==='fault-activity'?'Dodano wpis do historii zgłoszenia.':'Zapisano zmiany na dysku.');
    } catch(e) { $('form-error').textContent=e.message;$('form-error').focus(); }
    finally {busy=false;controls.forEach(([control,disabled])=>control.disabled=disabled);}
}
function download(data,filename) {
    const blob=new Blob([typeof data==='string'?data:JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function importFile(file) {
    if(currentUser?.role!=='ADMIN')throw new Error('Import bazy jest dostępny tylko dla administratora.');
    if(!file)return;
    await acquireLock('import');
    try {
    if(file.size>20*1024*1024)throw new Error('Limit importu wynosi 20 MB.');
    const bytes=new Uint8Array(await new Promise((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(reader.result);
        reader.onerror=()=>reject(new Error('Windows nie pozwala odczytać wybranego pliku. Skopiuj go do folderu lokalnego i wybierz ponownie.'));
        reader.onabort=()=>reject(new Error('Anulowano odczyt pliku.'));
        reader.readAsArrayBuffer(file);
    }));
    const encoding=bytes[0]===255&&bytes[1]===254?'utf-16le':bytes[0]===254&&bytes[1]===255?'utf-16be':'utf-8';
    let imported;
    if(file.name.toLowerCase().endsWith('.cfdb')) {
        const chunk=0x8000;let binary='';
        for(let i=0;i<bytes.length;i+=chunk)binary+=String.fromCharCode(...bytes.subarray(i,i+chunk));
        const result=await api('/api/import-cfdb-decode','POST',{file:btoa(binary)});
        imported=result.database;
    } else {
        imported=JSON.parse(new TextDecoder(encoding).decode(bytes));
    }
    if(!['panels','faults','history'].every(k=>Array.isArray(imported[k])))throw new Error('Plik nie jest bazą SSP.');
    const preview=await api('/api/import-preview','POST',{database:imported});
    const q=preview.summary;
    if(!confirm(`Plik: ${file.name}\nWersja danych: ${q.schemaVersion}; dokumenty: ${q.documents}; elementy słownika: ${q.elements||0}; wpisy kosztów: ${q.costs||0} (obecnie: ${preview.current.costs||0})\nOstatni wpis: ${q.lastEvent||'brak'}\nKonta i konfiguracja bieżącej instalacji pozostaną zachowane.\nZastąpić całą obecną bazę? Import: ${imported.panels.length} central, ${imported.faults.length} zgłoszeń, ${imported.history.length} wpisów. Przed importem powstanie kopia obecnej bazy.`))return;
    await persist(imported,'replace');render();notice('Baza zaimportowana. Dotychczasowe dane zachowano w kopii zapasowej.');
    } finally { await releaseLock(); }
}
async function action(event) {
    const target=event.target.closest('[data-action]');if(!target||busy)return;
    const {action,id}=target.dataset;
    try {
        if(['export','backup','import','download-backup'].includes(action) && currentUser?.role!=='ADMIN')
            throw new Error('Operacje na bazie danych są dostępne tylko dla administratora.');
        if(actionPermission[action]&&!can(actionPermission[action]))throw new Error('Brak uprawnienia do tej operacji.');
        if(action==='reset-view')return resetCurrentView();
        if(action==='new-element')return await lockedEditor('panels/'+id,()=>openElement(id));
        if(action==='edit-element'){const ref=JSON.parse(id);return await lockedEditor('panels/'+ref.panelId,()=>openElement(ref.panelId,ref.id));}
        if(action==='archive-element'){
            if(!can('panels.edit'))throw new Error('Brak uprawnienia do edycji słownika.');
            const ref=JSON.parse(id);await acquireLock('panels/'+ref.panelId);
            try{busy=true;const candidate=clone(db),p=candidate.panels.find(p=>p.id===ref.panelId),e=p.elements.find(e=>e.id===ref.id);e.archived=!e.archived;await persist(candidate);render();notice('Zmieniono stan elementu.');}finally{busy=false;await releaseLock();}return;
        }
        if(action==='link-similar'){
            if(editor?.kind!=='fault'||!can('faults.edit'))return;
            const f=db.faults.find(f=>f.id===id);if(!f||f.panelId!==$('f-panelId').value)throw new Error('Niewłaściwa centrala.');
            $('f-relatedFaultId').value=id;$('f-relationType').value=faultIsActive(f)?'Duplikat':'Nawrót';dirty=true;return;
        }
        if(action==='open-similar'){
            if(!can('faults.view'))return;
            if(dirty&&!confirm('Odrzucić niezapisany formularz i otworzyć istniejące zgłoszenie?'))return;
            closeModal(true);route='faults';selectedFault=id;selectedPanel='';selectedProtocol='';render();return;
        }

        if(action==='search-back'){
            const saved=searchReturnState;searchReturnState=null;route='search';filters=saved||{};selectedPanel='';selectedFault='';selectedProtocol='';return render();
        }
        if(action==='search-open'){
            const ref=JSON.parse(id),permission={panel:'panels.view',fault:'faults.view',protocol:'protocols.view',cost:'protocols.view'}[ref.kind];
            if(!permission||!can(permission))throw new Error('Brak dostępu do rekordu.');
            searchReturnState=clone(filters);filters={};selectedPanel='';selectedFault='';selectedProtocol='';
            if(ref.kind==='panel'){route='panels';selectedPanel=ref.id;}
            else if(ref.kind==='fault'){route='faults';selectedFault=ref.id;}
            else {route='protocols';selectedProtocol=ref.kind==='cost'?(db.costs||[]).find(c=>c.id===ref.id)?.protocolId:ref.id;}
            return render();
        }
        if(action==='new-cost')return openCost(id);
        if(action==='reverse-cost')return openCost('',id);
        if(action==='print-monthly'){$('print-area').innerHTML=monthlyHTML(true);return window.print();}
        if(action==='monthly-csv')return exportMonthlyCSV();
        if(action==='costs-csv')return exportCostsCSV();
        if(action==='plan-inspection')return await lockedEditor('panels/'+id,()=>openInspectionPlan(id));
        if(action==='print-schedule'){$('print-area').innerHTML='<article class="protocol-preview"><h1>Plan przeglądów SSP</h1><p>'+esc(filters.month||'Wszystkie miesiące')+' · Stan na '+esc(today())+'</p>'+scheduleTable(scheduleRows(),true)+'</article>';return window.print();}
        if(action==='print-panel'){const card=$('content').cloneNode(true);card.querySelectorAll('button').forEach(b=>b.replaceWith(document.createTextNode(b.textContent)));$('print-area').innerHTML=card.innerHTML;return window.print();}
        if(action==='print-fault'){$('print-area').innerHTML=faultPrintHTML(db.faults.find(f=>f.id===id));return window.print();}
        if(action==='print-report'){$('print-area').innerHTML=reportHTML();return window.print();}
        if(action==='report-csv')return exportReportCSV();
        if(action==='document-download'){
            const [panelId,docId]=id.split('|');const doc=db.panels.find(p=>p.id===panelId)?.documents?.find(d=>d.id===docId);
            if(!doc)throw new Error('Nie znaleziono dokumentu.');
            const bytes=Uint8Array.from(atob(doc.data),c=>c.charCodeAt(0));
            const url=URL.createObjectURL(new Blob([bytes],{type:'application/octet-stream'})),a=document.createElement('a');a.href=url;a.download=doc.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;
        }
        if(action==='fault-from-check'){
            const [protocolId,index]=id.split('|'),h=db.history.find(h=>h.id===protocolId),check=h?.checklist?.[Number(index)];
            if(!h||check?.result!=='Usterka')throw new Error('Nie znaleziono usterki.');
            const existing=db.faults.find(f=>f.sourceProtocolId===h.id&&f.desc===check.label+' — '+check.note);
            if(existing){route='faults';selectedFault=existing.id;return render();}
            return openFault('',h.panelId,{id:h.id,desc:check.label+' — '+check.note});
        }
        if(action==='sort-table') {
            const element=target.closest('table'),column=Number(target.dataset.column);
            const key=element.dataset.sortKey,previous=tableSortState.get(key);
            const direction=previous?.column===column&&previous.direction==='ascending'?'descending':'ascending';
            tableSortState.set(key,{column,direction});saveViewPreferences();
            sortTableElement(element,column,direction);
            return;
        }
        if(action==='navigate')return navigate(id);
        if(action==='logout')return await logout();
        if(action==='show-alerts')return toggleSyncFeed();
        if(action==='new-user')return openUser('');
        if(action==='edit-user')return openUser(id);
        if(action==='reset-user')return openUserReset(id);
        if(action==='new-panel')return openPanel('');
        if(action==='edit-panel')return await lockedEditor('panels/'+id,()=>openPanel(id));
        if(action==='panel-card'){route='panels';selectedPanel=id;return render();}
        if(action==='new-fault')return openFault('',id);
        if(action==='edit-fault')return await lockedEditor('faults/'+id,()=>openFault(id));
        if(action==='view-fault'){route='faults';selectedFault=id;return render();}
        if(action==='log-fault')return await lockedEditor('faults/'+id,()=>openFaultActivity(id));
        if(action==='new-inspection')return await lockedEditor('panels/'+id,()=>openProtocol('',id,'',true));
        if(action==='new-protocol')return openProtocol('',id);
        if(action==='service-fault')return await lockedEditor('faults/'+id,()=>openProtocol('','',id));
        if(action==='followup-protocol')return await lockedEditor('panels/'+db.history.find(h=>h.id===id).panelId,()=>openProtocol('','','',false,id));
        if(action==='edit-protocol')return await lockedEditor('history/'+id,()=>openProtocol(id));
        if(action==='delete-draft') {
            const h=db.history.find(h=>h.id===id);
            if(!h||h.protocolStatus!=='draft')throw new Error('Można usunąć wyłącznie szkic.');
            if(!confirm('Usunąć niezatwierdzony szkic? Poprzednia wersja bazy pozostanie w kopii.'))return;
            await acquireLock('history/'+id);
            try {busy=true;const candidate=clone(db);candidate.history=candidate.history.filter(h=>h.id!==id);
            await persist(candidate);selectedProtocol='';render();notice('Usunięto szkic.');}
            finally {await releaseLock();}
        }
        if(action==='view-protocol'){route='protocols';selectedProtocol=id;return render();}
        if(action==='print-protocol'){const h=db.history.find(h=>h.id===id);$('print-area').innerHTML=documentHTML(h);return window.print();}
        if(action==='edit-settings')return await lockedEditor('settings',()=>modal('settings','Konfiguracja firmy i serwisu',settingsFields(service)));
        if(action==='close-modal')return closeModal();
        if(action==='refresh') {if($('editor').open||activeLock)throw new Error('Najpierw zakończ edycję.');await refreshDatabase();setSyncStatus('● Odświeżono ręcznie');return render();}
        if(action==='export'){const exported=clone(db);delete exported.activeSessions;return download(exported,`CommandFIRE-SSP-baza-${today()}.json`);}
        if(action==='import')return $('import-file').click();
        if(action==='archive-panel') {
            const p=db.panels.find(p=>p.id===id);
            if(!p.archived&&(db.faults.some(f=>f.panelId===id&&faultIsActive(f))||db.history.some(h=>h.panelId===id&&h.protocolStatus==='draft')))throw new Error('Najpierw zamknij zgłoszenia i zakończ protokoły robocze tej centrali.');
            if(!confirm(p.archived?'Przywrócić centralę do ewidencji?':'Archiwizować centralę? Jej historia pozostanie dostępna.'))return;
            await acquireLock('panels/'+id);
            try {busy=true;const candidate=clone(db);candidate.panels.find(p=>p.id===id).archived=!p.archived;await persist(candidate);render();notice('Zmieniono status ewidencji.');}
            finally {await releaseLock();}
        }
        if(action==='backup'){busy=true;const result=await api('/api/backup','POST');if(route==='backups')render();notice(result.name?'Utworzono kopię: '+result.name:'Baza jest pusta i nie ma jeszcze pliku do skopiowania.');}
        if(action==='download-backup'){
            busy=true;const response=await fetch('/api/backups/'+encodeURIComponent(id),{headers:{'X-SSP-Client':'local','X-SSP-Session':authToken},signal:AbortSignal.timeout(20000)});
            if(!response.ok)throw new Error('Nie można pobrać kopii.');
            const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=id;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        }
    } catch(e){notice(e.message,true);} finally {busy=false;}
}
window.addEventListener('focus',()=>{if(document.visibilityState==='visible')void pollSynchronization();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)void pollSynchronization();});
$('auth-form').addEventListener('submit',authenticateUser);
$('editor-form').addEventListener('change',e=>{
 if(editor?.kind==='fault-activity'&&e.target.name==='status')refreshCompletionFields();
 if(editor?.kind==='fault'&&e.target.name==='panelId')refreshFaultDictionary(true);
 else if(editor?.kind==='fault'&&e.target.name==='elementId')refreshFaultDictionary();
 if(e.target.name==='role'&&editor?.kind==='user'){
  const defaults=roleDefaults[e.target.value]||[];
  document.querySelectorAll('#editor-fields [data-permission]').forEach(input=>{
   input.checked=defaults.includes(input.dataset.permission);input.disabled=e.target.value==='ADMIN';
  });
 }
});
document.addEventListener('keydown',event=>{
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'&&!event.altKey&&!$('editor').open&&!busy&&currentUser&&canRoute('search')){
        event.preventDefault();if(route!=='search')navigate('search');$('search')?.focus();
    }
});
document.addEventListener('click',action);
$('editor-form').addEventListener('submit',saveEditor);
$('editor-form').addEventListener('input',event=>{dirty=true;void touchLock();if(editor?.kind==='fault'&&['desc','elementAddress'].includes(event.target.name))refreshSimilarFaults();});
$('editor-form').addEventListener('change',()=>{dirty=true;void touchLock();});
$('editor').addEventListener('cancel',e=>{e.preventDefault();closeModal();});
window.addEventListener('beforeunload',e=>{if(dirty||busy){e.preventDefault();e.returnValue='';}});
window.addEventListener('pagehide',()=>{
    if(activeLock)fetch('/api/lock',{method:'POST',headers:{'X-SSP-Client':'local','X-SSP-Session':authToken,'Content-Type':'application/json'},
        body:JSON.stringify({action:'release',resource:activeLock,token:lockToken}),keepalive:true}).catch(()=>{});
});
$('content').addEventListener('input',event=>{
    const id=event.target.id;if(id!=='search')return;
    const position=event.target.selectionStart;filters.search=event.target.value;rememberViewFilters();render();$('search').focus();$('search').setSelectionRange(position,position);
});
$('content').addEventListener('change',event=>{const id=event.target.id;if(id==='filter')filters.status=event.target.value;else if(id==='date-from')filters.from=event.target.value;else if(id==='date-to')filters.to=event.target.value;else if(id==='schedule-month'||id==='report-month')filters.month=event.target.value;else if(id==='report-panel')filters.panel=event.target.value;else if(id==='plan-filter')filters.plan=event.target.value;else if(id==='fault-attention')filters.attention=event.target.value;else if(id==='fault-stage')filters.stage=event.target.value;else if(id==='fault-assignee')filters.assignee=event.target.value;else if(id==='search-kind')filters.kind=event.target.value;else return;rememberViewFilters();render();});
$('import-file').addEventListener('change',async event=>{try{if(busy)return;busy=true;await importFile(event.target.files[0]);}catch(e){notice('Import nie powiódł się: '+e.message,true);}finally{busy=false;event.target.value='';}});
async function loadApplication() {
    const [data,config]=await Promise.all([api('/api/database'),api('/api/config')]);
    db=data.database||{panels:[],faults:[],history:[],schemaVersion:3,audit:[]};dbRevision=data.revision;
    service=config.service;configRevision=config.revision;version=config.version;databaseName=config.database;
    loadViewPreferences();filters=restoredViewFilters(route);showApplication();render();startSynchronization();
    $('storage-status').textContent=`CommandFIRE SSP Serwis ${version} · ${databaseName} · Wspólna baza JSON · Zalogowany: ${currentUser.displayName}`;
}
async function init() {
    try {
        const setup=await api('/api/auth/setup');
        if(setup.needsAdmin){showAuth('Nie ma jeszcze administratora. Na jednym stanowisku uruchom Utworz_pierwszego_admina.bat, a następnie zaloguj się.');return;}
        if(authToken){
            try {const me=await api('/api/auth/me');currentUser=me.user;
                 availablePermissions=me.permissions;roleDefaults=me.roles;
                 if(currentUser.mustChangePassword){showAuth('',true);return;}
                 await loadApplication();return;}
            catch(e){authToken='';sessionStorage.removeItem('ssp-auth');}
        }
        showAuth();
    }catch(e){showAuth('Nie udało się połączyć z serwerem lub wspólną bazą: '+e.message);}
}
init();
