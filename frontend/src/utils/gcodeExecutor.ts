// src/utils/gcodeExecutor.ts
import { GCodeCommand } from './gcodeParser';

export type ToolType = 'TURNING' | 'MILLING' | 'DRILLING';

export interface Tool {
  id: string;             // z. B. "T0101"
  name: string;           // z. B. "Schruppmeißel CNMG 1204"
  type: ToolType;         // Abtragsmechanismus
  radius: number;         // Schneidradius / Werkzeugradius in mm
  maxSweepRadius?: number; // Max. Radius für radiales Abräumen (bei TURNING)
}

export class ToolRegistry {
  private tools: Map<string, Tool> = new Map();

  constructor() {
    // Standard-Bestückung des Revolvers
    this.registerTool({
      id: 'T0101',
      name: 'Schruppmeißel CNMG 1204',
      type: 'TURNING',
      radius: 3.5,
      maxSweepRadius: 60.0
    });

    this.registerTool({
      id: 'T0202',
      name: 'Spiralbohrer D8',
      type: 'DRILLING',
      radius: 4.0
    });

    this.registerTool({
      id: 'T0303',
      name: 'Schaftfräser D10',
      type: 'MILLING',
      radius: 5.0
    });
  }

  public registerTool(tool: Tool) {
    this.tools.set(tool.id.toUpperCase(), tool);
  }

  public getTool(id: string): Tool | undefined {
    return this.tools.get(id.toUpperCase());
  }
}

export interface ToolPosition {
  x: number;
  y: number;
  z: number;
}

export class GCodeExecutor {
  private commands: GCodeCommand[] = [];
  private currentCommandIndex: number = 0;
  private currentPos: ToolPosition = { x: 0, y: 0, z: 100 };
  private stepSize: number = 0.5; // Interpolations-Schrittweite in mm
  private toolRegistry: ToolRegistry;
  private activeTool: Tool;

  constructor(toolRegistry?: ToolRegistry) {
    this.toolRegistry = toolRegistry || new ToolRegistry();
    
    // Standard-Fallback Werkzeug
    this.activeTool = this.toolRegistry.getTool('T0101') || {
      id: 'DEFAULT',
      name: 'Default Turning Tool',
      type: 'TURNING',
      radius: 3.0,
      maxSweepRadius: 60.0
    };
  }

  public loadProgram(commands: GCodeCommand[], startPos?: ToolPosition) {
    this.commands = commands;
    this.currentCommandIndex = 0;
    if (startPos) this.currentPos = { ...startPos };
    
    // Bei Neustart auf Standard-Werkzeug zurücksetzen
    this.activeTool = this.toolRegistry.getTool('T0101') || this.activeTool;
  }

  public getPosition(): ToolPosition {
    return { ...this.currentPos };
  }

  public getCurrentLineNumber(): number {
    if (this.currentCommandIndex >= this.commands.length) return -1;
    return this.commands[this.currentCommandIndex]?.lineNumber || -1;
  }

  public getActiveTool(): Tool {
    return { ...this.activeTool };
  }

  public isFinished(): boolean {
    return this.currentCommandIndex >= this.commands.length;
  }

  public step(stockEngine: any): ToolPosition | null {
    if (this.isFinished()) return null;

    const cmd = this.commands[this.currentCommandIndex];

    // Dynamischer Werkzeugwechsel anhand von T-Befehlen im G-Code (z. B. T0101, T0202)
    const tMatch = cmd.raw.match(/T\d{4}/i) || cmd.raw.match(/T\d{2}/i);
    if (tMatch) {
      const toolId = tMatch[0].toUpperCase();
      const foundTool = this.toolRegistry.getTool(toolId);
      if (foundTool) {
        this.activeTool = foundTool;
      }
    }

    const targetPos: ToolPosition = {
      x: cmd.x !== undefined ? cmd.x : this.currentPos.x,
      y: cmd.y !== undefined ? cmd.y : this.currentPos.y,
      z: cmd.z !== undefined ? cmd.z : this.currentPos.z,
    };

    // Materialabtrag NUR bei Arbeitsvorschub (G01 / G1), NIEMALS bei G00 (Eilgang)
    if (cmd.type === 'G1' || cmd.type === 'G01') {
      this.interpolateCut(this.currentPos, targetPos, stockEngine);
    }

    this.currentPos = targetPos;
    this.currentCommandIndex++;

    return this.getPosition();
  }

  private interpolateCut(start: ToolPosition, end: ToolPosition, stockEngine: any) {
    // CNC-Drehkonvention: X im G-Code ist DURCHMESSER -> Radius = X / 2
    const startX = start.x / 2.0;
    const endX = end.x / 2.0;

    const dx = endX - startX;
    const dy = end.y - start.y;
    const dz = end.z - start.z;
    const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

    if (distance === 0) return;

    const steps = Math.max(1, Math.ceil(distance / this.stepSize));

    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      const cutX = startX + dx * t;
      const cutY = start.y + dy * t;
      const cutZ = start.z + dz * t;

      // Abtrags-Strategie basierend auf dem aktiven Werkzeug-Typ ausführen
      switch (this.activeTool.type) {
        case 'TURNING':
          this.applyTurningCut(cutX, cutZ, stockEngine);
          break;

        case 'MILLING':
        case 'DRILLING':
          this.applyPointCut(cutX, cutY, cutZ, stockEngine);
          break;
      }
    }
  }

  /**
   * Strategie 1: Rotationssymmetrischer Dreh-Abtrag
   * Räumt von der Schneidspitze (cutX) radial nach außen bis maxSweepRadius alles ab.
   */
  private applyTurningCut(cutX: number, cutZ: number, stockEngine: any) {
    const currentRadius = Math.abs(cutX);
    const maxRadius = this.activeTool.maxSweepRadius || 60.0;
    const angularSteps = 36;
    const radialStep = 2.0;

    for (let r = currentRadius; r <= maxRadius; r += radialStep) {
      for (let a = 0; a < angularSteps; a++) {
        const angle = (a / angularSteps) * Math.PI * 2;
        const rotX = Math.cos(angle) * r;
        const rotY = Math.sin(angle) * r;

        stockEngine.apply_cut(rotX, rotY, cutZ, this.activeTool.radius);
      }
    }
  }

  /**
   * Strategie 2: Punktueller Abtrag (Angetriebenes Werkzeug / Fräsen / Bohren)
   * Räumt punktgenau an den Koordianten (X, Y, Z) ohne 360-Grad-Rotation ab.
   */
  private applyPointCut(cutX: number, cutY: number, cutZ: number, stockEngine: any) {
    stockEngine.apply_cut(cutX, cutY, cutZ, this.activeTool.radius);
  }
}