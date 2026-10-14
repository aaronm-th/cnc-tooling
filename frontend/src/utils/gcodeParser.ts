// src/utils/gcodeParser.ts

export interface GCodeCommand {
  lineNumber: number;
  raw: string;
  type: 'G0' | 'G1' | 'G00' | 'G01' | 'OTHER';
  x?: number;
  y?: number;
  z?: number;
  feedRate?: number;
}

export function parseGCode(gcodeText: string): GCodeCommand[] {
  const lines = gcodeText.split('\n');
  const commands: GCodeCommand[] = [];

  // Führt den aktiven Bewegungsmodus über mehrere Zeilen mit (Modalität)
  let activeMotionMode: 'G0' | 'G1' = 'G0';

  lines.forEach((lineText, index) => {
    // Kommentare & Semikolons entfernen
    const cleanLine = lineText.replace(/\(.*?\)/g, '').split(';')[0].trim().toUpperCase();
    if (!cleanLine) return;

    const tokens = cleanLine.split(/\s+/);
    let explicitType: 'G0' | 'G1' | null = null;

    const cmd: GCodeCommand = {
      lineNumber: index + 1,
      raw: lineText,
      type: 'OTHER'
    };

    tokens.forEach(token => {
      const letter = token[0];
      const value = parseFloat(token.substring(1));

      if (isNaN(value) && letter !== 'G') return;

      switch (letter) {
        case 'G':
          if (value === 0 || value === 0.0) {
            explicitType = 'G0';
            activeMotionMode = 'G0';
          } else if (value === 1 || value === 1.0) {
            explicitType = 'G1';
            activeMotionMode = 'G1';
          }
          break;
        case 'X':
          cmd.x = value;
          break;
        case 'Y':
          cmd.y = value;
          break;
        case 'Z':
          cmd.z = value;
          break;
        case 'F':
          cmd.feedRate = value;
          break;
      }
    });

    // Wenn in der Zeile Bewegungen (X, Y, Z) vorkommen, nutze den modalen Modus (G0 oder G1)
    if (explicitType) {
      cmd.type = explicitType;
    } else if (cmd.x !== undefined || cmd.y !== undefined || cmd.z !== undefined) {
      cmd.type = activeMotionMode;
    } else {
      cmd.type = 'OTHER';
    }

    commands.push(cmd);
  });

  return commands;
}