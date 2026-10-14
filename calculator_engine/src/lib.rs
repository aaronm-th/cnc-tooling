use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct VoxelStock {
    width_x: f32,
    height_y: f32,
    length_z: f32,
    res_x: usize,
    res_y: usize,
    res_z: usize,
    grid: Vec<bool>,
}

#[wasm_bindgen]
impl VoxelStock {
    /// Erstellt ein zylindrisches Rohteil (z. B. für Drehen/Mill-Turn)
    #[wasm_bindgen]
    pub fn new_cylinder(diameter: f32, length: f32, resolution: usize) -> VoxelStock {
        let res_x = resolution;
        let res_y = resolution;
        let res_z = ((resolution as f32) * (length / diameter)) as usize;
        let total_voxels = res_x * res_y * res_z;
        let mut grid = vec![false; total_voxels];

        let radius = diameter / 2.0;
        let radius_sq = radius * radius;

        for z in 0..res_z {
            for y in 0..res_y {
                for x in 0..res_x {
                    let px = (x as f32 / res_x as f32 - 0.5) * diameter;
                    let py = (y as f32 / res_y as f32 - 0.5) * diameter;

                    if (px * px + py * py) <= radius_sq {
                        let idx = z * (res_x * res_y) + y * res_x + x;
                        grid[idx] = true;
                    }
                }
            }
        }

        VoxelStock {
            width_x: diameter,
            height_y: diameter,
            length_z: length,
            res_x,
            res_y,
            res_z,
            grid,
        }
    }

    /// Erstellt ein quaderförmiges Rohteil (z. B. für Fräsbearbeitung)
    #[wasm_bindgen]
    pub fn new_cuboid(width_x: f32, height_y: f32, length_z: f32, resolution: usize) -> VoxelStock {
        let res_x = resolution;
        let res_y = ((resolution as f32) * (height_y / width_x)) as usize;
        let res_z = ((resolution as f32) * (length_z / width_x)) as usize;

        let total_voxels = res_x * res_y * res_z;
        let grid = vec![true; total_voxels]; // Quader ist komplett mit Material gefüllt

        VoxelStock {
            width_x,
            height_y,
            length_z,
            res_x,
            res_y,
            res_z,
            grid,
        }
    }

    pub fn apply_cut(&mut self, tool_x: f32, tool_y: f32, tool_z: f32, tool_radius: f32) {
        let radius_sq = tool_radius * tool_radius;

        for z in 0..self.res_z {
            let cz = (z as f32 / self.res_z as f32) * self.length_z;
            if (cz - tool_z).abs() > tool_radius { continue; }

            for y in 0..self.res_y {
                let cy = (y as f32 / self.res_y as f32 - 0.5) * self.height_y;
                if (cy - tool_y).abs() > tool_radius { continue; }

                for x in 0..self.res_x {
                    let cx = (x as f32 / self.res_x as f32 - 0.5) * self.width_x;
                    let dx = cx - tool_x;
                    let dy = cy - tool_y;
                    let dz = cz - tool_z;

                    if (dx * dx + dy * dy + dz * dz) <= radius_sq {
                        let idx = z * (self.res_x * self.res_y) + y * self.res_x + x;
                        self.grid[idx] = false;
                    }
                }
            }
        }
    }

    fn solid(&self, x: i32, y: i32, z: i32) -> bool {
        if x < 0 || y < 0 || z < 0 { return false; }
        let (x, y, z) = (x as usize, y as usize, z as usize);
        if x >= self.res_x || y >= self.res_y || z >= self.res_z { return false; }
        self.grid[z * (self.res_x * self.res_y) + y * self.res_x + x]
    }

    pub fn get_mesh_vertices(&self) -> Vec<f32> {
        let (rx, ry, rz) = (self.res_x as i32, self.res_y as i32, self.res_z as i32);
        let (nx, ny, nz) = ((rx + 1) as usize, (ry + 1) as usize, (rz + 1) as usize);

        let cell_idx = |cx: i32, cy: i32, cz: i32| -> usize {
            ((cz + 1) as usize * ny + (cy + 1) as usize) * nx + (cx + 1) as usize
        };

        const EDGES: [(usize, usize); 12] = [
            (0, 1), (2, 3), (4, 5), (6, 7),
            (0, 2), (1, 3), (4, 6), (5, 7),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ];

        let mut cell_vertex: Vec<u32> = vec![u32::MAX; nx * ny * nz];
        let mut positions: Vec<[f32; 3]> = Vec::new();

        for cz in -1..rz {
            for cy in -1..ry {
                for cx in -1..rx {
                    let mut s = [false; 8];
                    for i in 0..8 {
                        s[i] = self.solid(
                            cx + (i & 1) as i32,
                            cy + ((i >> 1) & 1) as i32,
                            cz + ((i >> 2) & 1) as i32,
                        );
                    }
                    if s.iter().all(|&v| v) || s.iter().all(|&v| !v) { continue; }

                    let mut sum = [0.0f32; 3];
                    let mut n = 0.0f32;
                    for &(a, b) in EDGES.iter() {
                        if s[a] != s[b] {
                            let pa = [(a & 1) as f32, ((a >> 1) & 1) as f32, ((a >> 2) & 1) as f32];
                            let pb = [(b & 1) as f32, ((b >> 1) & 1) as f32, ((b >> 2) & 1) as f32];
                            for k in 0..3 { sum[k] += 0.5 * (pa[k] + pb[k]); }
                            n += 1.0;
                        }
                    }
                    let gx = cx as f32 + sum[0] / n;
                    let gy = cy as f32 + sum[1] / n;
                    let gz = cz as f32 + sum[2] / n;

                    positions.push([
                        (gx / self.res_x as f32 - 0.5) * self.width_x,
                        (gy / self.res_y as f32 - 0.5) * self.height_y,
                        (gz / self.res_z as f32) * self.length_z,
                    ]);
                    cell_vertex[cell_idx(cx, cy, cz)] = (positions.len() - 1) as u32;
                }
            }
        }

        let mut out: Vec<f32> = Vec::new();
        let mut emit_quad = |cells: [(i32, i32, i32); 4], flip: bool| {
            let mut v = [0u32; 4];
            for (i, &(cx, cy, cz)) in cells.iter().enumerate() {
                v[i] = cell_vertex[cell_idx(cx, cy, cz)];
            }
            if v.iter().any(|&i| i == u32::MAX) { return; }
            let tris: [[usize; 3]; 2] = if flip { [[0, 2, 1], [0, 3, 2]] } else { [[0, 1, 2], [0, 2, 3]] };
            for t in tris.iter() {
                for &i in t.iter() {
                    out.extend_from_slice(&positions[v[i] as usize]);
                }
            }
        };

        for z in -1..=rz {
            for y in -1..=ry {
                for x in -1..=rx {
                    let here = self.solid(x, y, z);
                    if here != self.solid(x + 1, y, z) {
                        emit_quad([(x, y - 1, z - 1), (x, y, z - 1), (x, y, z), (x, y - 1, z)], !here);
                    }
                    if here != self.solid(x, y + 1, z) {
                        emit_quad([(x - 1, y, z - 1), (x - 1, y, z), (x, y, z), (x, y, z - 1)], !here);
                    }
                    if here != self.solid(x, y, z + 1) {
                        emit_quad([(x - 1, y - 1, z), (x, y - 1, z), (x, y, z), (x - 1, y, z)], !here);
                    }
                }
            }
        }

        out
    }
}