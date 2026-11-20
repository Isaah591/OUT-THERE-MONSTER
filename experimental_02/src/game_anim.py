"""ASTRA R08 - Experimental Model 02: test animations (stage 4 of the Roblox build).

    bvenv/bin/python experimental_02/src/game_anim.py [game.blend]

Keys nine test clips on the armature (30 frames per second) and stores them as actions in the
.blend: Idle, Walk, Run, Attack, Lunge, HeadTrack, JawSnap, HitReact, Death.  They exist to prove
the rig - every joint is driven, the feet are planted by a two-bone solver, the jaw works on its
own bone - and to give Roblox something to play; they are not finished character animation.

Angles are in degrees about the creature's own axes as they lie in the rest pose, carried by the
parent bone:  x = about the left-right axis (+ pitches a forward-pointing bone down and swings a
hanging limb back), z = about the vertical (+ turns to the creature's left), y = about the
front-back axis (+ leans to the creature's left).  Distances are in studs.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from math import radians, sin, cos, pi, sqrt
import numpy as np
import bpy
from mathutils import Vector, Matrix, Euler, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "model", "astra_r08_exp02_game.blend")
ARMATURE = "ASTRA_R08"
FPS = 30
M_ = 1.0 / 0.28                 # metres -> studs


def sstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Rig:
    def __init__(self, ao, meshes=()):
        self.ao = ao
        self.meshes = list(meshes)
        self.dom = {}
        for ob in self.meshes:                     # the bone that carries each vertex most
            names = [vg.name for vg in ob.vertex_groups]
            dom = []
            for v in ob.data.vertices:
                g = max(v.groups, key=lambda e: e.weight)
                dom.append(names[g.group])
            self.dom[ob.name] = np.array(dom)
        self.pb = ao.pose.bones
        self.rest = {b.name: b.matrix_local.copy() for b in ao.data.bones}
        self.len = {b.name: b.length for b in ao.data.bones}
        self.last = {}
        for p in self.pb:
            p.rotation_mode = "QUATERNION"
        self.ankle = {S: self.rest[f"{S}Foot"].translation.copy() for S in ("Right", "Left")}
        self.pole = {}
        for S in ("Right", "Left"):
            h, k, a = (self.rest[f"{S}{n}"].translation for n in ("UpperLeg", "LowerLeg", "Foot"))
            u = (a - h).normalized()
            v = (k - h) - (k - h).dot(u) * u
            self.pole[S] = v.normalized()

    def reset(self):
        for p in self.pb:
            p.rotation_quaternion = Quaternion()
            p.location = (0.0, 0.0, 0.0)
            p.scale = (1.0, 1.0, 1.0)

    def update(self):
        bpy.context.view_layer.update()

    def r(self, name, x=0.0, y=0.0, z=0.0):
        R = Euler((radians(x), radians(y), radians(z)), "XYZ").to_matrix()
        M = self.rest[name].to_3x3()
        self.pb[name].rotation_quaternion = (M.inverted() @ R @ M).to_quaternion()

    def t(self, name, dx=0.0, dy=0.0, dz=0.0):
        M = self.rest[name].to_3x3()
        self.pb[name].location = M.inverted() @ Vector((dx, dy, dz))

    def aim(self, name, direction, xhint=None):
        """Point a bone along `direction` (armature space), its head staying where its parent has it."""
        self.update()
        p = self.pb[name]
        y = Vector(direction).normalized()
        xh = Vector(xhint) if xhint is not None else Vector(self.rest[name].to_3x3().col[0])
        x = (xh - xh.dot(y) * y).normalized()
        z = x.cross(y)
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = p.matrix.translation
        p.matrix = M

    def leg(self, S, ankle=None, d=(0.0, 0.0, 0.0), foot=0.0, toes=0.0):
        """Two-bone solve: put the ankle at `ankle` (default: where it rests) plus offset d, knee
        toward the leg's own rest side.  foot / toes: pitch of each, + = toes down."""
        up, lo, ft, to = (f"{S}UpperLeg", f"{S}LowerLeg", f"{S}Foot", f"{S}Toes")
        self.update()
        H = self.pb[up].matrix.translation.copy()
        T = (Vector(ankle) if ankle is not None else self.ankle[S].copy()) + Vector(d)
        # a pitched foot turns about the ankle: raise the ankle so the ball (toes down) or the heel
        # (toes up) stays on the floor instead of going through it
        fd = Vector(self.rest[ft].to_3x3().col[1])
        al = np.arcsin(min(max(-fd.z, -1.0), 1.0))
        if foot >= 0:
            T.z += 1.2 * self.len[ft] * (sin(al + radians(foot)) - sin(al))
        else:
            T.z += 0.36 * sin(radians(-foot))
        L1, L2 = self.len[up], self.len[lo]
        dist = min(max((T - H).length, abs(L1 - L2) + 1e-3), L1 + L2 - 1e-3)
        u = (T - H).normalized()
        T = H + u * dist
        a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
        h = sqrt(max(L1 * L1 - a * a, 0.0))
        pole = self.pole[S]
        pp = pole - pole.dot(u) * u
        pp = pp.normalized() if pp.length > 1e-6 else Vector((0.0, -1.0, 0.0))
        Kn = H + u * a + pp * h
        self.aim(up, Kn - H)
        self.aim(lo, T - Kn)
        self.aim(ft, Matrix.Rotation(radians(foot), 3, "X") @ Vector(self.rest[ft].to_3x3().col[1]))
        self.aim(to, Matrix.Rotation(radians(foot + toes), 3, "X") @ Vector(self.rest[to].to_3x3().col[1]))

    def family(self, name):
        out = [name]
        for c in self.ao.data.bones[name].children_recursive:
            out.append(c.name)
        return out

    def lowest(self, bones):
        """Lowest point (studs) of everything carried mainly by the given bones, as posed."""
        self.update()
        dg = bpy.context.evaluated_depsgraph_get()
        z = 1e9
        bs = np.array(sorted(bones))
        for ob in self.meshes:
            m = np.isin(self.dom[ob.name], bs)
            if not m.any():
                continue
            me = ob.evaluated_get(dg).data
            co = np.zeros(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            z = min(z, float(co.reshape(-1, 3)[m, 2].min()))
        return z

    def settle(self, bones, floor=-0.07, step=1.5, tries=60):
        """Lay limbs on the floor instead of through it: each bone in turn is raised about the
        horizontal axis across it until nothing it carries is below the floor (studs)."""
        for name in bones:
            fam = self.family(name)
            for _ in range(tries):
                if self.lowest(fam) >= floor:
                    break
                p = self.pb[name]
                M = p.matrix.copy()
                h = M.translation.copy()
                d = Vector(M.to_3x3().col[1])
                a = Vector((0.0, 0.0, 1.0)).cross(d)
                a = a.normalized() if a.length > 1e-4 else Vector((1.0, 0.0, 0.0))
                R = Matrix.Rotation(radians(-step), 4, a)
                p.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ M

    def ground(self, core, floor=-0.07):
        """Lift the pelvis if the trunk itself would sink into the floor; returns the lift (studs)."""
        z = self.lowest(core)
        if z < floor:
            p = self.pb["Pelvis"]
            M = self.rest["Pelvis"].to_3x3()
            p.location = p.location + M.inverted() @ Vector((0.0, 0.0, floor - z))
            return floor - z
        return 0.0

    def key(self, frame):
        self.update()
        for p in self.pb:
            q = p.rotation_quaternion.copy()
            if p.name in self.last and q.dot(self.last[p.name]) < 0:
                q.negate()
                p.rotation_quaternion = q
            self.last[p.name] = q
            p.keyframe_insert("rotation_quaternion", frame=frame)
            if p.name in ("Root", "Pelvis"):
                p.keyframe_insert("location", frame=frame)


# ------------------------------------------------------------------------------- the clips
# each clip: function(rig, u) -> poses the rig for phase u in [0, 1]; (name, seconds, loop, fn)

def base(g, dx=0.0, dy=0.0, dz=0.0, pitch=0.0, yaw=0.0, roll=0.0):
    """Pelvis offset (studs) and rotation; legs are solved afterwards by the caller."""
    g.reset()
    g.t("Pelvis", dx, dy, dz)
    g.r("Pelvis", pitch, roll, yaw)


def idle(g, u):
    b = sin(2 * pi * u)                  # breath
    s = sin(2 * pi * u + 1.1)
    base(g, dx=0.05 * s, dz=-0.035 * (0.5 + 0.5 * b))
    g.r("Spine", 1.2 * b)
    g.r("Chest", 1.6 * b, 0.0, 1.0 * s)
    g.r("Neck", -1.5 * b, 0.0, 2.5 * s)
    g.r("Head", -1.0 * b + 1.5 * sin(4 * pi * u), 1.5 * s, 3.0 * s)
    g.r("Jaw", 3.0 + 3.0 * sin(2 * pi * u - 0.6))
    for S, k in (("Right", 1.0), ("Left", -1.0)):
        g.r(f"{S}Shoulder", 0.0, 1.5 * b * k, 0.0)
        g.r(f"{S}UpperArm", 2.0 * s * k + 1.0 * b)
        g.r(f"{S}LowerArm", -2.0 * b)
        g.r(f"{S}Wrist", 2.0 * sin(2 * pi * u + 2.0))
        g.r(f"{S}Hand", 3.0 * sin(2 * pi * u + 2.6))
    g.leg("Right")
    g.leg("Left")


def gait(g, u, stride, lift, stance, bob, sway, lean, arm, neutral_back=0.10, crouch=0.0, jaw=4.0):
    """One cycle of a walk or run in place.  stride / lift / bob / sway in metres."""
    base(g, dx=-sway * M_ * sin(2 * pi * (u - 0.05)), dz=(-bob * cos(4 * pi * u) - crouch) * M_,
         pitch=lean * 0.35, yaw=5.0 * cos(2 * pi * u))
    g.r("Spine", lean * 0.4, 0.0, -3.5 * cos(2 * pi * u))
    g.r("Chest", lean * 0.25, 0.0, -4.5 * cos(2 * pi * u))
    g.r("Neck", -lean * 0.6 + 2.0 * cos(4 * pi * u), 0.0, 2.0 * cos(2 * pi * u))
    g.r("Head", -lean * 0.4 + 2.0 * cos(4 * pi * u + 0.6), 0.0, 1.0 * cos(2 * pi * u))
    g.r("Jaw", jaw + 3.0 * sin(4 * pi * u))
    c = cos(2 * pi * u)
    g.r("RightShoulder", 0.0, 0.0, 4.0 * c)
    g.r("RightUpperArm", arm * c - 4.0)
    g.r("RightLowerArm", -0.5 * arm * (1 - c) * 0.5 - 9.0)
    g.r("RightWrist", 0.35 * arm * cos(2 * pi * u - 0.7))
    g.r("RightHand", 0.45 * arm * cos(2 * pi * u - 1.2))
    g.r("LeftShoulder", 0.0, 0.0, 4.0 * c)
    g.r("LeftUpperArm", -1.3 * arm * c)
    g.r("LeftLowerArm", -0.8 * arm * (1 + c) * 0.5)
    g.r("LeftWrist", -0.4 * arm * cos(2 * pi * u - 0.7))
    g.r("LeftHand", -0.5 * arm * cos(2 * pi * u - 1.2))
    hipy = {"Right": g.rest["RightUpperLeg"].translation.y, "Left": g.rest["LeftUpperLeg"].translation.y}
    for S, ph in (("Right", 0.0), ("Left", 0.5)):
        f = (u + ph) % 1.0
        a0 = g.ankle[S].copy()
        a0.y = hipy[S] + neutral_back * M_
        if f < stance:                                   # on the ground, carried back under the body
            s = f / stance
            y = (-0.5 + s) * stride * M_
            z = 0.0
            foot = 22.0 * sstep((s - 0.72) / 0.28)       # heel peels off before the toe leaves
            toes = -foot
        else:                                            # in the air, swung forward
            s = (f - stance) / (1 - stance)
            y = (0.5 - sstep(s)) * stride * M_
            z = lift * M_ * sin(pi * s) ** 0.9
            foot = 22.0 * (1 - sstep(s / 0.45)) - 12.0 * sstep((s - 0.5) / 0.5) * (1 - sstep((s - 0.92) / 0.08))
            toes = 0.0
        g.leg(S, ankle=a0, d=(0.0, y, z), foot=foot, toes=toes)


def walk(g, u):
    gait(g, u, stride=1.00, lift=0.14, stance=0.60, bob=0.030, sway=0.045, lean=0.0, arm=11.0)


def run(g, u):
    gait(g, u, stride=1.50, lift=0.26, stance=0.40, bob=0.050, sway=0.030, lean=16.0, arm=24.0, crouch=0.07, jaw=11.0)


def blend(keys, u):
    """Piecewise smooth interpolation of dicts of numbers keyed by phase."""
    ks = sorted(keys)
    if u <= ks[0]:
        return dict(keys[ks[0]])
    for a, b in zip(ks[:-1], ks[1:]):
        if u <= b:
            w = sstep((u - a) / (b - a))
            A, B = keys[a], keys[b]
            return {k: A.get(k, 0.0) * (1 - w) + B.get(k, 0.0) * w for k in set(A) | set(B)}
    return dict(keys[ks[-1]])


def apply(g, v):
    """Pose from a flat dict: 'Bone.x' angles, 'px/py/pz' pelvis offsets in metres, 'Pelvis.x' ..."""
    base(g, dx=v.get("px", 0.0) * M_, dy=v.get("py", 0.0) * M_, dz=v.get("pz", 0.0) * M_,
         pitch=v.get("Pelvis.x", 0.0), yaw=v.get("Pelvis.z", 0.0), roll=v.get("Pelvis.y", 0.0))
    bones = {}
    for k, a in v.items():
        if "." in k and not k.startswith("Pelvis.") and not k.startswith("leg"):
            b, ax = k.split(".")
            bones.setdefault(b, {})[ax] = a
    for b, d in bones.items():
        g.r(b, d.get("x", 0.0), d.get("y", 0.0), d.get("z", 0.0))
    for S in ("Right", "Left"):
        g.leg(S, d=(v.get(f"leg{S}.dx", 0.0) * M_, v.get(f"leg{S}.dy", 0.0) * M_, v.get(f"leg{S}.dz", 0.0) * M_),
              foot=v.get(f"leg{S}.foot", 0.0), toes=v.get(f"leg{S}.toes", 0.0))


TRUNK = ["Pelvis", "Spine", "Chest", "RightShoulder", "LeftShoulder", "RightHip", "LeftHip"]
ARMS = ["RightUpperArm", "RightLowerArm", "RightWrist", "RightHand", "LeftUpperArm", "LeftLowerArm", "LeftWrist", "LeftHand"]


def floor_contact(g, head=False, trunk=False):
    """After a pose is set: nothing through the floor.  The trunk is lifted if it must be (and the
    legs solved again), then the arms - and the neck and head when asked - are laid on the floor."""
    if trunk and g.meshes:
        if g.ground(TRUNK) > 0:
            g.leg("Right")
            g.leg("Left")
    if g.meshes:
        g.settle(ARMS + (["Neck", "Head", "Jaw"] if head else []))


ATTACK = {   # a swipe with the long right arm
    0.00: {},
    0.24: {"px": 0.02, "py": 0.14, "pz": -0.06, "Pelvis.z": -8, "Spine.z": -12, "Chest.z": -16, "Chest.x": -4, "Neck.z": 14, "Head.z": 12,
           "Jaw.x": 6, "RightShoulder.z": -14, "RightUpperArm.x": 42, "RightUpperArm.y": 18, "RightLowerArm.x": -30, "RightWrist.x": -18,
           "RightHand.x": -14, "LeftUpperArm.x": -14, "LeftLowerArm.x": -18},
    0.42: {"px": -0.03, "py": -0.20, "pz": -0.10, "Pelvis.z": 9, "Spine.z": 14, "Spine.x": 8, "Chest.z": 20, "Chest.x": 8, "Neck.z": -14,
           "Head.z": -12, "Head.x": 4, "Jaw.x": 13, "RightShoulder.z": 16, "RightUpperArm.x": -72, "RightUpperArm.y": -10,
           "RightLowerArm.x": -18, "RightWrist.x": 16, "RightHand.x": 22, "LeftUpperArm.x": 18, "LeftLowerArm.x": -8},
    0.58: {"px": -0.04, "py": -0.16, "pz": -0.12, "Pelvis.z": 12, "Spine.z": 16, "Spine.x": 10, "Chest.z": 24, "Chest.x": 10, "Neck.z": -16,
           "Head.z": -14, "Jaw.x": -8, "RightShoulder.z": 18, "RightUpperArm.x": -48, "RightUpperArm.y": -34, "RightLowerArm.x": 6,
           "RightWrist.x": 26, "RightHand.x": 30, "LeftUpperArm.x": 22},
    1.00: {},
}
LUNGE = {    # a bite: draw back, throw the head forward, snap
    0.00: {},
    0.26: {"py": 0.24, "pz": -0.14, "Pelvis.x": -6, "Spine.x": -9, "Chest.x": -7, "Neck.x": -10, "Head.x": -14, "Jaw.x": 14,
           "RightUpperArm.x": 16, "LeftUpperArm.x": 20, "LeftLowerArm.x": -20},
    0.42: {"py": -0.42, "pz": -0.10, "Pelvis.x": 8, "Spine.x": 13, "Chest.x": 10, "Neck.x": 10, "Head.x": 4, "Jaw.x": 16,
           "RightUpperArm.x": -18, "RightLowerArm.x": -10, "LeftUpperArm.x": -26, "LeftLowerArm.x": -14, "legLeft.foot": 14, "legLeft.dz": 0.04},
    0.50: {"py": -0.46, "pz": -0.12, "Pelvis.x": 9, "Spine.x": 14, "Chest.x": 11, "Neck.x": 12, "Head.x": 9, "Jaw.x": -19,
           "RightUpperArm.x": -20, "RightLowerArm.x": -10, "LeftUpperArm.x": -28, "LeftLowerArm.x": -14, "legLeft.foot": 16, "legLeft.dz": 0.05},
    0.62: {"py": -0.40, "pz": -0.10, "Pelvis.x": 8, "Spine.x": 12, "Chest.x": 9, "Neck.x": 10, "Head.x": 7, "Head.z": 6, "Jaw.x": -19,
           "RightUpperArm.x": -16, "LeftUpperArm.x": -22, "legLeft.foot": 10, "legLeft.dz": 0.03},
    1.00: {},
}
HEADTRACK = {  # range of the neck and head: left, right, up, down
    0.00: {}, 0.14: {"Neck.z": 22, "Head.z": 30, "Head.y": 5, "Chest.z": 5}, 0.28: {},
    0.42: {"Neck.z": -22, "Head.z": -30, "Head.y": -5, "Chest.z": -5}, 0.56: {},
    0.68: {"Neck.x": -14, "Head.x": -20, "Jaw.x": 6}, 0.84: {"Neck.x": 12, "Head.x": 18}, 1.00: {},
}
JAWSNAP = {    # the jaw alone: open, shut, open, shut
    0.00: {}, 0.20: {"Jaw.x": 14}, 0.34: {"Jaw.x": -21, "Head.x": 2}, 0.52: {"Jaw.x": 11}, 0.66: {"Jaw.x": -21, "Head.x": 2},
    0.80: {"Jaw.x": -21}, 1.00: {},
}
HITREACT = {   # struck from the front
    0.00: {},
    0.16: {"py": 0.16, "pz": -0.05, "Pelvis.x": -4, "Spine.x": -11, "Chest.x": -9, "Chest.z": 9, "Neck.x": -8, "Head.x": -15, "Head.z": -12,
           "Jaw.x": 11, "RightUpperArm.x": 16, "RightLowerArm.x": -12, "LeftUpperArm.x": 22, "LeftUpperArm.y": 10, "LeftLowerArm.x": -18},
    0.44: {"py": -0.04, "pz": -0.03, "Spine.x": 5, "Chest.x": 4, "Chest.z": -3, "Head.x": 6, "Jaw.x": 2, "RightUpperArm.x": -6, "LeftUpperArm.x": -8},
    1.00: {},
}
DEATH = {      # staggers, the knees give, it folds forward onto its arm and face
    0.00: {},
    0.10: {"py": 0.20, "pz": -0.04, "Spine.x": -10, "Chest.x": -8, "Neck.x": -10, "Head.x": -18, "Head.z": 10, "Jaw.x": 14,
           "RightUpperArm.x": 14, "LeftUpperArm.x": 20, "LeftLowerArm.x": -16},
    0.30: {"py": 0.02, "pz": -0.34, "Pelvis.x": 6, "Spine.x": 10, "Chest.x": 8, "Chest.z": -8, "Neck.x": 8, "Head.x": 6, "Jaw.x": 10,
           "RightUpperArm.x": -10, "RightLowerArm.x": -14, "LeftUpperArm.x": -6, "LeftLowerArm.x": -10},
    0.52: {"py": -0.16, "pz": -0.74, "Pelvis.x": 16, "Pelvis.y": -5, "Spine.x": 20, "Chest.x": 14, "Chest.z": -12, "Neck.x": 12, "Head.x": 6,
           "Head.y": -10, "Jaw.x": 6, "RightShoulder.z": 8, "RightUpperArm.x": -34, "RightLowerArm.x": -22, "RightWrist.x": 20, "RightHand.x": 24,
           "LeftUpperArm.x": -24, "LeftUpperArm.y": -14, "LeftLowerArm.x": -30, "LeftWrist.x": 16, "legRight.foot": 10, "legLeft.foot": 18},
    0.66: {"py": -0.22, "pz": -0.86, "Pelvis.x": 22, "Pelvis.y": -8, "Spine.x": 24, "Chest.x": 16, "Chest.z": -14, "Neck.x": 16, "Head.x": 10,
           "Head.y": -16, "Jaw.x": -6, "RightShoulder.z": 10, "RightUpperArm.x": -40, "RightLowerArm.x": -26, "RightWrist.x": 26, "RightHand.x": 30,
           "LeftUpperArm.x": -30, "LeftUpperArm.y": -18, "LeftLowerArm.x": -34, "LeftWrist.x": 20, "LeftHand.x": 20, "legRight.foot": 12, "legLeft.foot": 22},
    0.76: {"py": -0.21, "pz": -0.83, "Pelvis.x": 21, "Pelvis.y": -8, "Spine.x": 23, "Chest.x": 15, "Chest.z": -14, "Neck.x": 14, "Head.x": 8,
           "Head.y": -15, "Jaw.x": 3, "RightShoulder.z": 10, "RightUpperArm.x": -39, "RightLowerArm.x": -25, "RightWrist.x": 25, "RightHand.x": 29,
           "LeftUpperArm.x": -29, "LeftUpperArm.y": -18, "LeftLowerArm.x": -33, "LeftWrist.x": 20, "LeftHand.x": 20, "legRight.foot": 12, "legLeft.foot": 22},
    1.00: {"py": -0.22, "pz": -0.87, "Pelvis.x": 22, "Pelvis.y": -9, "Spine.x": 24, "Chest.x": 16, "Chest.z": -14, "Neck.x": 17, "Head.x": 11,
           "Head.y": -17, "Jaw.x": 9, "RightShoulder.z": 10, "RightUpperArm.x": -40, "RightLowerArm.x": -26, "RightWrist.x": 26, "RightHand.x": 30,
           "LeftUpperArm.x": -30, "LeftUpperArm.y": -18, "LeftLowerArm.x": -34, "LeftWrist.x": 20, "LeftHand.x": 20, "legRight.foot": 12, "legLeft.foot": 22},
}

def clip(keys, head=False, trunk=False, contact=True):
    def fn(g, u):
        apply(g, blend(keys, u))
        if contact:
            floor_contact(g, head=head, trunk=trunk)
    return fn


def with_contact(fn):
    def f2(g, u):
        fn(g, u)
        floor_contact(g)
    return f2


CLIPS = [   # name, seconds, loops, pose function
    ("Idle", 3.0, True, with_contact(idle)),
    ("Walk", 1.0, True, with_contact(walk)),
    ("Run", 0.6, True, with_contact(run)),
    ("Attack", 1.2, False, clip(ATTACK)),
    ("Lunge", 1.1, False, clip(LUNGE, head=True)),
    ("HeadTrack", 3.4, False, clip(HEADTRACK, contact=False)),
    ("JawSnap", 1.0, False, clip(JAWSNAP, contact=False)),
    ("HitReact", 0.6, False, clip(HITREACT)),
    ("Death", 2.0, False, clip(DEATH, head=True, trunk=True)),
]


def make_actions(ao, step=2):
    """Key every clip (a key every `step` frames; Blender interpolates between)."""
    g = Rig(ao, [o for o in ao.children if o.type == "MESH" and o.name != "ASTRA_R08_Eyes"])
    if ao.animation_data is None:
        ao.animation_data_create()
    info = []
    for (name, secs, loop, fn) in CLIPS:
        old = bpy.data.actions.get(name)
        if old is not None:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        ao.animation_data.action = act
        g.last = {}
        n = int(round(secs * FPS))
        frames = sorted(set(list(range(0, n + 1, step)) + [n]))
        for f in frames:
            u = f / n
            fn(g, 0.0 if (loop and f == n) else u)
            g.key(f)
        act.frame_range = (0, n)
        act.use_frame_range = True
        try:
            act.use_cyclic = loop
        except Exception:
            pass
        info.append(dict(name=name, frames=n + 1, seconds=secs, fps=FPS, loop=loop, keys=len(frames)))
        print(f"[game_anim]    {name}: {n + 1} frames, {len(frames)} keys", flush=True)
    g.reset()
    ao.animation_data.action = None
    return info


def set_clip(ao, name):
    """Make one clip the armature's current animation (frame range set to match). None = rest."""
    sc = bpy.context.scene
    if ao.animation_data is None:
        ao.animation_data_create()
    if name is None:
        ao.animation_data.action = None
        for p in ao.pose.bones:
            p.rotation_quaternion = Quaternion()
            p.location = (0.0, 0.0, 0.0)
        return
    act = bpy.data.actions[name]
    ao.animation_data.action = act
    try:
        if ao.animation_data.action_slot is None and len(act.slots):
            ao.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    sc.frame_start, sc.frame_end = int(act.frame_range[0]), int(act.frame_range[1])


def main(path=GAME):
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    sc.render.fps = FPS
    ao = bpy.data.objects[ARMATURE]
    info = make_actions(ao)
    json.dump(dict(fps=FPS, clips=info), open(os.path.join(ROOT, "analysis", "game_animations.json"), "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("[game_anim] saved", path, flush=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(*args[:1])
