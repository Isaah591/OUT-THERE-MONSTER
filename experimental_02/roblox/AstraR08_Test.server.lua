-- AstraR08_Test (Script)
--
-- Plays every ASTRA R08 clip in turn on the imported model, so the rig, the weights and each
-- imported animation can be checked by eye in Studio.  Put this Script and the AstraR08
-- ModuleScript in the same folder in ServerScriptService, paste the animation IDs below, press
-- Run (or Play) and watch the model.  The Output window names each clip as it starts.

local AstraR08 = require(script.Parent:WaitForChild("AstraR08"))

local MODEL_NAME = "ASTRA_R08" -- the imported Model in Workspace

-- Paste each published clip's asset id (rbxassetid://123...).  Clips left empty are skipped.
local IDS = {
	Idle = "",
	Walk = "",
	Run = "",
	Chase = "",
	Attack = "",
	Lunge = "",
	HitReact = "",
	Death = "",
	JawSnap = "",
	JawChatter = "",
	HeadTrack = "",
}

-- In Run mode (no player) the server's view is what Studio shows, so the procedural jaw and
-- look-at can be tested here too.  For players, call EnableProcedural from a LocalScript.
local TEST_PROCEDURAL = true

local model = workspace:WaitForChild(MODEL_NAME, 30)
if not model then
	warn("AstraR08_Test: no Model named " .. MODEL_NAME .. " in Workspace")
	return
end
local rig = AstraR08.new(model, IDS)

local loaded = 0
for name in pairs(rig.Tracks) do
	loaded = loaded + 1
end
if loaded == 0 then
	warn("AstraR08_Test: no animation IDs set - publish the clips and paste their IDs into IDS")
	return
end

local function say(text)
	print("[ASTRA R08] " .. text)
end

local function playOnce(name)
	local track = rig:Play(name)
	if track then
		say(name)
		if AstraR08.WaitForLength(track) == 0 then
			warn("AstraR08_Test: " .. name .. " did not load - check its animation ID")
			return
		end
		task.wait(track.Length + 0.3)
	end
end

while model.Parent do
	for _, name in ipairs({ "Idle", "Walk", "Run", "Chase" }) do
		if rig:SetLocomotion(name) then
			say(name .. " (loop)")
			task.wait(3)
		end
	end
	rig:SetLocomotion("Idle")
	playOnce("Attack")
	playOnce("Lunge")
	playOnce("HitReact")
	say("JawSnap over Idle (only the jaw should move differently)")
	playOnce("JawSnap")
	if rig:SetLocomotion("Chase") then
		say("JawChatter over Chase")
		rig:Play("JawChatter")
		task.wait(3)
		rig:Stop("JawChatter")
	end
	rig:SetLocomotion("Idle")
	say("HeadTrack over Idle (only the neck and head)")
	playOnce("HeadTrack")
	if TEST_PROCEDURAL then
		say("procedural: jaw open, shut, then look around a moving point")
		rig:EnableProcedural()
		rig:SetJawOpen(1)
		task.wait(1)
		rig:SetJawOpen(-1)
		task.wait(1)
		rig:SetJawOpen(0)
		local pivot = model:GetPivot()
		for i = 0, 120 do
			local a = math.rad(i * 6)
			rig:SetLookTarget(pivot:PointToWorldSpace(Vector3.new(math.sin(a) * 12, 8 + math.cos(a * 0.5) * 4, -15)))
			task.wait(1 / 30)
		end
		rig:SetLookTarget(nil)
		task.wait(0.5)
		rig:DisableProcedural()
	end
	say("Death (holds the last frame for 3 s)")
	rig:Die()
	task.wait(5)
	rig:StopAll(0.3)
	task.wait(1)
end
