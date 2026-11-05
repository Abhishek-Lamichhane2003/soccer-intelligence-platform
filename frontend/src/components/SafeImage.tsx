import { useEffect, useState, type ReactNode } from 'react'
import type { Team } from '../types'

export function SafeImage({src,alt,className,fallback}:{src?:string|null;alt:string;className?:string;fallback:ReactNode}){
  const[failed,setFailed]=useState(false)
  useEffect(()=>setFailed(false),[src])
  if(!src||failed)return <span className={`${className||''} safe-image-fallback`} role="img" aria-label={alt}>{fallback}</span>
  return <img className={className} src={src} alt={alt} loading="lazy" onError={()=>setFailed(true)}/>
}

export function SafeTeamCrest({team,className}:{team:Team;className?:string}){
  const initials=(team.tla||team.short_name||team.name||'FC').replace(/[^A-Za-z0-9 ]/g,'').split(' ').filter(Boolean).map(x=>x[0]).join('').slice(0,3).toUpperCase()||'FC'
  return <SafeImage src={team.crest} alt={`${team.name} crest`} className={className} fallback={initials}/>
}
