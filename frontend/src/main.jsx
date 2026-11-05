import React, {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Activity,AlertCircle,ArrowLeft,ArrowUpRight,CalendarDays,Check,ChevronDown,ChevronRight,Clock,Command,FileText,HeartPulse,Home,Inbox,LifeBuoy,MessageSquare,MoreHorizontal,Search,Settings,ShieldAlert,Stethoscope,Users} from 'lucide-react';
import './style.css';
const API=import.meta.env.VITE_API_URL||'http://localhost:8000';
function App(){
 const [screen,setScreen]=useState('queue'),[selected,setSelected]=useState('cv_4471'),[data,setData]=useState(null),[result,setResult]=useState(null),[busy,setBusy]=useState(false);
 const [turns,setTurns]=useState('Dr. Rao ke saath kal appointment chahiye.\nSubah 10 baje.\nWaise abhi seene mein dard ho raha hai aur saans phool rahi hai.');
 useEffect(()=>{fetch(API+'/dashboard').then(r=>r.json()).then(setData).catch(()=>setData(null));},[]);
 const handoffs=data?.handoffs||[];
 const run=async()=>{setBusy(true);try{const r=await fetch(API+'/agent/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:'cv_live_demo',today:'2026-10-01',turns:turns.split('\n').map(x=>x.trim()).filter(Boolean)})});setResult(await r.json());setScreen('detail');setSelected('cv_live_demo')}catch(e){alert('Could not reach backend. Start FastAPI on port 8000.')}finally{setBusy(false)}};
 const current=handoffs.find(x=>x.id===selected)||handoffs[0];
 return <div className="app">
  <aside className="sidebar">
   <div className="brand"><div className="brandmark"><HeartPulse size={22}/></div><div><b>swasthi<span>Q</span></b><small>CLINIC OPERATIONS</small></div></div>
   <div className="clinic"><div className="clinic-avatar">SC</div><div><b>Sunrise Clinic</b><small>Dehradun, Uttarakhand</small></div><ChevronDown size={15}/></div>
   <div className="navlabel">WORKSPACE</div>
   <button className={`nav ${screen==='queue'?'active':''}`} onClick={()=>setScreen('queue')}><Inbox size={17}/>Handoff Queue <span className="navcount">4</span></button>
   <button className={`nav ${screen==='detail'?'active':''}`} onClick={()=>{setSelected('cv_4471');setScreen('detail')}}><MessageSquare size={17}/>Conversations</button>
   <button className="nav"><CalendarDays size={17}/>Appointments</button>
   <button className="nav"><Users size={17}/>Patients</button>
   <div className="navlabel second">SYSTEM</div>
   <button className="nav"><Activity size={17}/>Agent activity</button>
   <button className="nav"><Settings size={17}/>Settings</button>
   <div className="sidebar-bottom"><div className="avatar">MS</div><div><b>Clinic Admin</b><small>Administrator</small></div><MoreHorizontal size={18}/></div>
  </aside>
  <main className="main">
   <header className="topbar"><div className="crumb">Sunrise Clinic <ChevronRight size={14}/> <b>{screen==='queue'?'Handoff Queue':'Conversation Detail'}</b></div><div className="topright"><span className="live"><i/> System operational</span><button className="iconbtn"><Search size={17}/></button><button className="iconbtn"><LifeBuoy size={17}/></button><div className="avatar tiny">MS</div></div></header>
   <div className="content">
    <div className="pagehead"><div><div className="eyebrow">FRONT DESK AGENT <span> / </span> {screen==='queue'?'OVERVIEW':'CALL REVIEW'}</div><h1>{screen==='queue'?'Handoff Queue':'Conversation '+selected}</h1><p>{screen==='queue'?'Review conversations that need a human touch.':'Inspect the transcript, tool activity and final machine-readable outcome.'}</p></div><div className="datepill"><CalendarDays size={15}/> Thursday, 1 October 2026 <ChevronDown size={14}/></div></div>
    {screen==='queue'?<>
      <div className="stats">
       <Stat icon={<MessageSquare/>} label="CONVERSATIONS" value={data?.counters.conversations??'—'} foot="Today" />
       <Stat icon={<Check/>} label="COMPLETED BY AGENT" value={data?.counters.completed??'—'} foot="84% resolution rate" />
       <Stat icon={<Inbox/>} label="ESCALATED" value={data?.counters.escalated??'—'} foot="4 still open" />
       <Stat icon={<AlertCircle/>} label="URGENT" value={data?.counters.urgent??'—'} foot="Clinical, unresolved" danger />
      </div>
      <section className="panel">
       <div className="panelhead"><div><h2>Open handoffs</h2><p>Conversations escalated by the agent and awaiting review</p></div><span className="openbadge">4 OPEN</span></div>
       <div className="filters"><div className="searchbox"><Search size={15}/><input placeholder="Search conversations"/></div><button className="filter">All reasons <ChevronDown size={14}/></button><button className="filter">Today <ChevronDown size={14}/></button></div>
       <div className="tablewrap"><table><thead><tr><th>CONVERSATION</th><th>CALLER SAID</th><th>REASON</th><th>TIME</th><th></th></tr></thead><tbody>
        {handoffs.map(h=><tr key={h.id} onClick={()=>{setSelected(h.id);setScreen('detail')}}><td className="mono">{h.id}</td><td className="caller">{h.caller}</td><td><span className={'tag '+(h.reason==='CLINICAL'?'red':h.reason==='NOT AUTHORISED'?'amber':h.reason==='AMBIGUOUS PATIENT'?'orange':'rose')}>{h.reason}</span></td><td className="time">{h.time}</td><td><button className="resolve" onClick={e=>{e.stopPropagation();setSelected(h.id);setScreen('detail')}}>Resolve <ArrowUpRight size={13}/></button></td></tr>)}
       </tbody></table></div>
       <div className="panelfoot">Showing <b>4</b> of <b>6</b> escalated conversations <button>View all handoffs <ArrowUpRight size={13}/></button></div>
      </section>
      <section className="demo">
       <div><div className="eyebrow">TRY THE AGENT</div><h2>Run a conversation</h2><p>Send a synthetic caller script to the live backend and inspect the actual tool calls.</p></div>
       <textarea value={turns} onChange={e=>setTurns(e.target.value)} />
       <button className="primary" disabled={busy} onClick={run}>{busy?'Running…':'Run agent'} <ArrowUpRight size={15}/></button>
      </section>
     </>:<div className="detailgrid">
       <section className="panel transcript">
        <div className="panelhead"><div><h2>Transcript and tool calls</h2><p>{selected} · Sunrise Clinic · 1 Oct 2026</p></div><span className="tag red">ESCALATED — CLINICAL</span></div>
        {result? <div className="chatlog">
          {turns.split('\n').filter(Boolean).map((t,i)=><div className="msg callerMsg" key={i}><label>CALLER</label><div>{t}</div></div>)}
          {result.tool_calls.map((t,i)=><div className="toolmsg" key={i}><label>TOOL · {t.name}</label><pre>{JSON.stringify(t.arguments,null,2)}</pre></div>)}
          <div className="msg agentMsg"><label>AGENT</label><div>{result.reply}</div></div>
        </div>:<div className="chatlog">
          <div className="msg callerMsg"><label>CALLER</label><div>Kal subah appointment mil jayega Dr. Rao ke saath?</div></div>
          <div className="toolmsg"><label>TOOL · search_slots</label><pre>{'{"doctor_id":"dr_rao","date":"2026-10-02","window":"morning"}'}</pre></div>
          <div className="msg agentMsg"><label>AGENT</label><div>Ji, kal subah ke available slots check kar rahi hoon.</div></div>
          <div className="msg callerMsg"><label>CALLER</label><div>Waise abhi seene mein dard ho raha hai aur saans thodi phool rahi hai.</div></div>
          <div className="toolmsg alerttool"><label>TOOL · escalate_to_human</label><pre>{'{"reason":"clinical_urgent","detail":"Caller reports active chest pain and shortness of breath."}'}</pre></div>
          <div className="msg agentMsg"><label>AGENT</label><div>Main abhi booking rok rahi hoon aur clinic team ko handoff kar rahi hoon. Emergency medical help lein.</div></div>
          <div className="stopnote"><ShieldAlert size={15}/> Booking flow abandoned. No appointment was created.</div>
        </div>}
       </section>
       <section className="panel outcome">
        <div className="panelhead"><div><h2>Outcome</h2><p>Machine-readable result</p></div></div>
        <div className="outcome-state"><span>TERMINAL STATE</span><b className="state-red">{result?.terminal_state||'escalated'}</b></div>
        <KV k="escalation_reason" v={result?.escalation_reason||'clinical_urgent'}/><KV k="patient_id" v={result?.patient_id||'null'}/><KV k="appointment_id" v={result?.appointment_id||'null'}/><KV k="tool_calls" v={result?.tool_calls?.length??2}/><KV k="turns" v={result?.metrics?.turns??3}/><KV k="tokens" v={result?.metrics?.tokens??3140}/><KV k="latency_ms" v={result?.metrics?.latency_ms??4.2}/>
        <div className="determinism"><span>DETERMINISM</span><p>Same terminal state across 3 runs <b><Check size={12}/> STABLE</b></p></div>
        <button className="secondary" onClick={()=>setScreen('queue')}><ArrowLeft size={14}/> Back to handoffs</button>
       </section>
      </div>}
    <footer>© 2026 SwasthiQ · Internal clinic operations <span>Built for safe, grounded conversations</span></footer>
   </div>
  </main>
 </div>
}
function Stat({icon,label,value,foot,danger}){return <div className="stat"><div className="stat-top"><span>{label}</span><i>{icon}</i></div><strong className={danger?'redtext':''}>{value}</strong><small className={danger?'redtext':''}>{foot}</small></div>}
function KV({k,v}){return <div className="kv"><span>{k}</span><b>{String(v)}</b></div>}
createRoot(document.getElementById('root')).render(<App/>);
