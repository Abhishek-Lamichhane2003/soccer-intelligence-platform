import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TeamBadge } from './TeamBadge'

const team={id:'1',name:'Example United',short_name:'Example',crest:'https://invalid.example/crest.png'}

describe('TeamBadge',()=>{
  it('falls back to initials when a remote crest fails',()=>{
    render(<TeamBadge team={team} side="home" />)
    const image=screen.getByAltText('Example United crest')
    fireEvent.error(image)
    expect(screen.getByText('E')).toBeTruthy()
  })
})
