// Direct-manipulation spectral feature canvas without modal interruptions
export interface PeakHandle { id: string; wavelengthNm: number; selected: boolean; }
export function selectPeakDirectly(handles: PeakHandle[], id: string): PeakHandle[] {
  return handles.map(h => ({ ...h, selected: h.id === id }));
}
