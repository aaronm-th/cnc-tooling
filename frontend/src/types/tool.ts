export type ToolType = 'TURNING' | 'MILLING' | 'DRILLING';

export interface Tool {
  id: string;          // z. B. "T0101" oder "T0100"
  name: string;        // z. B. "Schruppmeißel Außen"
  type: ToolType;      // Abtragsmechanismus
  radius: number;      // Schneidradius / Werkzeugradius in mm
  maxSweepRadius?: number; // Max. Radius für radiales Abräumen (bei TURNING)
}