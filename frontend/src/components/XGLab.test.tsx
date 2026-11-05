import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../lib/api'
import { XGLab } from './XGLab'

describe('XGLab',()=>{
  afterEach(()=>vi.restoreAllMocks())

  it('calls the real xG endpoint and labels the returned model',async()=>{
    vi.spyOn(api,'xgPredict').mockResolvedValue({
      xg:0.421,
      model:'geometric-baseline',
      features:{distance:12.4,angle:0.55,under_pressure:false,first_time:false,body_part:'Right Foot',play_pattern:'Regular Play'},
    })
    render(<XGLab/>)
    fireEvent.click(screen.getByRole('button',{name:'Predict xG'}))
    expect(await screen.findByText('0.421')).toBeTruthy()
    expect(screen.getByText('BASELINE MODEL')).toBeTruthy()
    expect(api.xgPredict).toHaveBeenCalledTimes(1)
  })
})
