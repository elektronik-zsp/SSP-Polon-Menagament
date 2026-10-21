const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',open:false,files:[],classList:{add(){},remove(){}},addEventListener(){},setAttribute(){},showModal(){this.open=true;},close(){this.open=false;},querySelectorAll(){return[];}});return elements.get(id);};
const sandbox={console,crypto,structuredClone,Intl,Date,Blob,URL,AbortSignal,TextDecoder,Uint8Array,setTimeout,clearTimeout,setInterval,clearInterval,
 sessionStorage:{getItem(){return''},setItem(){},removeItem(){}},
 document:{getElementById:element,createElement(){return {innerHTML:'',content:{querySelector(){return null;}}};},addEventListener(){},querySelectorAll(){return[];}},window:{addEventListener(){}},confirm:()=>true};
vm.createContext(sandbox);let code=fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8').replace(/init\(\);\s*$/,'');vm.runInContext(code,sandbox);
vm.runInContext(`
service={inspectionMonths:3,reminderDays:30,checklist:['Kontrola'],technicians:[],numbering:{},company:'Jednostka',site:'Obiekt'};
currentUser={role:'ADMIN',displayName:'Administrator',permissions:['panels.view','panels.edit','faults.view','faults.edit','protocols.view','protocols.edit','backups.manage']};
db={panels:[{id:'C01',model:'Polon',location:'A',spot:'',serialNo:'',lastInspection:'',condition:'Sprawna',intervalMonths:3,documents:[{id:'D1',name:'instrukcja.txt',data:'VGVzdA=='}]}],faults:[{id:'F1',number:'ZG/2026/0001',panelId:'C01',date:'2026-10-20 12:00',desc:'Usterka',reporter:'Jan',status:'Nowe',priority:'Normalny',timeline:[]}],history:[{id:'H1',panelId:'C01',protocolStatus:'draft',date:'2026-10-20',type:'Przegląd',desc:'Kontrola',checklist:[{label:'Czujka',result:'Usterka',note:'Brak odpowiedzi'}]}]};
renderPanelCard('C01');if(!$('content').innerHTML.includes('instrukcja.txt'))throw Error('Brak dokumentacji');
openPanel('C01');if(!$('editor-fields').innerHTML.includes('serviceContact'))throw Error('Brak kontaktu');
openFault('F1');if(!$('editor-fields').innerHTML.includes('relatedFaultId'))throw Error('Brak powiązań');
openFaultActivity('F1');if(!$('editor-fields').innerHTML.includes('Oczekiwanie na części'))throw Error('Brak etapu');
renderFaultDetail('F1');if(!$('content').innerHTML.includes('Powiązania i nawroty'))throw Error('Brak powiązań w widoku');
renderProtocolView('H1');if(!$('content').innerHTML.includes('fault-from-check'))throw Error('Brak utworzenia zgłoszenia');
if(!reportHTML().includes('Raport prac SSP'))throw Error('Brak raportu');
if(!faultPrintHTML(db.faults[0]).includes('ZG/2026/0001'))throw Error('Brak wydruku');
filters.search='VGVzdA';if(matches(db.panels[0]))throw Error('Wyszukiwanie przeszukuje dane binarne');
filters.search='instrukcja';if(!matches(db.panels[0]))throw Error('Brak wyszukiwania nazw dokumentów');
`,sandbox);
vm.runInContext(`
filters={};db.panels[0].inspectionPlanDate='2026-11-10';db.panels[0].inspectionPlanAssignee='Jan';
db.panels[0].lastInspection='2026-01-31';
if(nextDate(db.panels[0])!=='2026-04-30')throw Error('Niepoprawna data końca miesiąca');
renderSchedule();if(!$('content').innerHTML.includes('Plan przeglądów'))throw Error('Brak planu');
filters.month='2026-11';if(scheduleRows().length!==1)throw Error('Brak filtrowania wizyt');
filters.month='2026-04';if(scheduleRows().length!==0)throw Error('Wizyta nie przesłania technicznego terminu w filtrze miesiąca');
filters={};openInspectionPlan('C01');if(!$('editor-fields').innerHTML.includes('cancelPlan'))throw Error('Brak odwołania planu');
openProtocol('','C01','',true);if(editor.record.technician!=='Jan')throw Error('Nie przeniesiono wykonawcy');
filters.attention='unassigned';if(filteredFaults().length!==1)throw Error('Brak filtra bez przypisania');
db.faults[0].assignee='Jan';if(filteredFaults().length!==0)throw Error('Filtr bez przypisania jest niepoprawny');
filters={stage:'Oczekiwanie na części'};if(filteredFaults().length!==0)throw Error('Filtr etapu jest niepoprawny');
db.faults[0].workStage='Oczekiwanie na części';if(filteredFaults().length!==1)throw Error('Filtr etapu nie znalazł sprawy');
filters={};selectedFault='';renderFaults();if(!$('content').innerHTML.includes('fault-attention'))throw Error('Brak kontrolek filtrów');
`,sandbox);
vm.runInContext(`
if(parseMoneyGrosz('0,10')+parseMoneyGrosz('0.20')!==30)throw Error('Niedokładne grosze');
if(parseMoneyGrosz('100000000,00')!==10000000000)throw Error('Błędny limit kwoty');
for(const value of ['1,001','1e3','-5','0','NaN','100000000,01']){let rejected=false;try{parseMoneyGrosz(value);}catch(e){rejected=true;}if(!rejected)throw Error('Zaakceptowano złą kwotę: '+value);}
filters={month:'2026-10'};
db.panels=[{id:'C01',location:'A'}];
db.history=[{id:'H1',panelId:'C01',date:'2026-10-01',protocolStatus:'final',type:'Przegląd',hours:1.5},
{id:'H2',panelId:'C01',date:'2026-10-02',protocolStatus:'final',type:'Naprawa',hours:2},
{id:'DRAFT',panelId:'C01',date:'2026-10-03',protocolStatus:'draft',hours:100}];
db.faults=[{id:'F1',number:'ZG/1',date:'2026-09-01',panelId:'C01',elementAddress:'Pętla 1 / 42',status:'Zakończone'},
{id:'F2',number:'ZG/2',date:'2026-10-01',panelId:'C01',elementAddress:' pĘTLA   1 / 42 ',status:'Nowe',relationType:'Nawrót',relatedFaultId:'F1'},
{id:'F3',date:'2026-10-02',panelId:'C01',elementAddress:'Pętla 1 / 42',status:'Nowe',relationType:'Duplikat',relatedFaultId:'F2'}];
db.costs=[{id:'K1',protocolId:'H1',date:'2026-10-01',category:'Części',amountGrosz:12345,description:'Czujka'},
{id:'R1',protocolId:'H1',date:'2026-11-01',category:'Części',amountGrosz:-12345,reversesId:'K1',description:'Korekta'},
{id:'K2',protocolId:'H1',date:'2026-11-01',category:'Części',amountGrosz:22345,description:'Nowa kwota',reference:'\\t=CMD()'}];
const oct=monthlyData();if(oct.history.length!==2||oct.hours!==3.5||oct.totalGrosz!==12345||oct.withoutCost!==1)throw Error('Błędne zestawienie miesięczne');
if(oct.confirmed.length!==1||oct.repeated.length!==1||oct.repeated[0].rows.length!==2)throw Error('Błędna analiza nawrotów');
filters.month='2026-11';if(monthlyData().totalGrosz!==10000)throw Error('Korekta w złym miesiącu');
filters.month='';if(monthlyData().totalGrosz!==22345)throw Error('Błędna suma historii');
renderReports();if(!$('content').innerHTML.includes('Raporty i koszty'))throw Error('Brak nowego widoku');
openCost('H1');if(!$('editor-fields').innerHTML.includes('Kwota brutto PLN'))throw Error('Brak formularza kwoty');
openCost('','K2');if(!$('editor-fields').innerHTML.includes('Powód korekty'))throw Error('Brak formularza korekty');
let rejected=false;try{openCost('','K1')}catch(e){rejected=true;}if(!rejected)throw Error('Pozwolono na podwójną korektę');
const originalCreate=document.createElement;document.createElement=(tag)=>tag==='a'?{click(){}}:originalCreate(tag);
URL.createObjectURL=blob=>{globalThis.testCsvBlob=blob;return 'blob:test'};URL.revokeObjectURL=()=>{};
filters.month='2026-11';exportCostsCSV();
`,sandbox);
vm.runInContext(`
currentUser.permissions=['panels.view','faults.view','protocols.view'];
db.panels[0].notes='Łączność bezprzewodowa';db.panels[0].documents=[{name:'Instrukcja_Polon.pdf',data:'SEKRET_BINARNY'}];
db.faults[1].number='ZG/2026/0042';db.faults[1].reporter='Żaneta Łącka';
db.faults[1].timeline=[{author:'Serwisant',text:'Wymieniono podstawę czujki'}];
db.history[0].protocolNo='SSP/2026/0001';
if(systemSearch('ZG/2026/0042')[0]?.id!=='F2')throw Error('Numer sprawy nie jest pierwszym wynikiem');
if(systemSearch('zaneta lacka','fault').length!==1)throw Error('Wyszukiwanie bez polskich znaków nie działa');
if(systemSearch('podstawe czujki','fault').length!==1)throw Error('Nie przeszukano historii czynności');
if(systemSearch('instrukcja_polon').length!==1)throw Error('Nie przeszukano nazw dokumentów');
if(systemSearch('SEKRET_BINARNY').length!==0)throw Error('Przeszukano dane binarne załącznika');
if(systemSearch('z').length!==0)throw Error('Za krótka fraza wyszukiwania');
if(systemSearch('zaneta brakujace').length!==0)throw Error('Nie zadziałał warunek wszystkich słów');
if(systemSearch('SSP/2026/0001','protocol').length!==1)throw Error('Nie zadziałał filtr rodzaju');
currentUser.permissions=['panels.view'];
if(!canRoute('search')||systemSearch('ZG/2026/0042').length!==0)throw Error('Wyniki naruszają uprawnienia');
if(button('Sprawa','view-fault','F2')!=='')throw Error('Link do niedostępnej sprawy jest widoczny');
currentUser.permissions=[];if(canRoute('search'))throw Error('Wyszukiwarka dostępna bez podglądu danych');
currentUser.permissions=['panels.view','faults.view','protocols.view'];
filters={search:'zaneta',kind:'fault'};renderGlobalSearch();
if(!$('content').innerHTML.includes('ZG/2026/0042'))throw Error('Brak wyniku w tabeli');
db.faults[1].desc='<img src=x onerror=alert(1)>';filters.search='onerror';renderGlobalSearch();
if($('content').innerHTML.includes('<img src=x'))throw Error('Niezabezpieczony HTML w wynikach');
route='search';busy=false;
void action({target:{closest:()=>({dataset:{action:'search-open',id:JSON.stringify({kind:'fault',id:'F2'})}})}});
if(route!=='faults'||selectedFault!=='F2'||!searchReturnState)throw Error('Nie otwarto wyniku');
void action({target:{closest:()=>({dataset:{action:'search-back'}})}});
if(route!=='search'||filters.search!=='onerror'||searchReturnState!==null)throw Error('Nie przywrócono wyszukiwania');

`,sandbox);
vm.runInContext(`
currentUser.permissions=['panels.view','panels.edit','faults.view','faults.edit','protocols.view'];
db.panels=[{id:'C01',location:'A',elements:[{id:'E1',address:'P1/42',type:'Czujka',location:'Hala',archived:false},{id:'E2',address:'P1/43',archived:true}]}];
db.faults=[{id:'A',number:'ZG/A',panelId:'C01',elementId:'E1',elementAddress:'P1/42',desc:'Brak odpowiedzi czujki w hali',status:'Nowe',date:'2026-10-20'},
{id:'B',number:'ZG/B',panelId:'C01',elementId:'E1',elementAddress:'P1/42',desc:'Brak odpowiedzi czujki w hali',status:'Zakończone',date:'2026-10-19'},
{id:'C',panelId:'C02',elementId:'E1',elementAddress:'P1/42',desc:'Brak odpowiedzi czujki w hali',status:'Nowe',date:'2026-10-20'},
{id:'D',panelId:'C01',elementAddress:'P1/42',desc:'Brak odpowiedzi czujki w hali',status:'Anulowane',date:'2026-10-20'},
{id:'E',panelId:'C01',elementAddress:'P1/42',desc:'Brak odpowiedzi czujki w hali',relationType:'Duplikat',status:'Nowe',date:'2026-10-20'}];
let suggestions=similarFaults('C01','E1','P1/42','');
if(suggestions.length!==2||suggestions[0].fault.id!=='A')throw Error('Błędna kolejność lub zakres podobnych zgłoszeń');
if(similarFaults('C01','','p1/42','').length!==2)throw Error('Brak dopasowania adresu');
if(similarFaults('C01','','','Brak odpowiedzi czujki na hali').length!==2)throw Error('Brak podobieństwa opisu');
if(similarFaults('C01','E1','','','A').some(x=>x.fault.id==='A'))throw Error('Podpowiadanie własnego zgłoszenia');
if(similarFaults('C01','','','').length!==0)throw Error('Podpowiedzi bez danych wejściowych');
currentUser.permissions=[];if(similarFaults('C01','E1','','').length)throw Error('Podpowiedzi bez podglądu zgłoszeń');
currentUser.permissions=['panels.view','panels.edit','faults.view','faults.edit'];
if(faultElementOptions('C01').some(([id])=>id==='E2'))throw Error('Archiwalny element dostępny jako nowy wybór');
if(!faultElementOptions('C01','E2').some(([id])=>id==='E2'))throw Error('Brak zachowania istniejącego archiwalnego powiązania');
if(!faultElementOptions('niedostepna','E9').some(([id])=>id==='E9'))throw Error('Brak zachowania zapisanego elementu bez słownika');
openElement('C01','E1');if(!$('editor-fields').innerHTML.includes('P1/42'))throw Error('Brak edycji elementu');
if(!elementTable(db.panels[0]).includes('Dodaj element'))throw Error('Brak słownika na karcie centrali');
`,sandbox);
const localViewStore=new Map();sandbox.localStorage={getItem:key=>localViewStore.get(key)||null,setItem:(key,value)=>localViewStore.set(key,value)};
vm.runInContext(`
currentUser.id='U1';databaseName='database-A';route='faults';selectedPanel='';selectedFault='';selectedProtocol='';
filters={status:'Nowe',attention:'unassigned',search:'Czujka'};rememberViewFilters();
const sortKey=JSON.stringify(['faults','','',['Numer','Status']]);tableSortState.set(sortKey,{column:1,direction:'descending'});saveViewPreferences();
loadViewPreferences();if(restoredViewFilters('faults').search!=='Czujka'||tableSortState.get(sortKey)?.column!==1)throw Error('Nie odtworzono filtrów i sortowania');
currentUser.id='U2';loadViewPreferences();if(Object.keys(restoredViewFilters('faults')).length||tableSortState.size)throw Error('Pomieszano ustawienia kont');
currentUser.id='U1';databaseName='database-B';loadViewPreferences();if(Object.keys(restoredViewFilters('faults')).length)throw Error('Pomieszano ustawienia baz');
databaseName='database-A';loadViewPreferences();if(restoredViewFilters('faults').status!=='Nowe')throw Error('Utracono ustawienia pierwszej bazy');
route='search';filters={search:'Poufna fraza'};rememberViewFilters();if(Object.hasOwn(viewPreferences,'search'))throw Error('Utrwalono globalną frazę wyszukiwania');
route='faults';filters=restoredViewFilters('faults');resetCurrentView();
if(Object.keys(filters).length||tableSortState.has(sortKey))throw Error('Reset nie wyczyścił filtrów i sortowania');
if(!defaultViewFilters('reports').month)throw Error('Brak bieżącego miesiąca po resecie raportu');
localStorage.setItem(preferenceStorageKey(),'{uszkodzone');loadViewPreferences();if(Object.keys(restoredViewFilters('faults')).length)throw Error('Nie pominięto uszkodzonych ustawień');
localStorage.setItem=()=>{throw Error('blocked')};route='faults';filters={status:'Nowe'};rememberViewFilters();
if(!preferencesSessionOnly||restoredViewFilters('faults').status!=='Nowe')throw Error('Brak pamięci sesji po blokadzie localStorage');
`,sandbox);
sandbox.testCsvBlob.text().then(text=>{
 assert(text.includes('"-123,45"'),'Ujemna korekta nie jest liczbą w CSV');
 assert(text.includes("'"+String.fromCharCode(9)+"=CMD()"),'CSV nie zabezpiecza formuły po białym znaku');
 console.log('PASS: monthly totals, cents, cost corrections, recurrence analysis, CSV, global search, permissions, element dictionary, similar faults remembered views and UI regression.');
}).catch(e=>{console.error(e);process.exitCode=1;});
