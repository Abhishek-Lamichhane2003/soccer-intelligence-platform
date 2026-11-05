import { useMemo, useState } from 'react'
import { Heart, Search, X } from 'lucide-react'
import type { Favorite, Team } from '../types'
import { SafeTeamCrest } from './SafeImage'
export function TeamBrowser({teams,onOpen,favorites,onFavorite}:{teams:Team[];onOpen:(t:Team)=>void;favorites:Favorite[];onFavorite:(t:Team)=>void}){const[q,setQ]=useState('');const filtered=useMemo(()=>teams.filter(t=>(t.name||'').toLowerCase().includes(q.toLowerCase())||(t.tla||'').toLowerCase().includes(q.toLowerCase())),[q,teams]);return <>
 <div className="club-search"><Search/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search clubs…"/>{q&&<button onClick={()=>setQ('')}><X/></button>}</div>
 <div className="club-grid">{filtered.map(t=><article className="club-card panel interactive-card" key={t.id} onClick={()=>onOpen(t)}><SafeTeamCrest team={t} className="club-crest"/><span>{t.tla}</span><h3>{t.short_name||t.name}</h3><p>{t.venue||'Venue data unavailable'}</p><button className={`heart-btn ${favorites.some(f=>f.entity_id===t.id)?'is-favorite':''}`} onClick={e=>{e.stopPropagation();onFavorite(t)}}><Heart fill="currentColor"/></button></article>)}</div>
 </>}
