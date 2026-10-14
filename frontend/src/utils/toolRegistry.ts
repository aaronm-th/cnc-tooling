import { Tool } from '../types/tool';

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
    this.tools.set(tool.id, tool);
  }

  public getTool(id: string): Tool | undefined {
    return this.tools.get(id);
  }
}