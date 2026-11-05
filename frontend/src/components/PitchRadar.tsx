import { useMemo } from 'react'
import type { DemoPlayer, Player } from '../types'

type PitchPlayer=Player & {x:number;y:number;shirt_number?:number|null;rating?:number}

function spread(count:number){if(count<=1)return [50];return Array.from({length:count},(_,i)=>12+(76*i)/(count-1))}
function isRole(p:Player,needle:string){return `${p.role||''} ${p.position||''}`.toLowerCase().includes(needle)}
function autoLayout(players:Player[],side:'home'|'away'):PitchPlayer[]{
  const list=players.slice(0,11)
  const gk=list.filter(p=>isRole(p,'goal'))
  const def=list.filter(p=>!gk.includes(p)&&(isRole(p,'back')||isRole(p,'defence')||isRole(p,'defender')))
  const fwd=list.filter(p=>!gk.includes(p)&&!def.includes(p)&&(isRole(p,'forward')||isRole(p,'wing')||isRole(p,'striker')||isRole(p,'attack')))
  const mid=list.filter(p=>!gk.includes(p)&&!def.includes(p)&&!fwd.includes(p))
  const rows=[gk.length?gk:[list[0]].filter(Boolean),def,mid,fwd].filter(r=>r.length)
  const homeXs=[8,28,52,76],awayXs=[92,72,48,24]
  const out:PitchPlayer[]=[]
  rows.forEach((row,ri)=>{const ys=spread(row.length);row.forEach((p,i)=>out.push({...p,x:side==='home'?homeXs[Math.min(ri,3)]:awayXs[Math.min(ri,3)],y:ys[i],shirt_number:p.shirt_number??null}))})
  return out.slice(0,11)
}

export function PitchRadar({home=[],away=[],ball,minute=0,onPlayer,selectedId,homeFormation,awayFormation}:{home?:Player[];away?:Player[];ball?:{x:number;y:number};minute?:number;onPlayer?:(p:DemoPlayer|PitchPlayer)=>void;selectedId?:string|null;homeFormation?:string|null;awayFormation?:string|null}){
 const fallbackBall=ball||{x:18+((minute*7)%64),y:25+((minute*11)%50)}
 const hp=useMemo(()=>home.length&&home[0].x!==undefined?home as PitchPlayer[]:autoLayout(home,'home'),[home])
 const ap=useMemo(()=>away.length&&away[0].x!==undefined?away as PitchPlayer[]:autoLayout(away,'away'),[away])
 return <div className="pitch-radar pitch-radar--full" aria-label="22-player tactical pitch">
  <div className="pitch-stripes"/><div className="pitch-mid"/><div className="pitch-circle"/><div className="pitch-spot pitch-spot--home"/><div className="pitch-spot pitch-spot--away"/><div className="box box-left"/><div className="box box-right"/><div className="goal goal-left"/><div className="goal goal-right"/><div className="radar-sweep"/>
  <div className="formation-tag formation-tag--home">{homeFormation||'HOME XI'}</div><div className="formation-tag formation-tag--away">{awayFormation||'AWAY XI'}</div>
  <div className="attack-arrow attack-arrow--home">→</div><div className="attack-arrow attack-arrow--away">←</div>
  <button className="ball-pulse ball-real" style={{left:`${fallbackBall.x}%`,top:`${fallbackBall.y}%`}} aria-label="ball" />
  {[...hp.map(p=>({...p,side:'home'})),...ap.map(p=>({...p,side:'away'}))].map((p:any)=>{const number=p.shirt_number??null;const label=number?`#${number}`:'—';return <button key={`${p.side}-${p.id}`} className={`player-token player-token--${p.side} ${selectedId===p.id?'is-selected':''}`} style={{left:`${p.x}%`,top:`${p.y}%`}} onClick={()=>onPlayer?.(p)} title={`${number?`#${number} `:''}${p.name} • ${p.position||p.role||'Player'}${number?'':' • shirt number unavailable'}`}><b className={number?'':'number-missing'}>{label}</b><span>{(p.name||'Player').split(' ').slice(-1)[0]}</span>{p.rating?<i>{p.rating}</i>:null}</button>})}
 </div>
}
