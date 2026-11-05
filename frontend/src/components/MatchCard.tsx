import { CalendarDays, Radio, ChevronRight } from 'lucide-react'
import type { Match } from '../types'
import { TeamBadge } from './TeamBadge'

function resultNote(match:Match){
  const s=match.score
  if(s.penalty_home!=null&&s.penalty_away!=null)return `Pens ${s.penalty_home}–${s.penalty_away}`
  if(s.duration==='EXTRA_TIME'||(s.extra_home!=null&&s.extra_away!=null))return 'AET'
  return match.minute?`${match.minute}'`:match.status
}

export function MatchCard({match,live=false,onOpen}:{match:Match;live?:boolean;onOpen?:(m:Match)=>void}){const date=match.utc_date?new Date(match.utc_date):null;return <article className="fixture-card interactive-card" onClick={()=>onOpen?.(match)}>
 <div className="fixture-topline"><span>{match.competition.name||match.competition.code}</span>{live?<span className="status-live"><Radio size={13}/> LIVE</span>:<span className="fixture-date"><CalendarDays size={13}/>{date?date.toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'TBD'}</span>}</div>
 <div className="fixture-teams"><TeamBadge team={match.home_team} side="home"/><div className="fixture-score">{live||match.status==='FINISHED'?<><strong>{match.score.home??'–'}</strong><span>–</span><strong>{match.score.away??'–'}</strong><small>{resultNote(match)}</small></>:<><span className="versus">VS</span><small>{match.status}</small></>}</div><TeamBadge team={match.away_team} side="away"/></div>
 {(match.score.penalty_home!=null&&match.score.penalty_away!=null)&&<div className="shootout-note">Penalty shootout: {match.score.penalty_home}–{match.score.penalty_away}</div>}
 <div className="card-open">Match intelligence <ChevronRight size={14}/></div>
 </article>}
