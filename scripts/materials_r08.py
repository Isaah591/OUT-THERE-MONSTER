"""
Geometry-driven materials for the R08 high-fidelity rebuild (Cycles; all bakeable).

The sculpt writes per-vertex attributes (see sculpt.py) and the shaders read them, so colour,
roughness and relief follow the actual geometry:
    layer   shell 0 / first under-layer 0.5 / deep layer 1   -> rust strata colours
    tear    torn shell fringe                                 -> light tan fibrous edge
    tissue  exposed flesh                                     -> dark wet fibrous meat
    convex  ridges, facet edges, corners                      -> worn, lighter rust
    cavity  creases, valleys, wound floors (+ AO)             -> dark grime
    blood   stains and runs around wounds                     -> old dried blood
Colours are linear. World-space position drives the noise, so the scaled head matches.
"""
from monster_materials import G, _new


def _attr(g, name):
    return g.attr(name).outputs["Fac"]


def _pos(g):
    return g.n("ShaderNodeNewGeometry").outputs["Position"]


def _stretched(g, pos, sx, sy, sz):
    m = g.n("ShaderNodeMapping")
    m.inputs["Scale"].default_value = (sx, sy, sz)
    g.link(pos, m.inputs["Vector"])
    return m.outputs["Vector"]


def _occlusion(g, dist=0.07, samples=6):
    node = g.n("ShaderNodeAmbientOcclusion", samples=samples)
    g.val(node, "Distance", dist)
    return g.math('SUBTRACT', 1.0, node.outputs["AO"])        # 0 open .. 1 occluded


def r08_rust(name="M_R08_Rust"):
    m, g = _new(name)
    pos = _pos(g)
    layer, tissue, tear = _attr(g, "layer"), _attr(g, "tissue"), _attr(g, "tear")
    convex, cavity, blood = _attr(g, "convex"), _attr(g, "cavity"), _attr(g, "blood")

    # --- outer rust shell: granular, stone-like, multi-scale -----------------------------
    mott = g.noise(2.4, 7.0, 0.62, coord=pos)
    shell = g.ramp(mott.outputs["Fac"], [(0.36, (0.018, 0.008, 0.005)), (0.48, (0.050, 0.020, 0.009)),
                                         (0.58, (0.100, 0.040, 0.016)), (0.70, (0.155, 0.062, 0.024))])
    mott2 = g.noise(9.0, 5.0, 0.6, coord=pos)                                            # finer mottling
    shell = g.mix(g.math('MULTIPLY', g.maprange(mott2.outputs["Fac"], 0.50, 0.66), 0.55), shell,
                  (0.030, 0.013, 0.008))
    oxid = g.maprange(g.noise(0.55, 2.0, 0.5, coord=pos).outputs["Fac"], 0.47, 0.66)      # orange zones
    shell = g.mix(g.math('MULTIPLY', oxid, 0.5), shell, (0.235, 0.085, 0.022))
    brown = g.maprange(g.noise(0.9, 2.0, 0.5, coord=pos).outputs["Fac"], 0.52, 0.70)      # dull brown zones
    shell = g.mix(g.math('MULTIPLY', brown, 0.6), shell, (0.042, 0.022, 0.015))
    vor = g.n("ShaderNodeTexVoronoi")
    g.val(vor, "Scale", 6.5)
    g.link(pos, vor.inputs["Vector"])
    blot = g.math('MULTIPLY', g.maprange(vor.outputs["Distance"], 0.0, 0.28, 1.0, 0.0),
                  g.maprange(g.noise(3.0, 2.0, 0.5, coord=pos).outputs["Fac"], 0.5, 0.62))
    shell = g.mix(g.math('MULTIPLY', blot, 0.85), shell, (0.024, 0.010, 0.009))          # purple-brown blotches
    speck = g.maprange(g.noise(150.0, 2.0, 0.5, coord=pos).outputs["Fac"], 0.57, 0.66)
    shell = g.mix(g.math('MULTIPLY', speck, 0.85), shell, (0.016, 0.008, 0.005))        # dark pits
    fleck = g.maprange(g.noise(95.0, 2.0, 0.5, coord=pos).outputs["Fac"], 0.66, 0.72)
    shell = g.mix(g.math('MULTIPLY', fleck, 0.12), shell, (0.18, 0.08, 0.030))            # bright flecks
    streak = g.noise(4.5, 3.0, 0.55, coord=_stretched(g, pos, 6.0, 6.0, 0.6))
    shell = g.mix(g.math('MULTIPLY', g.maprange(streak.outputs["Fac"], 0.5, 0.7), 0.45), shell,
                  (0.030, 0.014, 0.009))                                                  # run-off streaks
    grime_p = g.maprange(g.noise(1.6, 3.0, 0.55, coord=pos).outputs["Fac"], 0.50, 0.68)  # dark grime patches
    shell = g.mix(g.math('MULTIPLY', grime_p, 0.55), shell, (0.016, 0.008, 0.006))
    shell = g.mix(g.math('MULTIPLY', convex, 0.25), shell, (0.20, 0.100, 0.045))        # worn edges

    # --- exposed under-layers -------------------------------------------------------------
    flake = g.noise(22.0, 5.0, 0.62, coord=pos)
    under = g.ramp(flake.outputs["Fac"], [(0.32, (0.050, 0.020, 0.010)), (0.52, (0.110, 0.045, 0.021)),
                                          (0.70, (0.180, 0.078, 0.036))])
    deep = g.ramp(g.noise(30.0, 4.0, 0.6, coord=pos).outputs["Fac"],
                  [(0.35, (0.012, 0.005, 0.003)), (0.70, (0.040, 0.015, 0.008))])
    under = g.mix(g.maprange(layer, 0.6, 0.95), under, deep)
    col = g.mix(g.maprange(layer, 0.2, 0.3), shell, under)

    # --- torn fringe: light tan fibrous edge of the shell -------------------------------
    fringe = g.ramp(g.noise(60.0, 3.0, 0.6, coord=pos).outputs["Fac"],
                    [(0.35, (0.19, 0.095, 0.040)), (0.65, (0.36, 0.200, 0.095))])
    col = g.mix(g.math('MULTIPLY', tear, 0.85), col, fringe)

    # --- tissue: dark fibrous meat, wetter ----------------------------------------------
    fib = g.noise(26.0, 6.0, 0.65, coord=_stretched(g, pos, 1.0, 1.0, 0.18))
    meat = g.ramp(fib.outputs["Fac"], [(0.30, (0.012, 0.002, 0.002)), (0.55, (0.050, 0.007, 0.006)),
                                       (0.75, (0.110, 0.024, 0.018))])
    col = g.mix(tissue, col, meat)

    # --- old blood and grime ----------------------------------------------------------------
    col = g.mix(g.math('MULTIPLY', blood, 0.85), col, (0.030, 0.004, 0.003))
    occ = _occlusion(g)
    grime = g.math('MAXIMUM', g.math('MULTIPLY', cavity, 0.75), g.math('MULTIPLY', occ, 0.85))
    col = g.mix(grime, col, (0.010, 0.005, 0.004))
    col = g.mix(_attr(g, "socket"), col, (0.004, 0.002, 0.002))                          # eye sockets
    g.link(col, g.bsdf.inputs["Base Color"])

    # --- roughness ------------------------------------------------------------------------
    rough = g.maprange(mott.outputs["Fac"], 0.3, 0.8, 0.80, 0.94)
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', convex, 0.14))
    rough = g.math('ADD', g.math('MULTIPLY', rough, g.math('SUBTRACT', 1.0, tissue)),
                   g.math('MULTIPLY', tissue, 0.38))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', blood, 0.25))
    g.link(rough, g.bsdf.inputs["Roughness"])

    # --- relief: grain + pitting on the shell, fibres in the meat ----------------------
    grain = g.noise(85.0, 4.0, 0.6, coord=pos)
    pit = g.n("ShaderNodeTexVoronoi")
    g.val(pit, "Scale", 45.0)
    g.link(pos, pit.inputs["Vector"])
    h = g.math('ADD', grain.outputs["Fac"], g.math('MULTIPLY', g.maprange(pit.outputs["Distance"], 0.0, 0.25), 0.6))
    h = g.math('ADD', h, g.math('MULTIPLY', tissue, g.math('MULTIPLY', fib.outputs["Fac"], 2.0)))
    g.link(g.bump(h, 0.22, 0.0025), g.bsdf.inputs["Normal"])
    return m


def r08_bar(name="M_R08_Bar"):
    """Rusted flat bar: dark scaly rust, orange blooms, bare worn steel on the edges."""
    m, g = _new(name)
    pos = _pos(g)
    convex, cavity = _attr(g, "convex"), _attr(g, "cavity")
    n = g.noise(9.0, 6.0, 0.62, coord=pos)
    col = g.ramp(n.outputs["Fac"], [(0.35, (0.040, 0.022, 0.016)), (0.55, (0.110, 0.045, 0.022)),
                                    (0.72, (0.260, 0.095, 0.032))])
    bloom = g.maprange(g.noise(3.0, 2.0, 0.5, coord=pos).outputs["Fac"], 0.55, 0.70)
    col = g.mix(g.math('MULTIPLY', bloom, 0.6), col, (0.36, 0.13, 0.035))
    wear = g.math('MULTIPLY', g.math('MULTIPLY', convex, 0.6),
                  g.maprange(g.noise(14.0, 3.0, 0.6, coord=pos).outputs["Fac"], 0.5, 0.7))
    col = g.mix(wear, col, (0.32, 0.30, 0.28))
    occ = _occlusion(g, 0.04)
    col = g.mix(g.math('MAXIMUM', cavity, g.math('MULTIPLY', occ, 0.8)), col, (0.02, 0.012, 0.009))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.math('MULTIPLY', wear, 0.85), g.bsdf.inputs["Metallic"])
    g.link(g.maprange(wear, 0.0, 1.0, 0.82, 0.38), g.bsdf.inputs["Roughness"])
    g.link(g.bump(g.noise(60.0, 4.0, 0.6, coord=pos).outputs["Fac"], 0.4, 0.002), g.bsdf.inputs["Normal"])
    return m


# ---------------------------------------------------------------------------
# ASTRA R08 - MORE OPEN JAW sheet: flake mosaic, dark red exposed tissue, wet crimson mouth
# ---------------------------------------------------------------------------
def openjaw_rust(name="M_OJ_Rust"):
    """Rust flake mosaic: per-plate tint (`flake`), dark cracks (`crack`), torn orange edges,
    dark red dried-meat under-layers and wet crimson tissue; same geometry-driven grime/wear."""
    m, g = _new(name)
    pos = _pos(g)
    layer, tissue, tear = _attr(g, "layer"), _attr(g, "tissue"), _attr(g, "tear")
    convex, cavity, blood = _attr(g, "convex"), _attr(g, "cavity"), _attr(g, "blood")
    flake, crack = _attr(g, "flake"), _attr(g, "crack")

    mott = g.noise(3.0, 7.0, 0.62, coord=pos)
    shell = g.ramp(mott.outputs["Fac"], [(0.36, (0.022, 0.008, 0.004)), (0.50, (0.060, 0.021, 0.008)),
                                         (0.62, (0.112, 0.039, 0.013)), (0.74, (0.165, 0.058, 0.018))])
    plate = g.ramp(flake, [(0.0, (0.024, 0.010, 0.006)), (0.35, (0.070, 0.025, 0.009)),
                           (0.70, (0.135, 0.046, 0.015)), (1.0, (0.200, 0.070, 0.020))])
    shell = g.mix(0.45, shell, plate, 'MULTIPLY')
    shell = g.mix(0.5, shell, plate)
    blot = g.maprange(g.noise(2.2, 3.0, 0.55, coord=pos).outputs["Fac"], 0.52, 0.68)
    shell = g.mix(g.math('MULTIPLY', blot, 0.55), shell, (0.020, 0.009, 0.006))          # dark corrosion
    speck = g.maprange(g.noise(140.0, 2.0, 0.5, coord=pos).outputs["Fac"], 0.57, 0.66)
    shell = g.mix(g.math('MULTIPLY', speck, 0.8), shell, (0.012, 0.006, 0.004))
    shell = g.mix(g.math('MULTIPLY', convex, 0.55), shell, (0.34, 0.15, 0.050))         # sunlit plate edges
    shell = g.mix(g.math('MULTIPLY', crack, 0.45), shell, (0.022, 0.009, 0.005))        # cracks between flakes

    meat = g.ramp(g.noise(24.0, 5.0, 0.62, coord=_stretched(g, pos, 1.0, 1.0, 0.25)).outputs["Fac"],
                  [(0.30, (0.060, 0.008, 0.006)), (0.55, (0.160, 0.022, 0.014)), (0.75, (0.280, 0.045, 0.025))])
    deep = (0.020, 0.004, 0.003)
    under = g.mix(g.maprange(layer, 0.6, 0.95), meat, deep)
    col = g.mix(g.maprange(layer, 0.2, 0.3), shell, under)
    fringe = g.ramp(g.noise(60.0, 3.0, 0.6, coord=pos).outputs["Fac"],
                    [(0.35, (0.20, 0.080, 0.025)), (0.65, (0.38, 0.170, 0.060))])
    col = g.mix(g.math('MULTIPLY', tear, 0.8), col, fringe)
    fib = g.noise(26.0, 6.0, 0.65, coord=_stretched(g, pos, 1.0, 1.0, 0.18))
    wet = g.ramp(fib.outputs["Fac"], [(0.30, (0.050, 0.004, 0.004)), (0.55, (0.170, 0.016, 0.012)),
                                      (0.78, (0.320, 0.050, 0.030))])
    col = g.mix(tissue, col, wet)
    col = g.mix(g.math('MULTIPLY', blood, 0.85), col, (0.030, 0.004, 0.003))
    occ = _occlusion(g)
    grime = g.math('MAXIMUM', g.math('MULTIPLY', cavity, 0.7), g.math('MULTIPLY', occ, 0.85))
    col = g.mix(grime, col, (0.008, 0.004, 0.003))
    col = g.mix(_attr(g, "socket"), col, (0.004, 0.002, 0.002))
    g.link(col, g.bsdf.inputs["Base Color"])

    rough = g.maprange(mott.outputs["Fac"], 0.3, 0.8, 0.78, 0.94)
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', convex, 0.12))
    rough = g.math('ADD', g.math('MULTIPLY', rough, g.math('SUBTRACT', 1.0, tissue)),
                   g.math('MULTIPLY', tissue, 0.66))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', blood, 0.25))
    g.link(rough, g.bsdf.inputs["Roughness"])
    g.link(g.math('SUBTRACT', 0.5, g.math('MULTIPLY', tissue, 0.32)), g.bsdf.inputs["Specular IOR Level"])
    grain = g.noise(85.0, 4.0, 0.6, coord=pos)
    h = g.math('ADD', grain.outputs["Fac"], g.math('MULTIPLY', crack, -1.5))
    h = g.math('ADD', h, g.math('MULTIPLY', tissue, g.math('MULTIPLY', fib.outputs["Fac"], 1.0)))
    g.link(g.bump(h, 0.25, 0.0025), g.bsdf.inputs["Normal"])
    return m


def wet_flesh(name, dark=(0.050, 0.005, 0.004), mid=(0.130, 0.014, 0.011), light=(0.240, 0.040, 0.028), rough=0.28):
    """Wet crimson tissue (gums, cheek walls, tendons, tongue, throat)."""
    m, g = _new(name)
    pos = _pos(g)
    n = g.noise(18.0, 6.0, 0.62, coord=pos)
    col = g.ramp(n.outputs["Fac"], [(0.32, dark), (0.55, mid), (0.75, light)])
    rot = g.maprange(g.noise(5.0, 3.0, 0.55, coord=pos).outputs["Fac"], 0.56, 0.68)
    col = g.mix(g.math('MULTIPLY', rot, 0.7), col, (0.014, 0.003, 0.003))
    col = g.mix(_occlusion(g, 0.04), col, (0.008, 0.001, 0.001))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.maprange(n.outputs["Fac"], 0.3, 0.8, rough, rough + 0.2), g.bsdf.inputs["Roughness"])
    g.link(g.bump(n.outputs["Fac"], 0.35, 0.004), g.bsdf.inputs["Normal"])
    return m
