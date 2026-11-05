import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PitchRadar } from './PitchRadar'

const players=(prefix:string)=>Array.from({length:11},(_,i)=>({id:`${prefix}-${i+1}`,name:`${prefix} Player ${i+1}`,position:i===0?'Goalkeeper':i<5?'Defender':i<9?'Midfielder':'Forward',shirt_number:i+1}))

describe('PitchRadar',()=>{
  it('renders all 22 identifiable players',()=>{
    render(<PitchRadar home={players('Home')} away={players('Away')} />)
    expect(screen.getAllByRole('button').length).toBe(23) // 22 players + ball
    expect(screen.getByTitle('#1 Home Player 1 • Goalkeeper')).toBeTruthy()
    expect(screen.getByTitle('#11 Away Player 11 • Forward')).toBeTruthy()
  })

  it('never fabricates a shirt number when provider data omits it',()=>{
    const withoutNumbers=players('Real').map(p=>({...p,shirt_number:null}))
    render(<PitchRadar home={withoutNumbers} away={[]} />)
    expect(screen.getByTitle('Real Player 1 • Goalkeeper • shirt number unavailable')).toBeTruthy()
    expect(screen.queryByTitle('#1 Real Player 1 • Goalkeeper')).toBeNull()
  })
})
