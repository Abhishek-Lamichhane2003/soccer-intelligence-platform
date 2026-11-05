import { useState, type MouseEvent } from 'react'
import { Crosshair, LoaderCircle, Sparkles } from 'lucide-react'
import { api } from '../lib/api'

type Result={xg:number;model:string;features:{distance:number;angle:number;under_pressure:boolean;first_time:boolean;body_part:string;play_pattern:string}}

export function XGLab(){
 const[x,setX]=useState(104);const[y,setY]=useState(40);const[underPressure,setUnderPressure]=useState(false);const[firstTime,setFirstTime]=useState(false);const[bodyPart,setBodyPart]=useState('Right Foot');const[result,setResult]=useState<Result|null>(null);const[loading,setLoading]=useState(false);const[error,setError]=useState('')
 function placeShot(e:MouseEvent<HTMLButtonElement>){const r=e.currentTarget.getBoundingClientRect();const px=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));const py=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height));setX(Math.round(px*1200)/10);setY(Math.round(py*800)/10);setResult(null)}
 async function predict(){setLoading(true);setError('');try{setResult(await api.xgPredict({x,y,under_pressure:underPressure,first_time:firstTime,body_part:bodyPart,play_pattern:'Regular Play'}))}catch(e){setError(e instanceof Error?e.message:'xG prediction unavailable')}finally{setLoading(false)}}
 const pct=Math.round((result?.xg||0)*1000)/10
 return <section className="xg-lab panel">
  <div className="section-head"><div><span className="eyebrow">SHOT INTELLIGENCE</span><h3>xG Shot Lab</h3></div><Crosshair/></div>
  <p className="xg-copy">Select a shot location and conditions to estimate the probability of scoring.</p>
  <div className="xg-lab-grid">
   <button className="xg-pitch" onClick={placeShot} aria-label="Choose shot location"><span className="xg-box"/><span className="xg-goal"/><span className="xg-spot" style={{left:`${(x/120)*100}%`,top:`${(y/80)*100}%`}}><i/></span><small>Attack →</small></button>
   <div className="xg-controls"><label>Body part<select value={bodyPart} onChange={e=>{setBodyPart(e.target.value);setResult(null)}}><option>Right Foot</option><option>Left Foot</option><option>Head</option><option>Other</option></select></label><label className="check-row"><input type="checkbox" checked={underPressure} onChange={e=>{setUnderPressure(e.target.checked);setResult(null)}}/> Under pressure</label><label className="check-row"><input type="checkbox" checked={firstTime} onChange={e=>{setFirstTime(e.target.checked);setResult(null)}}/> First-time shot</label><div className="shot-coords"><span>X <b>{x.toFixed(1)}</b></span><span>Y <b>{y.toFixed(1)}</b></span></div><button className="primary-btn compact" disabled={loading} onClick={predict}>{loading?<LoaderCircle className="spin"/>:<Sparkles/>}{loading?'Predicting…':'Predict xG'}</button>{error&&<div className="form-error">{error}</div>}</div>
   <div className={`xg-result ${result?'has-result':''}`}><span>EXPECTED GOALS</span><strong>{result?result.xg.toFixed(3):'—'}</strong><div className="xg-meter"><i style={{width:`${pct}%`}}/></div><small>{result?`${pct}% scoring probability`:'Place a shot and run the model.'}</small>{result&&<><b>{result.model==='trained-statsbomb-model'?'STATSBOMB-TRAINED MODEL':'BASELINE MODEL'}</b><p>Distance {result.features.distance.toFixed(1)} • angle {result.features.angle.toFixed(2)} rad</p></>}</div>
  </div>
 </section>
}
