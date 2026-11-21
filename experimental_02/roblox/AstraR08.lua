-- AstraR08 (ModuleScript)
--
-- Plays the ASTRA R08 clips on the imported rig: one locomotion loop at a time (Idle / Walk /
-- Run / Chase), one-shot actions over it, and the layering clips (JawSnap, JawChatter on the Jaw
-- bone alone; HeadTrack on Neck and Head alone) over anything.  Also: procedural jaw opening and
-- head look-at on top of whatever is playing.
--
-- Written for the files of this package, in plain Lua syntax (checked with a Lua parser), but
-- not run in Roblox Studio before delivery - see README.md, "Scripts".
--
-- Usage (server Script):
--     local AstraR08 = require(path.to.AstraR08)
--     local rig = AstraR08.new(workspace.ASTRA_R08, { Idle = "rbxassetid://...", Walk = "...", ... })
--     rig:SetLocomotion("Walk", humanoidSpeedInStudsPerSecond)
--     rig:Play("Attack")
--     rig:Play("JawSnap")          -- moves the jaw only, over the walk
--     rig:Die()

local RunService = game:GetService("RunService")

local AstraR08 = {}
AstraR08.__index = AstraR08

-- Priority decides which clip wins on the bones it animates.  GroundSpeed (studs per second) is
-- the speed at which the in-place locomotion clips' feet do not slide.
AstraR08.Clips = {
	Idle = { Priority = Enum.AnimationPriority.Idle, Looped = true },
	Walk = { Priority = Enum.AnimationPriority.Movement, Looped = true, GroundSpeed = 5.95 },
	Run = { Priority = Enum.AnimationPriority.Movement, Looped = true, GroundSpeed = 22.3 },
	Chase = { Priority = Enum.AnimationPriority.Movement, Looped = true, GroundSpeed = 25.1 },
	Attack = { Priority = Enum.AnimationPriority.Action, Looped = false },
	Lunge = { Priority = Enum.AnimationPriority.Action, Looped = false },
	HitReact = { Priority = Enum.AnimationPriority.Action2, Looped = false },
	Death = { Priority = Enum.AnimationPriority.Action4, Looped = false },
	JawSnap = { Priority = Enum.AnimationPriority.Action3, Looped = false }, -- Jaw bone only
	JawChatter = { Priority = Enum.AnimationPriority.Action3, Looped = true }, -- Jaw bone only
	HeadTrack = { Priority = Enum.AnimationPriority.Action2, Looped = false }, -- Neck and Head only
}
AstraR08.Locomotion = { "Idle", "Walk", "Run", "Chase" }

-- Procedural limits (degrees).  Jaw: 0 = the sheet's open mouth (the rest pose), +16 = widest,
-- -21 = shut as far as the teeth allow.  Look-at: how far the neck and head together may turn.
AstraR08.Limits = { JawOpen = 16, JawShut = 21, Yaw = 55, Pitch = 25, NeckShare = 0.4, TurnRate = 6 }

local function findAnimator(model)
	local holder = model:FindFirstChildWhichIsA("Humanoid", true) or model:FindFirstChildWhichIsA("AnimationController", true)
	if not holder then
		holder = Instance.new("AnimationController")
		holder.Parent = model
	end
	local animator = holder:FindFirstChildOfClass("Animator")
	if not animator then
		animator = Instance.new("Animator")
		animator.Parent = holder
	end
	return animator
end

function AstraR08.new(model, animationIds)
	local self = setmetatable({}, AstraR08)
	self.Model = model
	self.Animator = findAnimator(model)
	self.Tracks = {}
	self.Bones = {}
	self.Current = nil
	for _, d in ipairs(model:GetDescendants()) do
		if d:IsA("Bone") then
			self.Bones[d.Name] = d
		end
	end
	for name, id in pairs(animationIds or {}) do
		local info = AstraR08.Clips[name]
		if info and type(id) == "string" and string.match(id, "%d") then
			local anim = Instance.new("Animation")
			anim.Name = name
			anim.AnimationId = id
			local track = self.Animator:LoadAnimation(anim)
			track.Priority = info.Priority
			track.Looped = info.Looped
			self.Tracks[name] = track
		end
	end
	return self
end

-- Idle / Walk / Run / Chase, one at a time.  speed (studs per second, optional) sets the playback
-- rate so the feet match the ground: speed / GroundSpeed.
function AstraR08:SetLocomotion(name, speed, fade)
	fade = fade or 0.25
	for _, clip in ipairs(AstraR08.Locomotion) do
		local t = self.Tracks[clip]
		if t and clip ~= name and t.IsPlaying then
			t:Stop(fade)
		end
	end
	local track = self.Tracks[name]
	if not track then
		return nil
	end
	if not track.IsPlaying then
		track:Play(fade)
	end
	local info = AstraR08.Clips[name]
	if speed and info.GroundSpeed then
		track:AdjustSpeed(math.max(speed, 0.05) / info.GroundSpeed)
	else
		track:AdjustSpeed(1)
	end
	self.Current = name
	return track
end

function AstraR08:Play(name, fade, weight, speed)
	local track = self.Tracks[name]
	if track then
		track:Play(fade or 0.1, weight or 1, speed or 1)
	end
	return track
end

function AstraR08:Stop(name, fade)
	local track = self.Tracks[name]
	if track and track.IsPlaying then
		track:Stop(fade or 0.15)
	end
end

function AstraR08:StopAll(fade)
	for _, track in pairs(self.Tracks) do
		if track.IsPlaying then
			track:Stop(fade or 0.15)
		end
	end
	self.Current = nil
end

-- seconds until a track knows its length (0 = it never loaded: check the animation ID)
function AstraR08.WaitForLength(track, timeout)
	local t0 = os.clock()
	while track.Length == 0 and os.clock() - t0 < (timeout or 10) do
		task.wait()
	end
	return track.Length
end

-- Death: everything else stops, the clip plays once and holds its last frame.
function AstraR08:Die(fade)
	self:StopAll(fade or 0.1)
	local track = self.Tracks.Death
	if not track then
		return nil
	end
	track:Play(fade or 0.1)
	task.spawn(function()
		if AstraR08.WaitForLength(track) == 0 then
			warn("AstraR08: the Death animation did not load")
			return
		end
		task.wait(math.max(track.Length - 0.05, 0))
		if track.IsPlaying then
			track:AdjustSpeed(0)
		end
	end)
	return track
end

-- ---------------------------------------------------------------------------------------------
-- Procedural jaw and look-at, added on top of the playing clips.  Rotations are built in world
-- space (about the model's own axes) and converted into each bone's frame, so they do not depend
-- on how Studio orients the bones' local axes.  Bone.Transform set by a script is seen where the
-- script runs: call this from a LocalScript for players, or test it in Studio's Run mode.

local function rotateBoneInWorld(bone, axis, angle)
	if angle == 0 then
		return
	end
	local w = bone.TransformedWorldCFrame
	local r = w - w.Position
	local delta = r:Inverse() * CFrame.fromAxisAngle(axis, angle) * r
	bone.Transform = bone.Transform * delta
end

function AstraR08:SetJawOpen(amount)
	-- -1 = shut, 0 = as animated, 1 = widest
	self.JawOpen = math.clamp(amount or 0, -1, 1)
end

function AstraR08:SetLookTarget(position)
	-- a Vector3 to look at, or nil to look ahead
	self.LookTarget = position
end

function AstraR08:EnableProcedural()
	if self._procedural then
		return
	end
	self.JawOpen = self.JawOpen or 0
	self._yaw, self._pitch = 0, 0
	local bones = { self.Bones.Neck, self.Bones.Head, self.Bones.Jaw }
	local base, written = {}, {}
	local L = AstraR08.Limits
	local function restore()
		-- take our offsets back off unless the Animator has written the bone since
		for i, b in ipairs(bones) do
			if b and written[i] and b.Transform == written[i] then
				b.Transform = base[i]
			end
			written[i] = nil
		end
	end
	local function apply(dt)
		for i, b in ipairs(bones) do
			if b then
				base[i] = b.Transform
			end
		end
		local pivot = self.Model:GetPivot()
		local up, right = pivot.UpVector, pivot.RightVector
		local neck, head, jaw = bones[1], bones[2], bones[3]
		-- look-at: yaw about the model's up axis (+ = toward the creature's left), then pitch about the
		-- creature's right axis turned by that yaw (+ = up)
		local wantYaw, wantPitch = 0, 0
		if self.LookTarget and head then
			local d = pivot:VectorToObjectSpace(self.LookTarget - head.TransformedWorldCFrame.Position)
			wantYaw = math.clamp(math.deg(math.atan2(-d.X, -d.Z)), -L.Yaw, L.Yaw)
			wantPitch = math.clamp(math.deg(math.atan2(d.Y, math.sqrt(d.X * d.X + d.Z * d.Z))), -L.Pitch, L.Pitch)
		end
		local k = math.min(1, (dt or 1 / 60) * L.TurnRate)
		self._yaw = self._yaw + (wantYaw - self._yaw) * k
		self._pitch = self._pitch + (wantPitch - self._pitch) * k
		if neck and head then
			local side = CFrame.fromAxisAngle(up, math.rad(self._yaw)):VectorToWorldSpace(right)
			for i, b in ipairs({ neck, head }) do
				local share = (i == 1) and L.NeckShare or (1 - L.NeckShare)
				rotateBoneInWorld(b, up, math.rad(self._yaw * share))
				rotateBoneInWorld(b, side, math.rad(self._pitch * share))
			end
		end
		-- jaw: about the creature's own left axis (opening drops the chin)
		if jaw and self.JawOpen ~= 0 then
			local deg = (self.JawOpen > 0) and self.JawOpen * L.JawOpen or self.JawOpen * L.JawShut
			rotateBoneInWorld(jaw, -right, math.rad(deg))
		end
		for i, b in ipairs(bones) do
			if b then
				written[i] = b.Transform
			end
		end
	end
	self._procedural = {
		RunService.PreAnimation:Connect(restore),
		RunService.PreSimulation:Connect(apply),
	}
end

function AstraR08:DisableProcedural()
	if self._procedural then
		for _, c in ipairs(self._procedural) do
			c:Disconnect()
		end
		self._procedural = nil
	end
end

return AstraR08
