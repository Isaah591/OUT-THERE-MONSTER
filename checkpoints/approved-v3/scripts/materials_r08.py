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
    wear = g.math('MULTIPLY', g.math('MULTIPLY', convex, 0.25),
                  g.maprange(g.noise(14.0, 3.0, 0.6, coord=pos).outputs["Fac"], 0.55, 0.7))
    col = g.mix(wear, col, (0.32, 0.30, 0.28))
    occ = _occlusion(g, 0.04)
    col = g.mix(g.math('MAXIMUM', cavity, g.math('MULTIPLY', occ, 0.8)), col, (0.02, 0.012, 0.009))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.math('MULTIPLY', wear, 0.85), g.bsdf.inputs["Metallic"])
    g.link(g.maprange(wear, 0.0, 1.0, 0.82, 0.38), g.bsdf.inputs["Roughness"])
    g.val(g.bsdf, "Specular IOR Level", 0.3)
    g.link(g.bump(g.noise(60.0, 4.0, 0.6, coord=pos).outputs["Fac"], 0.4, 0.002), g.bsdf.inputs["Normal"])
    return m


# ---------------------------------------------------------------------------
# ASTRA R08 - MORE OPEN JAW sheet: flake mosaic, dark red exposed tissue, wet crimson mouth
# ---------------------------------------------------------------------------
def openjaw_rust(name="M_OJ_Rust"):
    """Cohesive dark reddish-brown rust shell (approved sheet): large plates (`flake`) outlined by
    thin lighter crackle (`crack`), dark corrosion patches, subtle worn plate edges; matte dark
    red-brown under-layers and dark crimson tissue in the wounds; per-plate roughness variation.
    Same geometry-driven grime/wear (convex, cavity, AO)."""
    m, g = _new(name)
    pos = _pos(g)
    layer, tissue, tear = _attr(g, "layer"), _attr(g, "tissue"), _attr(g, "tear")
    convex, cavity, blood = _attr(g, "convex"), _attr(g, "cavity"), _attr(g, "blood")
    flake, crack, socket = _attr(g, "flake"), _attr(g, "crack"), _attr(g, "socket")

    mott = g.noise(3.0, 7.0, 0.62, coord=pos)
    shell = g.ramp(mott.outputs["Fac"], [(0.34, (0.026, 0.007, 0.003)), (0.50, (0.060, 0.016, 0.006)),
                                         (0.64, (0.100, 0.027, 0.009)), (0.78, (0.142, 0.040, 0.012))])
    plate = g.ramp(flake, [(0.0, (0.030, 0.008, 0.004)), (0.35, (0.068, 0.018, 0.007)),
                           (0.70, (0.110, 0.030, 0.010)), (1.0, (0.158, 0.045, 0.013))])
    shell = g.mix(0.55, shell, plate)
    blot = g.maprange(g.noise(1.6, 3.0, 0.55, coord=pos).outputs["Fac"], 0.50, 0.68)
    shell = g.mix(g.math('MULTIPLY', blot, 0.6), shell, (0.014, 0.006, 0.004))          # dark corrosion patches
    ox = g.maprange(g.noise(0.9, 2.0, 0.5, coord=pos).outputs["Fac"], 0.56, 0.70)
    shell = g.mix(g.math('MULTIPLY', ox, 0.35), shell, (0.200, 0.058, 0.014))          # localized oxidation
    speck = g.maprange(g.noise(140.0, 2.0, 0.5, coord=pos).outputs["Fac"], 0.58, 0.66)
    shell = g.mix(g.math('MULTIPLY', speck, 0.6), shell, (0.010, 0.005, 0.003))
    shell = g.mix(g.math('MULTIPLY', crack, 0.55), shell, (0.240, 0.085, 0.026))        # thin orange crackle
    shell = g.mix(g.math('MULTIPLY', convex, 0.30), shell, (0.260, 0.095, 0.030))       # worn plate edges

    meat = g.ramp(g.noise(24.0, 5.0, 0.62, coord=_stretched(g, pos, 1.0, 1.0, 0.25)).outputs["Fac"],
                  [(0.30, (0.060, 0.008, 0.005)), (0.55, (0.130, 0.017, 0.010)), (0.75, (0.200, 0.034, 0.018))])
    deep = (0.045, 0.006, 0.005)
    under = g.mix(g.maprange(layer, 0.6, 0.95), meat, deep)
    col = g.mix(g.maprange(layer, 0.2, 0.3), shell, under)
    fringe = g.ramp(g.noise(60.0, 3.0, 0.6, coord=pos).outputs["Fac"],
                    [(0.35, (0.110, 0.040, 0.014)), (0.65, (0.200, 0.080, 0.028))])
    col = g.mix(g.math('MULTIPLY', tear, 0.6), col, fringe)
    fib = g.noise(26.0, 6.0, 0.65, coord=_stretched(g, pos, 1.0, 1.0, 0.18))
    wet = g.ramp(fib.outputs["Fac"], [(0.30, (0.045, 0.004, 0.004)), (0.55, (0.130, 0.012, 0.010)),
                                      (0.78, (0.230, 0.030, 0.022))])
    col = g.mix(tissue, col, wet)
    col = g.mix(g.math('MULTIPLY', blood, 0.85), col, (0.026, 0.004, 0.003))
    occ = _occlusion(g)
    grime = g.math('MAXIMUM', g.math('MULTIPLY', cavity, 0.7), g.math('MULTIPLY', occ, 0.85))
    exposed = g.math('MAXIMUM', g.maprange(layer, 0.2, 0.3), tissue)
    grime = g.math('MULTIPLY', grime, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', exposed, 0.7)))
    col = g.mix(grime, col, (0.007, 0.003, 0.002))
    col = g.mix(socket, col, (0.004, 0.002, 0.002))
    g.link(col, g.bsdf.inputs["Base Color"])

    # roughness: varies per plate and with the mottling; worn edges a little smoother; exposed
    # layers matte; tissue moist but not glossy; sockets / deep mouth fully matte
    rough = g.math('ADD', g.maprange(mott.outputs["Fac"], 0.3, 0.8, 0.70, 0.90), g.maprange(flake, 0.0, 1.0, -0.06, 0.06))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', convex, 0.10))
    rough = g.math('ADD', rough, g.math('MULTIPLY', g.maprange(layer, 0.2, 0.3), 0.12))
    rough = g.math('ADD', g.math('MULTIPLY', rough, g.math('SUBTRACT', 1.0, tissue)),
                   g.math('MULTIPLY', tissue, 0.55))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', blood, 0.2))
    g.link(g.math('ADD', rough, g.math('MULTIPLY', socket, 0.4), clamp=True), g.bsdf.inputs["Roughness"])
    # specular: dark exposed layers and tissue must not mirror the studio lights (they read grey)
    spec = g.math('SUBTRACT', 0.24, g.math('MULTIPLY', g.math('MAXIMUM', g.maprange(layer, 0.2, 0.3), tissue), 0.12))
    g.link(g.math('MULTIPLY', spec, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', socket, 0.95))),
           g.bsdf.inputs["Specular IOR Level"])
    grain = g.noise(85.0, 4.0, 0.6, coord=pos)
    h = g.math('ADD', grain.outputs["Fac"], g.math('MULTIPLY', crack, -1.0))
    h = g.math('ADD', h, g.math('MULTIPLY', tissue, g.math('MULTIPLY', fib.outputs["Fac"], 1.0)))
    g.link(g.bump(h, 0.22, 0.0025), g.bsdf.inputs["Normal"])
    return m


def openjaw_teeth(name="M_OJ_Teeth"):
    """Dirty, yellowed tusks (approved sheet): fluted bone with dark streaks running along each
    tooth, paler tips, dark grime at the roots, decay pits and old blood from the gums."""
    m, g = _new(name)
    pos = _pos(g)
    a = g.attr("tooth")
    t = g.n("ShaderNodeSeparateColor")
    g.link(a.outputs["Color"], t.inputs[0])
    tpos, tblood, tdecay = t.outputs[0], t.outputs[1], t.outputs[2]
    tint = a.outputs["Alpha"]
    n = g.noise(14.0, 5.0, 0.6, coord=pos).outputs["Fac"]
    col = g.ramp(n, [(0.30, (0.19, 0.12, 0.045)), (0.60, (0.32, 0.22, 0.085)), (0.85, (0.44, 0.32, 0.13))])
    col = g.mix(g.math('MULTIPLY', tint, 0.45), col, (0.22, 0.13, 0.04))                # per-tooth yellowing
    col = g.mix(g.maprange(tpos, 0.6, 1.0, 0.0, 0.25), col, (0.48, 0.37, 0.18))         # slightly paler tips
    flute = g.noise(26.0, 3.0, 0.5, coord=_stretched(g, pos, 1.0, 1.0, 0.08))           # streaks along the tooth
    col = g.mix(g.maprange(flute.outputs["Fac"], 0.47, 0.62, 0.0, 0.85), col, (0.070, 0.044, 0.018))
    root = g.maprange(tpos, 0.35, 0.0)
    col = g.mix(g.math('MULTIPLY', root, 0.9), col, (0.050, 0.028, 0.012))
    dec = g.math('MULTIPLY', tdecay, g.maprange(g.noise(9.0, 4.0, coord=pos).outputs["Fac"], 0.48, 0.6), clamp=True)
    col = g.mix(dec, col, (0.025, 0.015, 0.007))
    bl = g.maprange(g.math('SUBTRACT', g.math('MULTIPLY', tblood, 0.9), tpos), -0.06, 0.12)
    bl = g.math('MULTIPLY', bl, g.maprange(g.noise(11.0, 5.0, coord=pos, distortion=1.0).outputs["Fac"], 0.35, 0.6), clamp=True)
    col = g.mix(bl, col, (0.050, 0.004, 0.003))
    col = g.mix(g.math('MULTIPLY', _occlusion(g, 0.05), 0.8), col, (0.03, 0.018, 0.008))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.math('ADD', g.maprange(n, 0.3, 0.8, 0.58, 0.78), g.math('MULTIPLY', dec, 0.15)), g.bsdf.inputs["Roughness"])
    g.val(g.bsdf, "Specular IOR Level", 0.3)
    g.link(g.bump(g.math('ADD', flute.outputs["Fac"], g.math('MULTIPLY', n, 0.3)), 0.35, 0.003), g.bsdf.inputs["Normal"])
    return m


def wet_flesh(name, dark=(0.050, 0.005, 0.004), mid=(0.130, 0.014, 0.011), light=(0.240, 0.040, 0.028), rough=0.28,
              spec=0.5):
    """Wet crimson tissue (gums, cheek walls, tendons, tongue, throat). `spec` lowers the sheen of
    tissue deep in the mouth so it reads as a dark cavity instead of reflecting the studio."""
    m, g = _new(name)
    g.val(g.bsdf, "Specular IOR Level", spec)
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
