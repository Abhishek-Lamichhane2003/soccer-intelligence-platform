import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRightLeft, BrainCircuit, CalendarDays, Info, LoaderCircle, ShieldAlert, Trophy, X } from 'lucide-react'
import { api } from '../lib/api'
import type { Match, Player, TimelineEvent } from '../types'
import { PitchRadar } from './PitchRadar'
import { TeamBadge } from './TeamBadge'
import { SafeImage } from './SafeImage'

function eventIcon(kind:string,meta?:string|null){if(kind==='goal')return '⚽';if(kind==='substitution')return '↕';if((meta||'').includes('RED'))return '🟥';return '🟨'}
function minuteLabel(e:TimelineEvent){return e.minute==null?'—':`${e.minute}'`}
function matchStatusLabel(m:Match){if(m.score.penalty_home!=null&&m.score.penalty_away!=null)return `PENS ${m.score.penalty_home}–${m.score.penalty_away}`;if(m.score.duration==='EXTRA_TIME'||(m.score.extra_home!=null&&m.score.extra_away!=null))return 'AET';return m.status==='IN_PLAY'||m.status==='LIVE'?`${m.minute||''}'`:m.status}

export function MatchDetailModal({match,onClose}:{match:Match;onClose:()=>void}){
 const [detail,setDetail]=useState<Match|null>(null);const [loading,setLoading]=useState(true);const [error,setError]=useState<string|null>(null);const [selected,setSelected]=useState<Player|null>(null)
 const [prediction,setPrediction]=useState<any|null>(null);const[predicting,setPredicting]=useState(false);const[predictError,setPredictError]=useState('')
 useEffect(()=>{let live=true;setLoading(true);api.match(match.id).then(d=>live&&setDetail(d)).catch(e=>live&&setError(e.message)).finally(()=>live&&setLoading(false));return()=>{live=false}},[match.id])
 const m=detail||match
 const timeline=useMemo(()=>m.timeline||[],[m.timeline])
 const homePlayers=m.home_lineup?.lineup||[];const awayPlayers=m.away_lineup?.lineup||[]
 async function runModel(){setPredicting(true);setPredictError('');try{setPrediction(await api.predict(match.id))}catch(e){setPredictError(e instanceof Error?e.message:'Prediction unavailable')}finally{setPredicting(false)}}
 return <div className="modal-backdrop" onMouseDown={e=>{if(e.currentTarget===e.target)onClose()}}><section className="match-modal panel modal-enter">
   <button className="modal-close" onClick={onClose}><X/></button>
   <div className="match-modal-head">
    <div className="modal-comp"><SafeImage src={m.competition.emblem} alt={`${m.competition.name||m.competition.code||'Competition'} emblem`} className="modal-comp-emblem" fallback={<Trophy/>}/><span>{m.competition.name||m.competition.code}</span></div>
    <div className="modal-meta"><CalendarDays size={14}/>{m.utc_date?new Date(m.utc_date).toLocaleString():'TBD'}{m.venue&&<><span>•</span>{m.venue}</>}</div>
   </div>
   <div className="modal-scoreboard"><TeamBadge team={m.home_team} side="home"/><div className="modal-score"><strong>{m.score.home??'–'}</strong><span>:</span><strong>{m.score.away??'–'}</strong><small>{matchStatusLabel(m)}</small></div><TeamBadge team={m.away_team} side="away"/></div>
   {(m.score.penalty_home!=null&&m.score.penalty_away!=null)&&<div className="score-breakdown"><b>Penalty shootout</b><span>{m.score.penalty_home}–{m.score.penalty_away}</span>{m.score.regular_home!=null&&<small>90 min: {m.score.regular_home}–{m.score.regular_away}</small>}{m.score.extra_home!=null&&<small>Extra time: {m.score.extra_home}–{m.score.extra_away}</small>}</div>}
   {m.score.duration==='EXTRA_TIME'&&m.score.penalty_home==null&&<div className="score-breakdown"><b>After extra time</b>{m.score.regular_home!=null&&<small>90 min: {m.score.regular_home}–{m.score.regular_away}</small>}</div>}
   <div className="model-action-row"><button className="primary-btn compact" disabled={predicting} onClick={runModel}><BrainCircuit size={16}/>{predicting?'Running…':prediction?'Refresh match model':'Run match model'}</button><small>Transparent win-probability baseline; optional grounded LLM explanation only when configured.</small></div>
   {predictError&&<div className="form-error">{predictError}</div>}
   {prediction&&<div className="prediction-card"><div><span>HOME</span><b>{prediction.probabilities.home}%</b></div><div><span>DRAW</span><b>{prediction.probabilities.draw}%</b></div><div><span>AWAY</span><b>{prediction.probabilities.away}%</b></div><p><strong>{prediction.analysis.headline}</strong> {prediction.analysis.detail}</p><small>{prediction.probabilities.model} • {prediction.analysis.generated_by}</small></div>}
   {loading?<div className="modal-loading"><LoaderCircle className="spin"/> Loading match intelligence…</div>:error?<div className="notice-card notice-card--warn"><ShieldAlert/><div><b>Match detail unavailable</b><p>{error}</p></div></div>:<>
    {m.deep_data_available?<div className="detail-layout">
      <div className="detail-main"><div className="detail-title"><Activity/><div><span>TACTICAL LINEUP</span><h3>{m.home_lineup?.formation||'XI'} vs {m.away_lineup?.formation||'XI'}</h3></div></div>
       <PitchRadar home={homePlayers} away={awayPlayers} homeFormation={m.home_lineup?.formation} awayFormation={m.away_lineup?.formation} onPlayer={setSelected} selectedId={selected?.id}/>
       <div className="coaches"><span>Coach: <b>{m.home_lineup?.coach||'—'}</b></span><span>Coach: <b>{m.away_lineup?.coach||'—'}</b></span></div>
      </div>
      <div className="event-timeline"><div className="detail-title"><ArrowRightLeft/><div><span>MATCH EVENTS</span><h3>Who did what</h3></div></div>
       {timeline.length?timeline.map((e,i)=><article className={`timeline-row timeline-${e.kind}`} key={`${e.kind}-${e.minute}-${i}`}><time>{minuteLabel(e)}</time><div className="timeline-icon">{eventIcon(e.kind,e.meta)}</div><div><b>{e.primary?.shirt_number?`#${e.primary.shirt_number} `:''}{e.primary?.name||'Unknown player'}</b><small>{e.team?.short_name||e.team?.name}</small>{e.kind==='goal'&&<p>{e.secondary?.name?`Assist: ${e.secondary.shirt_number?`#${e.secondary.shirt_number} `:''}${e.secondary.name}`:'Unassisted / assist unavailable'}{e.score?` • ${e.score.home}–${e.score.away}`:''}</p>}{e.kind==='substitution'&&<p>ON • {e.secondary?.name?`${e.secondary.shirt_number?`#${e.secondary.shirt_number} `:''}${e.secondary.name} OFF`:''}</p>}{e.kind==='booking'&&<p>{(e.meta||'CARD').replace('_',' ')}</p>}</div></article>):<div className="empty-mini">No unfolded events returned for this match.</div>}
      </div>
     </div>:<div className="notice-card"><Info/><div><b>Basic match data is available.</b><p>Detailed lineup and event data are unavailable for this match. Basic match information remains available.</p></div></div>}
    {selected&&<div className="player-inspector floating-inspector"><button onClick={()=>setSelected(null)}><X size={14}/></button><span>PLAYER DETAILS</span><h3>{selected.shirt_number?`#${selected.shirt_number} `:''}{selected.name}</h3><div><b>{selected.position||'Player'}</b><small>{selected.shirt_number?'':'Shirt number unavailable • '}{selected.nationality||''}</small></div></div>}
   </>}
 </section></div>
}
