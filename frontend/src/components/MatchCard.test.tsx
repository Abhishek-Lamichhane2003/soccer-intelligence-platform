import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MatchCard } from './MatchCard'

const match:any={id:'10',status:'SCHEDULED',utc_date:'2026-11-05T20:00:00Z',competition:{name:'Premier League'},home_team:{id:'1',name:'Home FC'},away_team:{id:'2',name:'Away FC'},score:{home:null,away:null}}

describe('MatchCard',()=>{
  it('opens the selected match',()=>{
    const onOpen=vi.fn()
    render(<MatchCard match={match} onOpen={onOpen}/>)
    fireEvent.click(screen.getByText('Match intelligence'))
    expect(onOpen).toHaveBeenCalledWith(match)
  })
})

describe('MatchCard knockout scoring',()=>{
  it('shows a penalty shootout without replacing the regulation score',()=>{
    const knockout:any={...match,status:'FINISHED',score:{home:1,away:1,penalty_home:5,penalty_away:4,duration:'PENALTY_SHOOTOUT'}}
    render(<MatchCard match={knockout}/>)
    expect(screen.getByText('Penalty shootout: 5–4')).toBeTruthy()
    expect(screen.getByText('Pens 5–4')).toBeTruthy()
  })
})
