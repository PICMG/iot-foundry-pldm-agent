import { describe, expect, it } from 'vitest'
import { extractLinkedResources, getStatusTone, normalizeRedfishPath } from './redfish'

describe('redfish utilities', () => {
  it('normalizes absolute and relative resource paths', () => {
    expect(normalizeRedfishPath('http://127.0.0.1:8000/redfish/v1/Systems/1')).toBe('/redfish/v1/Systems/1')
    expect(normalizeRedfishPath('Systems')).toBe('/Systems')
    expect(normalizeRedfishPath('/')).toBe('/redfish/v1')
  })

  it('extracts direct and array link references', () => {
    const links = extractLinkedResources({
      Name: 'Root',
      Systems: { '@odata.id': '/redfish/v1/Systems' },
      Links: [
        { '@odata.id': '/redfish/v1/Chassis/1U' },
        { notALink: true },
      ],
    })

    expect(links).toEqual([
      { key: 'Systems:0', path: '/redfish/v1/Systems' },
      { key: 'Links:0', path: '/redfish/v1/Chassis/1U' },
    ])
  })

  it('maps redfish status to visual tones', () => {
    expect(getStatusTone({ Health: 'OK', State: 'Enabled' })).toBe('ok')
    expect(getStatusTone({ Health: 'Warning', State: 'Enabled' })).toBe('warning')
    expect(getStatusTone({ Health: 'Critical', State: 'Enabled' })).toBe('critical')
  })
})
