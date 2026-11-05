import type { Probabilities } from '../types'

export function ProbabilityBar({ p }: { p: Probabilities }) {
  return (
    <section className="panel probability-panel">
      <div className="section-head">
        <div>
          <span className="eyebrow">EXPLAINABLE MODEL</span>
          <h3>Win probability</h3>
        </div>
        <span className="model-chip">{p.model}</span>
      </div>
      <div className="probability-track" aria-label="win probability">
        <div className="prob-home" style={{ width: `${p.home}%` }} />
        <div className="prob-draw" style={{ width: `${p.draw}%` }} />
        <div className="prob-away" style={{ width: `${p.away}%` }} />
      </div>
      <div className="probability-labels">
        <div><strong>{p.home}%</strong><span>Home</span></div>
        <div><strong>{p.draw}%</strong><span>Draw</span></div>
        <div><strong>{p.away}%</strong><span>Away</span></div>
      </div>
      <p className="microcopy">{p.disclaimer}</p>
    </section>
  )
}
