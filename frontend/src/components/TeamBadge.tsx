import type { Team } from '../types'
import { SafeTeamCrest } from './SafeImage'

export function TeamBadge({ team, side }: { team: Team; side: 'home' | 'away' }) {
  return (
    <div className={`team team--${side}`}>
      <div className="crest-wrap"><SafeTeamCrest team={team} className="team-badge-crest"/></div>
      <div>
        <div className="team-kicker">{side === 'home' ? 'HOME' : 'AWAY'}</div>
        <div className="team-name">{team.short_name || team.name}</div>
      </div>
    </div>
  )
}
