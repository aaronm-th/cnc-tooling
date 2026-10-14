
declare module '*/calculator_engine.js' {
  export class VoxelStock {
    constructor(diameter: number, length: number, resolution: number);
    apply_cut(tool_x: number, tool_y: number, tool_z: number, tool_radius: number): void;
    get_active_voxel_count(): number;
  }
  
  export default function init(): Promise<void>;
}