"""ASTRA R08 - stage 4 for the v2 body: the eleven clips carried over from the v1 game file, unchanged.

    bvenv/bin/python experimental_02/src/game_clips_v2.py [game.blend]

v2 rebuilt the joints of the game Body mesh (armoured segments); it did not touch the skeleton - the
same 27 bones, names, hierarchy, rest and bind pose.  A clip is bone rotations plus the root's travel,
so the v1 clips play on the v2 body as they are.  They are appended from the v1 game file (not keyed
again by game_anim.py, whose floor-contact pass reads the mesh and would come out slightly different),
then checked:

  1. the two skeletons are equal (every bone's name, parent and rest matrix);
  2. every key of every curve of every clip equals the source key;
  3. the floor: the lowest point of the v2 meshes in each clip, frame by frame, against v1's.

Results: analysis/game_clips_v2.json.  The game file is saved with the clips in it.
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import game_anim as GA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "model", "astra_r08_exp02_game.blend")
V1 = os.path.join(ROOT, "model", "astra_r08_exp02_game_v1.blend")
CLIPS = [c[0] for c in GA.CLIPS]
MESHES = ("ASTRA_R08_Body", "ASTRA_R08_Head", "ASTRA_R08_Eyes")


def log(*a):
    print("[game_clips_v2]", *a, flush=True)


def skeleton():
    ao = bpy.data.objects[GA.ARMATURE]
    return {b.name: (b.parent.name if b.parent else None, np.array(b.matrix_local)) for b in ao.data.bones}


def curves(act):
    """{(data_path, index): keyframe array (frame, value, left handle, right handle, interpolation)}"""
    from bpy_extras import anim_utils
    out = {}
    for slot in act.slots:
        cb = anim_utils.action_get_channelbag_for_slot(act, slot)
        if cb is None:
            continue
        for fc in cb.fcurves:
            k = np.array([(p.co[0], p.co[1], p.handle_left[0], p.handle_left[1], p.handle_right[0], p.handle_right[1],
                           ["CONSTANT", "LINEAR", "BEZIER"].index(p.interpolation) if p.interpolation in ("CONSTANT", "LINEAR", "BEZIER") else 9)
                          for p in fc.keyframe_points], float)
            out[(fc.data_path, fc.array_index)] = k
    return out


def clip_facts(act):
    return dict(frame_range=[float(x) for x in act.frame_range], use_frame_range=bool(act.use_frame_range),
                cyclic=bool(getattr(act, "use_cyclic", False)), fake_user=bool(act.use_fake_user))


def lowest_per_frame(ao):
    """Lowest point (studs) of the posed meshes at every frame of every clip."""
    sc = bpy.context.scene
    out = {}
    obs = [bpy.data.objects[n] for n in MESHES]
    for name in CLIPS:
        GA.set_clip(ao, name)
        zs = []
        for f in range(sc.frame_start, sc.frame_end + 1):
            sc.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            z = 1e9
            for ob in obs:
                me = ob.evaluated_get(dg).to_mesh()
                co = np.zeros(len(me.vertices) * 3)
                me.vertices.foreach_get("co", co)
                ob.evaluated_get(dg).to_mesh_clear()
                M = np.array(ob.matrix_world)
                P = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
                z = min(z, float(P[:, 2].min()))
            zs.append(z)
        out[name] = zs
    GA.set_clip(ao, None)
    return out


def main(game=GAME):
    t0 = time.time()
    # ---- the source: v1 skeleton, clip curves, floor contact
    bpy.ops.wm.open_mainfile(filepath=V1)
    sk1 = skeleton()
    src = {n: curves(bpy.data.actions[n]) for n in CLIPS}
    facts1 = {n: clip_facts(bpy.data.actions[n]) for n in CLIPS}
    low1 = lowest_per_frame(bpy.data.objects[GA.ARMATURE])
    log(f"v1: {len(sk1)} bones, {len(src)} clips read ({time.time() - t0:.1f} s)")

    # ---- the v2 game file: skeleton check, then the clips appended
    bpy.ops.wm.open_mainfile(filepath=game)
    sk2 = skeleton()
    assert list(sk1) == list(sk2), "bone names or order differ"
    skel_diff = max(float(np.abs(sk1[b][1] - sk2[b][1]).max()) for b in sk1)
    assert all(sk1[b][0] == sk2[b][0] for b in sk1), "bone hierarchy differs"
    assert skel_diff < 1e-5, f"rest pose differs by {skel_diff}"
    for n in CLIPS:
        old = bpy.data.actions.get(n)
        if old is not None:
            bpy.data.actions.remove(old)
    with bpy.data.libraries.load(V1, link=False) as (s_, d_):
        d_.actions = list(CLIPS)
    rows = []
    worst = 0.0
    for n in CLIPS:
        act = bpy.data.actions[n]
        assert act.name == n, f"{n} arrived as {act.name}"
        act.use_fake_user = True
        got = curves(act)
        assert set(got) == set(src[n]), f"{n}: channels differ"
        d = max(float(np.abs(got[k] - src[n][k]).max()) if len(got[k]) else 0.0 for k in got)
        worst = max(worst, d)
        f2 = clip_facts(act)
        assert f2 == facts1[n], f"{n}: frame range / loop flag differ: {f2} vs {facts1[n]}"
        rows.append(dict(clip=n, channels=len(got), keys=int(sum(len(v) for v in got.values())), max_key_difference=d,
                         frames=int(f2["frame_range"][1] - f2["frame_range"][0]) + 1, loop=f2["cyclic"]))
        log(f"   {n}: {len(got)} channels, {rows[-1]['keys']} keys, identical to v1 (max difference {d:g})")
    assert worst == 0.0, f"a key changed in transit ({worst})"
    low2 = lowest_per_frame(bpy.data.objects[GA.ARMATURE])
    floor = {}
    for n in CLIPS:
        a, b = np.array(low1[n]), np.array(low2[n])
        floor[n] = dict(v1_lowest_studs=round(float(a.min()), 3), v2_lowest_studs=round(float(b.min()), 3),
                        largest_v2_minus_v1_studs=round(float((a - b).max()), 3))
    log("   floor (lowest point, studs; negative = below the floor): " +
        ", ".join(f"{n} v1 {floor[n]['v1_lowest_studs']} / v2 {floor[n]['v2_lowest_studs']}" for n in CLIPS))
    json.dump(dict(source=os.path.relpath(V1, ROOT), target=os.path.relpath(game, ROOT), bones=len(sk2),
                   skeleton_max_difference=skel_diff, clips=rows, floor=floor),
              open(os.path.join(ROOT, "analysis", "game_clips_v2.json"), "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=game, compress=True)
    log(f"saved {game}  ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(*args[:1])
