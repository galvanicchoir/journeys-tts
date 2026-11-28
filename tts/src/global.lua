--[[ Journeys - TTS playtest framework (Global script)
     Content lives in the generated data block above this file (built from data/journeys-cards.xlsx).
     Adding an adventure, class or journey stage = add rows to the spreadsheet and rebuild; no Lua changes.
     Object-local coordinates: x and z run -1..1 across a tile; +z is the edge nearest the seated player. ]]

-- ------------------------------------------------------------------ layout
SEATS = {          -- seat color -> playmat centre and facing (180 = mat faces the south side)
  White = {pos = {-10, 1.05, -12.5}, rot = 180},
  Red   = {pos = { 10, 1.05, -12.5}, rot = 180},
  Green = {pos = {-10, 1.05,  12.5}, rot = 0},
  Blue  = {pos = { 10, 1.05,  12.5}, rot = 0},
}
SEAT_ORDER    = {"White", "Red", "Green", "Blue"}
TILE_SCALE    = 2
TILE_SPACING  = 5
BOARD_POS     = {-19, 1.05, -1}
BOARD_SCALE   = 5
-- Battlefield layout (must match build.py): Encounter Deck + Discard at the west end, six enemy stacks in a row
-- in the middle (all facing south), the 2x2 obstacle block at the east end.
ENC_DECK_POS  = {-11.6, 1.5, 1.8}
ENC_DISC_POS  = {-11.6, 1.5, -1.8}
OBSTACLE_SPOTS = {{9.0, 1.5, 1.8}, {11.6, 1.5, 1.8}, {9.0, 1.5, -1.8}, {11.6, 1.5, -1.8}}   -- the 2x2 obstacle block
STACK_X0      = -7.75              -- x of Stack 1 (west); the others follow every STACK_DX
STACK_DX      = 2.7
STACK_REAR_Z  = 2.3                -- centre of a stack's rear card (north end of the column)
STACK_STEP    = 0.65               -- how far each card in front sits below the one behind (shows its header + DMG counter)
STACK_SPAN    = 3.0                -- longest cascade (rear card centre to front card centre)
STACK_ZMIN, STACK_ZMAX = -2.45, 3.95   -- a stack column's extent along z
STACK_BAR_Z   = -3.05              -- aggro token + Aggro button row
BAG_POS       = {-19, 1.5, 5.6}    -- just above (north of) the journey board
-- Caches: face-down piles an adventure routes set-aside cards through. & = Wave, % = Bowl, $ = Fan
-- (a "#" in adventure text means the % cache). One column west of the set-aside bag.
CACHE_ORDER = {"&", "%", "$"}
CACHE_POS   = {["&"] = {-22.6, 1.5, 6.9}, ["%"] = {-22.6, 1.5, 10.4}, ["$"] = {-22.6, 1.5, 13.9}}
CACHE_NAME  = {["&"] = "Wave", ["%"] = "Bowl", ["$"] = "Fan"}
local function cacheKey(sig) if sig == "#" then return "%" end return sig end
ADV_TILE_POS  = {12, 1.2, 1.5}     -- where the chosen adventure tile goes
SUPPLY_X      = {22.5, 24.7}       -- token bags: two columns along the right edge of the table
SUPPLY_Z0     = 6.5                -- first bag (north end); the rest step south
SUPPLY_DZ     = 2.1
PHASES        = {"Encounter", "Hero", "Enemy", "Rally"}
DEFAULT_AP    = 2
BOSS_DIE      = {"A", "A", "A", "B", "B", "C"}   -- six faces
DIE_NAME      = {A = "Circle", B = "Triangle", C = "Square"}   -- how the faces are shown (cards use these shapes)
HAND_SIZE     = 4
BTN_PER_LOCAL = 520                -- button size units per local unit (measured in TTS)

STATE = {seats = {}, adventure = nil, journey = nil, turn = nil}

-- ------------------------------------------------------------------ helpers
local function copy(t) local r = {} for i, v in ipairs(t) do r[i] = v end return r end
local function shuffle(t)
  local r = copy(t)
  for i = #r, 2, -1 do local j = math.random(i); r[i], r[j] = r[j], r[i] end
  return r
end
local function expand(ids)            -- card ids -> one entry per physical copy
  local r = {}
  for _, id in ipairs(ids) do for _ = 1, (CARDS[id].qty or 1) do r[#r + 1] = id end end
  return r
end
local function cycle(list, cur, dir)
  local i = 1
  for k, v in ipairs(list) do if v == cur then i = k end end
  return list[((i - 1 + dir) % #list) + 1]
end
local function keys(t, field) local r = {} for _, v in ipairs(t) do r[#r + 1] = v[field] end return r end
local function first(tag) return getObjectsWithTag(tag)[1] end
-- Buttons and our generated images share one x direction; positionToWorld / snap points use the mirrored one.
-- Always go through this when turning image-layout coordinates into a world position.
local function imageToWorld(obj, x, y, z) return obj.positionToWorld({-x, y, z}) end
local function esc(s) return (s:gsub("%p", "%%%0")) end
local function T(x, y, z, ry, rz) return {posX = x or 0, posY = y or 0, posZ = z or 0, rotX = 0, rotY = ry or 180, rotZ = rz or 0, scaleX = 1, scaleY = 1, scaleZ = 1} end

local function sheetEntry(n)
  local s = SHEETS[n]
  return {FaceURL = s.face, BackURL = s.back, NumWidth = s.w, NumHeight = s.h, BackIsHidden = true, UniqueBack = false, Type = 0}
end

-- ---------------- Forge stickers (TTS decals). Gem badges sit left/right of the art, symmetric so a
-- mirrored card frame can't put them on the text; enhancement banners go across the lower card.
GEM_BY_KEY = {} for _, g in ipairs(GEMS) do GEM_BY_KEY[g.key] = g end
ENH_BY_ID = {} for _, e in ipairs(ENHANCEMENTS) do ENH_BY_ID[e.id] = e end
GEM_SLOTS = {{-0.78, 0}, {0.78, 0}}
ENH_POS = {0, 1.1}
GEMS_PER_CARD = 2
-- Sticker transform copied from stickers placed with TTS's own Decal tool on a card (posY 0.363, depth ~4.6 at
-- size 0.3). Sticker images must be web links (Steam Cloud) - local file links attach but never render.
STICKER_Y = 0.363
STICKER_DEPTH = 4.6
GEM_SIZE = 0.34

function stickerList(seat, id)                    -- setDecals() format
  local s = seat and STATE.seats[seat]
  if not s then return {} end
  local r = {}
  for i, key in ipairs((s.sockets or {})[id] or {}) do
    local g = GEM_BY_KEY[key]
    r[#r + 1] = {name = "Gem " .. g.label, url = g.image, position = {GEM_SLOTS[i][1], STICKER_Y, GEM_SLOTS[i][2]},
                 rotation = {90, 180, 0}, scale = {GEM_SIZE, GEM_SIZE, STICKER_DEPTH}}
  end
  for _, eid in ipairs((s.enh or {})[id] or {}) do
    local e = ENH_BY_ID[eid]
    if e then r[#r + 1] = {name = e.name, url = e.image, position = {ENH_POS[1], STICKER_Y, ENH_POS[2]},
                           rotation = {90, 180, 0}, scale = {1.7, 0.44, STICKER_DEPTH}} end
  end
  return r
end
local function decalData(list)                    -- setDecals() format -> saved-object format
  local r = {}
  for _, d in ipairs(list) do
    r[#r + 1] = {CustomDecal = {Name = d.name, ImageURL = d.url, Size = d.scale[1]},
      Transform = {posX = d.position[1], posY = d.position[2], posZ = d.position[3], rotX = d.rotation[1], rotY = d.rotation[2],
                   rotZ = d.rotation[3], scaleX = d.scale[1], scaleY = d.scale[2], scaleZ = d.scale[3]}}
  end
  return r
end

function cardData(id, tags, faceDown, seat)
  local c = CARDS[id]
  local d = {
    Name = "Card", Nickname = c.name, Description = c.text,
    GMNotes = JSON.encode({id = id, set = c.set, type = c.type, enc = c.enc, seat = seat}),
    CardID = c.sheet * 100 + c.idx, CustomDeck = {[c.sheet] = sheetEntry(c.sheet)},
    Hands = true, Tags = tags or {}, Transform = T(0, 0, 0, 180, faceDown and 180 or 0),
  }
  local dl = stickerList(seat, id)
  if #dl > 0 then d.AttachedDecals = decalData(dl) end
  return d
end

function deckData(ids, tags, nickname, gm, faceDown, seat)   -- nickname "" on purpose for play decks
  if #ids == 1 then local d = cardData(ids[1], tags, faceDown, seat) if nickname ~= "" then d.Nickname = nickname end return d end
  local contained, deckIds, decks = {}, {}, {}
  for i, id in ipairs(ids) do
    local d = cardData(id, tags, false, seat)
    contained[i] = d; deckIds[i] = d.CardID; decks[CARDS[id].sheet] = sheetEntry(CARDS[id].sheet)
  end
  return {Name = "Deck", Nickname = nickname or "", GMNotes = gm or "", DeckIDs = deckIds, CustomDeck = decks,
          ContainedObjects = contained, Tags = tags or {}, Hands = false, Transform = T(0, 0, 0, 180, faceDown and 180 or 0)}
end

function spawnCards(ids, pos, rotY, faceDown, tags, seat)
  if #ids == 0 then return end
  return spawnObjectData({data = deckData(ids, tags, "", nil, false, seat), position = pos, rotation = {0, rotY, faceDown and 180 or 0}})
end

function spawnLabel(text, pos, tags)
  return spawnObjectData({data = {
    Name = "3DText", Tags = tags or {}, Transform = T(0, 0, 0, 0),
    Text = {Text = text, colorstate = {r = 0.95, g = 0.88, b = 0.7}, fontSize = 40},
  }, position = pos, rotation = {90, 0, 0}})
end

local function tile(image, name, desc, gm, tags, pos, rotY, sx, sz, stretch)
  return {
    Name = "Custom_Tile", Nickname = name, Description = desc, GMNotes = gm, Tags = tags, Locked = true,
    Transform = {posX = pos[1], posY = pos[2], posZ = pos[3], rotX = 0, rotY = rotY, rotZ = 0, scaleX = sx, scaleY = 1, scaleZ = sz or sx},
    CustomImage = {ImageURL = image, ImageSecondaryURL = "", ImageScalar = 1.0, WidthScale = 0.0,
                   CustomTile = {Type = 0, Thickness = 0.1, Stackable = false, Stretch = stretch ~= false}},
  }
end

-- obj-attached button. squash compensates for non-uniform object scale (playmats).
local function button(obj, fn, label, x, z, w, h, fs, tip, bg, squash, fg)
  obj.createButton({
    click_function = fn, function_owner = self, label = label,
    position = {x, 0.3, z}, rotation = {0, 0, 0},
    scale = type(squash) == "table" and squash or {squash or 1, 1, 1},
    width = w, height = h, font_size = fs, tooltip = tip or "",
    color = bg or {0.16, 0.13, 0.22, 0.95}, font_color = fg or {0.96, 0.9, 0.74},
  })
end

function j_noop() end

-- ------------------------------------------------------------------ save / load
function onSave() return JSON.encode(STATE) end

function onLoad(saved)
  if saved and saved ~= "" then
    local ok, s = pcall(JSON.decode, saved)
    if ok and type(s) == "table" then STATE = s end
  end
  STATE.seats = STATE.seats or {}
  Wait.frames(initTable, 20)
end

local function defaultSeat()
  local cls = CLASS_ORDER[1]
  return {class = cls, subclass = CLASSES[cls].subclasses[1].name, ancestry = ANCESTRIES[1].name, level = 1, built = false}
end

OUR_HANDS = {a1f001 = true, a1f002 = true, a1f003 = true, a1f004 = true}   -- the four hand zones in the save file

-- The table adds its own default hand zones; remove every hand zone that isn't one of ours.
function removeDefaultHands()
  local ok, hands = pcall(function() return Hands.getHands() end)
  if not ok or not hands then return end
  for _, h in ipairs(hands) do
    if not OUR_HANDS[h.getGUID()] then h.destruct() end
  end
end

function initTable()
  removeDefaultHands()
  local haveMat = {}
  for _, m in ipairs(getObjectsWithTag("J_Mat")) do haveMat[m.getGMNotes()] = m end
  for _, color in ipairs(SEAT_ORDER) do
    STATE.seats[color] = STATE.seats[color] or defaultSeat()
    if haveMat[color] then drawMat(haveMat[color]) else spawnMat(color) end
  end
  for _, t in ipairs(getObjectsWithTag("J_AdvTile")) do destroyObject(t) end   -- tiles from older builds
  for _, b in ipairs(getObjectsWithTag("J_Board")) do drawBoard(b) end
  for _, t in ipairs(getObjectsWithTag("J_Track")) do drawTracker(t) end
  for _, b in ipairs(getObjectsWithTag("J_Boss")) do drawBoss(b) end
  for _, p in ipairs(getObjectsWithTag("J_Phase")) do destroyObject(p) end   -- tracker tiles from older builds
  if #getObjectsWithTag("J_Supply") == 0 then spawnSupply() end
  STATE.stacks, STATE.aggro, STATE.hp = STATE.stacks or {}, STATE.aggro or {}, STATE.hp or {}
  for g in pairs(STATE.hp) do                                   -- buttons aren't saved: put the counters back
    local o = getObjectFromGUID(g)
    if o then drawEnemyHP(o) else STATE.hp[g] = nil end
  end
  for k in pairs(STATE.stacks) do if not k:match("^S%d$") then STATE.stacks[k] = nil end end   -- old per-player stacks
  for _, p in ipairs(getObjectsWithTag("J_StackSlot")) do destroyObject(p) end      -- per-stack strips from an older build
  if #getObjectsWithTag("J_Battlefield") == 0 then spawnBattlefield() else drawBattlefield() end
  buildUI()
end

-- ------------------------------------------------------------------ adventures (started from the Encounters menu)
function startAdventure(id, color)
  if STATE.adventure then broadcastToColor("An adventure is already running. Reset the table first.", color, {1, 0.6, 0.2}) return end
  local adv = ADVENTURE_BY_ID[id]
  STATE.adventure = adv.id
  setupAdventure(adv)
  broadcastToAll("Adventure: " .. adv.name .. " (Level " .. adv.level .. ")", {0.95, 0.85, 0.55})
  buildUI()
end

local function players()
  local n = 0
  for _, s in pairs(STATE.seats) do if s.built then n = n + 1 end end
  if n == 0 then n = #getSeatedPlayers() end
  return math.max(n, 1)
end

local function starred(v)               -- "2*" -> 2 x players, "3" -> 3
  v = tostring(v)
  local n = tonumber(v:match("%d+")) or 0
  if v:find("%*") then n = n * players() end
  return n
end

function setupAdventure(adv)
  local tags = {"J_Setup"}
  local deck, bagItems, caches = {}, {}, {}
  -- rows like "cache:&:SDK-007" claim just those cards; the set's other rows skip them
  local claimed = {}
  for _, e in ipairs(adv.sets) do
    local only = e.use:match("^cache:[^:]+:(.+)$")
    if only then for id in only:gmatch("[^,%s]+") do claimed[id] = true end end
  end
  for _, e in ipairs(adv.sets) do
    local set = SETS[e.set]
    local ids, isAside = {}, {}
    for _, id in ipairs(e.set_aside or {}) do isAside[id] = true end
    local only = e.use:match("^cache:[^:]+:(.+)$")
    local onlySet
    if only then onlySet = {} for id in only:gmatch("[^,%s]+") do onlySet[id] = true end end
    for _, id in ipairs(expand(set.cards)) do
      if onlySet then
        if onlySet[id] then ids[#ids + 1] = id end
      elseif not claimed[id] then
        if isAside[id] then bagItems[#bagItems + 1] = cardData(id, tags) else ids[#ids + 1] = id end
      end
    end
    local cacheSig = e.use:match("^cache:([^:]+)")
    if cacheSig then
      local k = cacheKey(cacheSig)
      caches[k] = caches[k] or {}
      for _, id in ipairs(ids) do table.insert(caches[k], id) end
    elseif e.use == "all" then
      for _, id in ipairs(ids) do deck[#deck + 1] = id end
    elseif e.use:match("^random") then
      local n = tonumber(e.use:match("%d+")) or 0
      ids = shuffle(ids)
      for i = 1, math.min(n, #ids) do deck[#deck + 1] = ids[i] end
    elseif e.use == "staged" then        -- whole set waits in the bag until a journey stage shuffles it in
      bagItems[#bagItems + 1] = deckData(shuffle(ids), tags, set.name, JSON.encode({staged = e.set}), true)
    else                                  -- "setaside": individual cards in the bag
      for _, id in ipairs(ids) do bagItems[#bagItems + 1] = cardData(id, tags) end
    end
  end
  -- A start stage that moves the top of the encounter deck into a cache (The Silken Dark's A1) is done here, on the
  -- card lists, before anything spawns: moving cards out of a deck that is still loading can lose the whole deck in TTS.
  deck = shuffle(deck)
  local j = JOURNEYS[adv.id]
  local preDone = {}
  if j then
    for _, a in ipairs(j.nodes[j.start].actions) do
      local sig, n = a:match("^cachetop:([^:]+):?(.*)$")
      if sig then
        local k = cacheKey(sig)
        n = math.min(starred(n ~= "" and n or "1"), #deck)
        caches[k] = caches[k] or {}
        for _ = 1, n do table.insert(caches[k], table.remove(deck, 1)) end
        preDone[a] = true
        broadcastToAll("The top " .. n .. " encounter cards are shuffled into the " .. CACHE_NAME[k] .. " Cache (" .. k .. ").", {0.9, 0.8, 0.5})
      end
    end
  end
  spawnObjectData({data = {Name = "Bag", Nickname = "Set Aside", Description = "Cards this adventure keeps out of the encounter deck.",
    Tags = {"J_Setup", "J_SetAsideBag"}, ContainedObjects = bagItems, Transform = T(0, 0, 0, 180),
    ColorDiffuse = {r = 0.55, g = 0.4, b = 0.25}}, position = BAG_POS})
  spawnCards(deck, ENC_DECK_POS, 180, true, tags)
  spawnZone(ENC_DECK_POS, "J_EncZone"); spawnZone(ENC_DISC_POS, "J_DiscZone")
  for _, k in ipairs(CACHE_ORDER) do
    if caches[k] then
      local p = CACHE_POS[k]
      if #caches[k] > 0 then spawnCards(shuffle(caches[k]), p, 180, true, tags) end
      spawnCacheToken(k, tags)
    end
  end
  STATE.turn = {round = 0, phase = 0, die = nil}
  if j then
    STATE.journey = {adv = adv.id, node = nil, visited = {}, boss = nil, summoned = 0}
    spawnObjectData({data = tile(j.board, adv.name .. " - Journey", "", adv.id, {"J_Setup", "J_Board"},
      BOARD_POS, 180, BOARD_SCALE), callback_function = function(b)
        Wait.frames(function() enterNode(j.start, preDone) end, 5)
      end})
  end
end

function spawnZone(pos, tag)
  spawnObjectData({data = {Name = "ScriptingTrigger", Tags = {"J_Setup", tag},
    Transform = {posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 2.6, scaleY = 3, scaleZ = 3.6}},
    position = pos})
end

local function isEncounter(o)
  local gm = o.getGMNotes()
  if o.type == "Deck" then local c = o.getObjects()[1]; gm = c and (c.gm_notes or "") or "" end
  return gm:find('"enc":%s*true') ~= nil
end

function resetTable(color)
  for _, o in ipairs(getObjectsWithTag("J_Setup")) do destroyObject(o) end
  for _, o in ipairs(getAllObjects()) do
    if (o.type == "Card" or o.type == "Deck") and isEncounter(o) then destroyObject(o) end
  end
  STATE.journey = nil
  STATE.turn = nil
  STATE.stacks, STATE.aggro, STATE.hp = {}, {}, {}
  drawBattlefield()
  STATE.adventure = nil
  broadcastToAll("Table reset - choose an adventure from the Encounters menu.", {0.95, 0.85, 0.55})
  buildUI()
end

-- ------------------------------------------------------------------ journey board
local function zoneCards(tag)
  local z = first(tag); local r = {}
  if not z then return r end
  for _, o in ipairs(z.getObjects()) do if o.type == "Card" or o.type == "Deck" then r[#r + 1] = o end end
  return r
end
local function bagIndex(pattern)        -- index of the first bag item whose GM notes match
  local bag = first("J_SetAsideBag")
  if not bag then return end
  for _, e in ipairs(bag.getObjects()) do
    if (e.gm_notes or ""):find(pattern) then return bag, e.index end
  end
end

ACTIONS = {}
function ACTIONS.summon(args)            -- summon:<card id>:<n>
  local id, n = args[1], starred(args[2] or "1")
  for _ = 1, n do
    local bag, idx = bagIndex('"id":%s*"' .. esc(id) .. '"')
    if not bag then broadcastToAll("No set-aside " .. CARDS[id].name .. " left to summon.", {1, 0.6, 0.2}) return end
    local slot = STATE.journey.summoned
    STATE.journey.summoned = slot + 1
    local target = emptyStack(slot)           -- each summoned enemy starts its own stack
    local c = target and slotCenter(target) or {ENC_DECK_POS[1] + 2.6, 1.5, 0}
    bag.takeObject({index = idx, position = {c[1], 1.6, STACK_REAR_Z}, rotation = {0, 180, 0}, smooth = true,
                    callback_function = function(card) if target then addToStack(target, card, nil, nil) end end})
  end
end
-- Every encounter pile (deck or loose card) sitting on a spot: the encounter deck / discard spots on the board.
function encPilesAt(spot)
  local out = {}
  for _, o in ipairs(getAllObjects()) do
    if (o.type == "Deck" or o.type == "Card") and not o.held_by_color then
      local p = o.getPosition()
      if math.abs((p.x or p[1]) - spot[1]) < 1.3 and math.abs((p.z or p[3]) - spot[3]) < 1.8 and isEncounter(o) then
        out[#out + 1] = o
      end
    end
  end
  return out
end

-- Stack objects onto the encounter deck spot face down, merge them into one deck, shuffle; then call after(deck).
-- Merging is checked and repeated: a pile that was still landing when group() ran gets swept in on the next pass.
function rebuildEncounterDeck(list, after)
  local objs, seen = {}, {}
  for _, o in ipairs(list) do if o and not seen[o] and not o.isDestroyed() then seen[o] = true objs[#objs + 1] = o end end
  for i, o in ipairs(objs) do
    o.setRotation({0, 180, 180})
    o.setPosition({ENC_DECK_POS[1], ENC_DECK_POS[2] + i * 0.6, ENC_DECK_POS[3]})
  end
  local tries = 0
  local function finish()
    tries = tries + 1
    local piles = encPilesAt(ENC_DECK_POS)
    if #piles > 1 and tries < 4 then
      group(piles)
      Wait.time(finish, 0.8)
      return
    end
    local deck = piles[1]
    if deck and deck.type == "Deck" then deck.shuffle() Wait.time(function() if not deck.isDestroyed() then deck.shuffle() end end, 0.3) end
    if after then after(deck) end
  end
  Wait.time(function() group(objs) Wait.time(finish, 0.8) end, 1.0)
end

-- shuffle:SET,SET - the encounter deck, its discard pile and the named staged sets become one shuffled deck.
function ACTIONS.shuffle(args)
  local objs = {}
  for _, o in ipairs(encPilesAt(ENC_DECK_POS)) do objs[#objs + 1] = o end
  for _, o in ipairs(encPilesAt(ENC_DISC_POS)) do objs[#objs + 1] = o end
  local pending, sets = 0, 0
  local function arrived(o)
    if o then objs[#objs + 1] = o end
    pending = pending - 1
    if pending == 0 then rebuildEncounterDeck(objs) end
  end
  for set in tostring(args[1]):gmatch("[^,]+") do
    local bag, idx = bagIndex('"staged":%s*"' .. esc(set) .. '"')
    if bag then
      pending, sets = pending + 1, sets + 1
      bag.takeObject({index = idx, position = {ENC_DECK_POS[1], ENC_DECK_POS[2] + 6, ENC_DECK_POS[3]},
                      rotation = {0, 180, 180}, smooth = false, callback_function = arrived})
    end
  end
  if sets == 0 then rebuildEncounterDeck(objs) end
  broadcastToAll("The encounter deck and discard pile are shuffled together" .. (sets > 0 and " with the new cards." or "."), {0.9, 0.8, 0.5})
end
-- The cache pile for a sigil: the encounter pile sitting on its spot.
-- Run fn once obj has finished spawning and loading its images (TTS loses decks that are moved while loading).
function whenReady(obj, fn)
  if not obj then fn(obj) return end
  Wait.condition(function() fn(obj) end,
    function() return obj.isDestroyed() or (not obj.spawning and not obj.loading_custom) end, 10, function() fn(obj) end)
end

-- A round sigil token beside each cache pile, so players can tell & % $ apart.
CACHE_TOKEN_DX = -2.0
function spawnCacheToken(k, tags)
  local p = CACHE_POS[k]
  local t = tile(CACHE_TOKENS[k], CACHE_NAME[k] .. " Cache  " .. k, "The " .. CACHE_NAME[k] .. " Cache. Card text marks it with " .. k .. ".",
    "", tags, {p[1] + CACHE_TOKEN_DX, 1.05, p[3]}, 180, 0.55)
  t.CustomImage.CustomTile.Type = 2
  spawnObjectData({data = t})
end

-- track:<Name>:<rows> - a seat-by-row tracker board east of the Battlefield (The Silken Dark's Descent).
-- Each seat starts on the top row; click a square to move that seat's marker there.
TRACK_POS, TRACK_SCALE_TILE = {17.4, 1.05, 0}, 3.6
function ACTIONS.track(args)
  local js = STATE.journey
  local key = args[1] .. ":" .. (args[2] or "4")
  if not TRACKER_IMAGES[key] then return end
  if not (js.track and js.track.key == key) then
    js.track = {key = key, name = args[1], rows = tonumber(args[2]) or 4, at = {}, done = false}
  end
  for _, o in ipairs(getObjectsWithTag("J_Track")) do if o.getGMNotes() == key then drawTracker(o) return end end
  spawnObjectData({data = tile(TRACKER_IMAGES[key], args[1], "Click a square to move that hero's marker there.", key,
    {"J_Setup", "J_Track"}, TRACK_POS, 180, TRACK_SCALE_TILE), callback_function = function(o) drawTracker(o) end})
end

function drawTracker(obj)
  obj.clearButtons()
  local tr = STATE.journey and STATE.journey.track
  if not tr then return end
  local g = TRACK_GRID
  local cw, rh = (g.x1 - g.x0) / 4, (g.y1 - g.y0) / tr.rows
  for i, seat in ipairs(SEAT_ORDER) do
    local at = tr.at[seat] or 1
    for r = 1, tr.rows do
      local fx, fy = g.x0 + (i - 0.5) * cw, g.y0 + (r - 0.5) * rh
      local fn = "j_trk_" .. i .. "_" .. r
      _G[fn] = function(_, color, alt) moveTracker(seat, r) end
      local here = (at == r)
      local rgb = stringColorToRGB(seat)
      button(obj, fn, here and "●" or "", 2 * fx - 1, 2 * fy - 1, 110, 110, 80,
        here and (seat .. " is here") or ("Move " .. seat .. " here"),
        here and {rgb.r, rgb.g, rgb.b, 0.95} or {1, 1, 1, 0.04}, nil, here and {0.1, 0.08, 0.12} or nil)
    end
  end
end

function moveTracker(seat, row)
  local tr = STATE.journey and STATE.journey.track
  if not tr then return end
  tr.at[seat] = row
  for _, o in ipairs(getObjectsWithTag("J_Track")) do drawTracker(o) end
  local all, any = true, false
  for _, s in ipairs(SEAT_ORDER) do
    if (Player[s] and Player[s].seated) or (STATE.seats[s] and STATE.seats[s].built) then
      any = true
      if (tr.at[s] or 1) < tr.rows then all = false end
    end
  end
  if any and all and not tr.done then
    tr.done = true
    broadcastToAll("Every hero has reached the bottom. Journey Forward when you Rally.", {0.95, 0.85, 0.55})
  elseif not all then tr.done = false end
end

function cachePile(sig) return encPilesAt(CACHE_POS[cacheKey(sig)] or {0, 0, 999})[1] end

-- cachetop:<sigil>:<n> - shuffle the top n cards of the encounter deck into that cache (n may be starred)
function ACTIONS.cachetop(args)
  local k, n = cacheKey(args[1]), starred(args[2] or "1")
  local p = CACHE_POS[k]
  if not p then return end
  Wait.frames(function()
    whenReady(encPilesAt(ENC_DECK_POS)[1], function(deck)
    if not deck or deck.isDestroyed() then return end
    local moved = {}
    local have = cachePile(k)
    if have then moved[#moved + 1] = have end
    for i = 1, n do
      if deck == nil or deck.isDestroyed() then break end
      if deck.type == "Deck" then
        moved[#moved + 1] = deck.takeObject({position = {p[1], p[2] + i * 0.4, p[3]}, rotation = {0, 180, 180}, smooth = false})
      else
        deck.setRotation({0, 180, 180}) deck.setPosition({p[1], p[2] + i * 0.4, p[3]}) moved[#moved + 1] = deck break
      end
    end
    Wait.time(function()
      local pile = encPilesAt(p)
      if #pile > 1 then pile = group(pile) end
      Wait.time(function() local c = encPilesAt(p)[1] if c and c.type == "Deck" then c.shuffle() end end, 0.6)
    end, 0.8)
    broadcastToAll("The top " .. n .. " encounter cards are shuffled into the " .. CACHE_NAME[k] .. " Cache (" .. k .. ").", {0.9, 0.8, 0.5})
    end)
  end, 10)
end

-- awaits:<sigil> - discard from the encounter deck until an Elite comes up, spawn it in its own stack, then
-- attach the card waiting in that cache (What Awaits) behind it in the same stack.
function ACTIONS.awaits(args)
  local k = cacheKey(args[1] or "$")
  local function isElite(o) local c = CARDS[cardIdOf(o) or ""] return c and c.type == "Enemy" and (c.traits or ""):find("Elite") end
  local function step()
    local deck = encPilesAt(ENC_DECK_POS)[1]
    if not deck then broadcastToAll("The encounter deck ran out before an Elite came up.", {1, 0.6, 0.2}) return end
    local target = emptyStack(0)
    local card
    if deck.type == "Deck" then card = deck.takeObject({position = {ENC_DECK_POS[1], 3, ENC_DECK_POS[3]}, rotation = {0, 180, 0}, smooth = false})
    else card = deck card.setRotation({0, 180, 0}) end
    Wait.frames(function()
      if isElite(card) and target then
        local c = slotCenter(target)
        card.setPosition({c[1], 1.6, STACK_REAR_Z})
        addToStack(target, card, nil, nil)
        broadcastToAll((CARDS[cardIdOf(card)] or {name = "An Elite"}).name .. " awaits! (Stack " .. target:sub(2) .. ")", {0.9, 0.3, 0.3})
        local aw = cachePile(k)
        if aw then
          local w = aw
          if aw.type == "Deck" then w = aw.takeObject({position = {c[1], 2.2, STACK_REAR_Z + 1}, rotation = {0, 180, 0}, smooth = false})
          else aw.setRotation({0, 180, 0}) aw.setPosition({c[1], 2.2, STACK_REAR_Z + 1}) end
          Wait.frames(function()
            local list = STATE.stacks[target] or {}
            table.insert(list, 1, w.getGUID())               -- attached: tucked in behind the elite
            STATE.stacks[target] = list
            layoutStack(target)
          end, 5)
        end
      else
        card.setPosition({ENC_DISC_POS[1], 2, ENC_DISC_POS[3]})
        Wait.frames(step, 3)
      end
    end, 3)
  end
  step()
end

function ACTIONS.boss(args)              -- boss:<id>[:armor=<n>]
  local b = BOSSES[args[1]]
  local armor = 0
  for i = 2, #args do local k, v = args[i]:match("(%w+)=(.+)") if k == "armor" then armor = starred(v) end end
  local hp = b.per_player and b.health * players() or b.health
  STATE.journey.boss = {id = args[1], hp = hp, max = hp, armor = armor, power = 0}
  local board = first("J_Board")
  local j = JOURNEYS[STATE.journey.adv]
  local pos = imageToWorld(board, j.boss_pos[1], 0.3, j.boss_pos[2])
  spawnObjectData({data = tile(b.image, b.name, b.text, args[1], {"J_Setup", "J_Boss"}, pos, 180, j.boss_scale, j.boss_scale_z or j.boss_scale, false),
    callback_function = drawBoss})
  broadcastToAll(b.name .. " has been summoned! (" .. hp .. " health" .. (armor > 0 and (", " .. armor .. " armor") or "") .. ")", {0.9, 0.3, 0.3})
end

function enterNode(id, skip)
  local js = STATE.journey
  local node = JOURNEYS[js.adv].nodes[id]
  js.node = id; js.visited[id] = true
  local board = first("J_Board")
  if board then board.setDescription("Current stage: " .. id .. " " .. node.name .. "\n" .. node.rules) drawBoard(board) end
  broadcastToAll("Journey: " .. id .. " " .. node.name, {0.95, 0.85, 0.55})
  local keepTrack = {}
  for _, a in ipairs(node.actions) do local t = a:match("^track:(.+)$") if t then keepTrack[t] = true end end
  for _, o in ipairs(getObjectsWithTag("J_Track")) do
    if not keepTrack[o.getGMNotes()] then destroyObject(o) end
  end
  if js.track and not keepTrack[js.track.key] then js.track = nil end
  for _, a in ipairs(node.actions) do
    if not (skip and skip[a]) then
      local parts = {}
      for p in a:gmatch("[^:]+") do parts[#parts + 1] = p end
      local fn = ACTIONS[table.remove(parts, 1)]
      if fn then fn(parts) end
    end
  end
end

-- Only the stages you can journey to next get a (clickable) highlight.
function drawBoard(board)
  board.clearButtons()
  local js = STATE.journey
  if not js or not js.node then return end
  local j = JOURNEYS[js.adv]
  local reachable = {}
  for _, n in ipairs(j.nodes[js.node].next) do reachable[n] = true end
  for i, id in ipairs(j.order) do
    if reachable[id] then
      local n = j.nodes[id]
      button(board, "j_node_" .. i, "", n["local"][1], n["local"][2], j.node_w * BTN_PER_LOCAL + 10, j.node_h * BTN_PER_LOCAL + 10, 1,
        "Journey to " .. id .. " " .. n.name .. "\n" .. n.rules, {0.25, 0.85, 0.35, 0.35})
    end
  end
end

for i = 1, 20 do
  _G["j_node_" .. i] = function(obj, color)
    local js = STATE.journey
    local j = JOURNEYS[js.adv]
    local id = j.order[i]
    for _, n in ipairs(j.nodes[js.node].next) do if n == id then enterNode(id) return end end
  end
end

function drawBoss(obj)
  obj.clearButtons()
  local b = STATE.journey and STATE.journey.boss
  if not b then return end
  local tip = "Click: +1   |   Right-click: -1"
  -- the tile is landscape (non-uniform scale): keep the buttons a fixed size in the world, just off the tile's right edge
  local sc = obj.getScale()
  local K = 2.2                                   -- the scale the button sizes below were made for
  local sq, x, dz = {K / sc.x, 1, K / sc.z}, -(1 + 1.65 / sc.x), 0.88 / sc.z   -- image right = local -x
  button(obj, "j_bossHP",    "Health " .. b.hp .. " / " .. b.max, x, -dz, 700, 160, 90, tip, {0.5, 0.12, 0.12, 0.95}, sq)
  button(obj, "j_bossArmor", "Armor " .. b.armor,                  x, 0.0, 700, 160, 90, tip, nil, sq)
  button(obj, "j_bossPower", "Power +" .. b.power,                 x, dz,  700, 160, 90, tip, nil, sq)
end
local function bump(field, obj, alt, lo, hi)
  local b = STATE.journey.boss
  b[field] = math.max(lo, math.min(hi, b[field] + (alt and -1 or 1)))      -- click +1, right-click -1
  drawBoss(obj)
end
function j_bossHP(obj, color, alt)
  bump("hp", obj, alt, 0, STATE.journey.boss.max)
  if STATE.journey.boss.hp == 0 then broadcastToAll(BOSSES[STATE.journey.boss.id].name .. " is defeated!", {0.4, 0.9, 0.4}) end
end
function j_bossArmor(obj, color, alt) bump("armor", obj, alt, 0, 99) end
function j_bossPower(obj, color, alt) bump("power", obj, alt, 0, 99) end

-- ------------------------------------------------------------------ boss die
function rollBossDie()
  local face = BOSS_DIE[math.random(#BOSS_DIE)]
  if STATE.turn then STATE.turn.die = face end
  local msg = "Boss die: " .. DIE_NAME[face]
  local b = STATE.journey and STATE.journey.boss
  if b and b.hp > 0 then msg = msg .. "  -  " .. BOSSES[b.id].name .. ": " .. BOSSES[b.id].abc[({A = 1, B = 2, C = 3})[face]] end
  broadcastToAll(msg, {0.95, 0.45, 0.35})
  refreshTurnBar()
  return face
end
function j_ui_rollDie() rollBossDie() end

-- ------------------------------------------------------------------ round / phase tracker
local function builtSeats()
  local r = {}
  for _, c in ipairs(SEAT_ORDER) do if STATE.seats[c] and STATE.seats[c].built then r[#r + 1] = c end end
  return r
end
local function matOf(seat) for _, m in ipairs(getObjectsWithTag("J_Mat")) do if m.getGMNotes() == seat then return m end end end
local function quantity(o) if not o then return 0 elseif o.type == "Deck" then return o.getQuantity() else return 1 end end

-- Labels for the turn bar (bottom-right, above the launcher). Display only: it never moves cards.
local function phaseLabel()
  local t = STATE.turn
  if not t or t.round == 0 then return "Start Round 1   >" end
  return "Round " .. t.round .. "  -  " .. PHASES[t.phase]
end
local function dieLabel()
  local t = STATE.turn
  return (t and t.die) and ("Boss Die: " .. (DIE_NAME[t.die] or t.die)) or "Roll Boss Die"
end
-- Rebuild the whole Global UI so every player sees the same round / phase / die.
function refreshTurnBar()
  if STATE.turn then buildUI() end
end

-- Draw up to hand size. With reshuffle (Rally): draw the deck dry, shuffle the discard pile in as the new
-- deck, then keep drawing.
local function dealTo(seat, pile, n)
  if n <= 0 or not pile then return end
  if pile.type == "Deck" then pile.deal(n, seat)
  else pile.setPosition(Player[seat].getHandTransform().position) end
end
function drawToHandSize(seat, reshuffle)
  local deck = seatPile(seat, "Deck")
  local inHand = 0
  local ok, hand = pcall(function() return Player[seat].getHandObjects() end)
  if ok and hand then for _, o in ipairs(hand) do if o.type == "Card" then inHand = inHand + 1 end end end
  local need = HAND_SIZE - inHand
  if need <= 0 then return end
  local n = math.min(need, quantity(deck))
  dealTo(seat, deck, n)
  local rest = need - n
  if rest <= 0 then return end
  local discard = reshuffle and seatPile(seat, "Discard")
  if not discard then broadcastToAll(seat .. "'s deck is out of cards.", {1, 0.6, 0.2}) return end
  local mat, sl = matOf(seat), slot("Deck")
  discard.setRotation({0, mat.getRotation().y, 180})                 -- face down
  discard.setPositionSmooth(imageToWorld(mat, sl.x, 0.6, sl.z), false, true)
  broadcastToAll(seat .. " shuffles their discard pile into a new deck.", stringColorToRGB(seat))
  Wait.time(function()
    if discard == nil or discard.isDestroyed() then return end
    if discard.type == "Deck" then discard.shuffle() end
    local avail = quantity(discard)
    dealTo(seat, discard, math.min(rest, avail))
    if avail < rest then broadcastToAll(seat .. " has no more cards to draw.", {1, 0.6, 0.2}) end
  end, 0.8)
end

-- Round / phase tracker. Click = next phase, right-click = back one. Nothing else happens.
function stepPhase(dir)
  local t = STATE.turn
  if not t then return end
  if dir > 0 then
    t.phase = t.phase % #PHASES + 1
    if t.phase == 1 then t.round = t.round + 1 t.die = nil end
  else
    if t.round == 0 or (t.round == 1 and t.phase == 1) then t.round, t.phase = 0, 0
    elseif t.phase == 1 then t.phase = #PHASES t.round = t.round - 1
    else t.phase = t.phase - 1 end
  end
  if t.round > 0 then broadcastToAll("Round " .. t.round .. " - " .. PHASES[t.phase], {0.95, 0.85, 0.55}) end
  t.acted = {}                                   -- who has pressed this phase's highlighted button
  refreshTurnBar()
  refreshMats()
end

-- Phase highlights: in the Encounter phase each player's Draw Encounter button glows, in the Rally phase their
-- Rally button does, until that player presses it.
function phaseWants(seat, phaseName)
  local t = STATE.turn
  return t and t.round > 0 and PHASES[t.phase] == phaseName and not (t.acted and t.acted[seat]) and true or false
end
function markActed(seat, phaseName)
  local t = STATE.turn
  if t and t.round > 0 and PHASES[t.phase] == phaseName then
    t.acted = t.acted or {}
    if not t.acted[seat] then t.acted[seat] = true local m = matOf(seat) if m then drawMat(m) end end
  end
end
function refreshMats() for _, m in ipairs(getObjectsWithTag("J_Mat")) do drawMat(m) end end
function j_ui_nextPhase(player, btn) stepPhase(btn == "-2" and -1 or 1) end

-- ------------------------------------------------------------------ token supply
-- One token / bag object. Counter = TTS's built-in number counter (its own +/- buttons), tinted.
local function tokenData(t, pos, rotY)
  if t.kind == "counter" then
    return {Name = "Counter", Nickname = t.name, Tags = {"J_Token"}, Locked = false,
      ColorDiffuse = {r = t.rgb[1], g = t.rgb[2], b = t.rgb[3]}, Transform = T(pos[1], pos[2], pos[3], rotY)}
  end
  local tok = tile(t.image, t.name, "", "", {"J_Token"}, pos, rotY, 0.45)
  tok.Locked = false
  tok.CustomImage.CustomTile.Type = 2                     -- round
  tok.CustomImage.CustomTile.Thickness = 0.15
  tok.CustomImage.CustomTile.Stackable = (t.kind == "stack")
  return tok
end
local function tokenBag(t, pos, rotY, tags)
  return {Name = "Infinite_Bag", Nickname = t.name,
    Description = t.kind == "counter" and "Numbered counter (Horde bodies, damage, anything)." or ("Drag out " .. t.name .. " tokens. Stack them to count."),
    Tags = tags, Locked = true, ContainedObjects = {tokenData(t, {0, 0, 0}, 180)},
    ColorDiffuse = {r = t.rgb[1], g = t.rgb[2], b = t.rgb[3]}, Transform = T(pos[1], pos[2], pos[3], rotY)}
end

function spawnSupply()
  local i = 0
  for _, t in ipairs(TOKENS) do
    if t.owner == "" then
      i = i + 1
      spawnObjectData({data = tokenBag(t, {SUPPLY_X[(i - 1) % 2 + 1], 1.5, SUPPLY_Z0 - math.floor((i - 1) / 2) * SUPPLY_DZ}, 180, {"J_Supply"})})
    end
  end
end

-- Class tokens (Ember, Renown, Stealth...) go on the top-left of the playmat of a character that uses them.
CLASS_TOKEN_SPOTS = {{-0.86, -0.62}, {-0.68, -0.62}, {-0.50, -0.62}}
function spawnClassTokens(seat, sets)
  local mat = matOf(seat)
  local n, rot = 0, mat.getRotation().y
  for _, t in ipairs(TOKENS) do
    if t.owner ~= "" and sets[t.owner] then
      n = n + 1
      local spot = CLASS_TOKEN_SPOTS[n] or CLASS_TOKEN_SPOTS[#CLASS_TOKEN_SPOTS]
      local w = imageToWorld(mat, spot[1], 0.6, spot[2])
      local pos = {w.x or w[1], w.y or w[2], w.z or w[3]}
      local tags = {"J_Seat_" .. seat}
      if t.kind == "single" then
        local d = tokenData(t, pos, rot) d.Tags = {"J_Token", tags[1]}
        spawnObjectData({data = d})
      else
        spawnObjectData({data = tokenBag(t, pos, rot, tags)})
      end
    end
  end
end

-- ------------------------------------------------------------------ playmats / character creation
local MAT_SX, MAT_SZ = MAT_LAYOUT.w / 2, MAT_LAYOUT.d / 2
local SQUASH = MAT_SZ / MAT_SX              -- keeps button text from stretching on the wide mat
TRACK_X = 0.84                              -- Health / Shield / Actions: top-right corner of the mat (image coords)
TRACK_Z = {-0.84, -0.72, -0.60}
RALLY_POS = {0.80, 0.87}                  -- Rally: bottom-right, under the Discard slot
DRAW_POS  = {0.57, 0.87}                  -- Draw Encounter: next to Rally, under the Deck slot
local TRACK_K = 0.5                         -- shrink factor for the tracker buttons
local TRACK_SCALE = {SQUASH * TRACK_K, 1, TRACK_K}

function spawnMat(color)
  local s = SEATS[color]
  local d = tile(MAT_IMAGES[color], color .. " - Playmat", "Playmat for the " .. color .. " seat",
    color, {"J_Mat"}, s.pos, s.rot, MAT_SX, MAT_SZ, false)
  spawnObjectData({data = d, callback_function = drawMat})
end

function slot(name)
  for _, s in ipairs(MAT_LAYOUT.slots) do if s.name == name then return s end end
end

local function seatOf(obj) local c = obj.getGMNotes() return c, STATE.seats[c] end

-- Is a world position on a given slot of this mat? (slot ~ one card footprint, in mat-local units)
local function onSlot(mat, pos, name)
  local sl, lp = slot(name), mat.positionToLocal(pos)
  return math.abs(lp.x + sl.x) < 0.13 and math.abs(lp.z - sl.z) < 0.3     -- local x is the mirror of image x
end
-- The card/deck sitting on a seat's slot (the biggest pile if several). Found by position, not by zones.
function seatPile(seat, name)
  local mat = matOf(seat)
  if not mat then return end
  local best, bestN
  for _, o in ipairs(getAllObjects()) do
    if (o.type == "Card" or o.type == "Deck") and not o.held_by_color and onSlot(mat, o.getPosition(), name) then
      local n = o.type == "Deck" and o.getQuantity() or 1
      if not best or n > bestN then best, bestN = o, n end
    end
  end
  return best
end

function drawMat(obj)
  local color, s = seatOf(obj)
  local snaps = {}
  for _, sl in ipairs(MAT_LAYOUT.slots) do
    snaps[#snaps + 1] = {position = {-sl.x, 0.2, sl.z}, rotation = {0, 0, 0}, rotation_snap = true}
  end
  obj.setSnapPoints(snaps)
  obj.clearButtons()
  if s.built then
    button(obj, "j_noop", "Level " .. s.level .. " " .. s.subclass .. " " .. s.class .. "  (" .. s.ancestry .. ")",
      0, 1.12, 1600, 60, 45, "", {0, 0, 0, 0}, SQUASH)
    local tip = "Click: +1   |   Right-click: -1"
    local x = TRACK_X
    button(obj, "j_hp",     "Health " .. s.hp .. " / " .. s.maxhp, x, TRACK_Z[1], 340, 42, 42, tip, {0.5, 0.12, 0.12, 0.95}, TRACK_SCALE)
    button(obj, "j_shield", "Shield " .. s.shield,                 x, TRACK_Z[2], 340, 42, 42, tip .. "\n(clears when you Rally)", {0.25, 0.3, 0.45, 0.95}, TRACK_SCALE)
    button(obj, "j_ap",     "Actions " .. s.ap,                    x, TRACK_Z[3], 340, 42, 42, tip .. "\n(resets to " .. DEFAULT_AP .. " when you Rally)", {0.5, 0.42, 0.12, 0.95}, TRACK_SCALE)
    local GLOW, GLOW_TEXT = {1, 0.82, 0.25, 1}, {0.15, 0.1, 0.02}       -- your turn to press this one
    local rallyOn, drawOn = phaseWants(color, "Rally"), phaseWants(color, "Encounter")
    button(obj, "j_endTurn", rallyOn and "> Rally <" or "Rally", RALLY_POS[1], RALLY_POS[2], 340, 54, 46,
      "Ready (straighten) your exhausted cards, draw up to " .. HAND_SIZE .. ", reset Actions to " .. DEFAULT_AP .. " and Shield to 0",
      rallyOn and GLOW or {0.18, 0.4, 0.22, 0.95}, TRACK_SCALE, rallyOn and GLOW_TEXT or nil)
    button(obj, "j_matDraw", drawOn and "> Draw Encounter <" or "Draw Encounter", DRAW_POS[1], DRAW_POS[2], 340, 54, drawOn and 32 or 36,
      "Draw the top encounter card face up onto this playmat. If the deck is empty, the discard is shuffled in first.",
      drawOn and GLOW or {0.45, 0.36, 0.12, 0.95}, TRACK_SCALE, drawOn and GLOW_TEXT or nil)
    return
  end
  button(obj, "j_noop", "Open  Character  (bottom-right of your screen)\nto create your hero", 0, 0.45, 520, 60, 30, "", {0, 0, 0, 0}, SQUASH)
end

-- Rally (per mat): ready exhausted cards on the mat, draw up to hand size, reset Actions and Shield.
function endTurn(seat)
  local mat, s = matOf(seat), STATE.seats[seat]
  if not (mat and s and s.built) then return end
  local my, readied = mat.getRotation().y, 0
  for _, o in ipairs(getAllObjects()) do
    if o.type == "Card" and not o.held_by_color then
      local lp = mat.positionToLocal(o.getPosition())
      if math.abs(lp.x) <= 1.05 and math.abs(lp.z) <= 1.05 then
        local r = o.getRotation()
        local d = (r.y - my) % 180
        if d > 30 and d < 150 then                    -- turned sideways = exhausted
          o.setRotationSmooth({r.x, my, r.z})       -- back upright, facing the seat like the hero
          readied = readied + 1
        end
      end
    end
  end
  drawToHandSize(seat, true)
  s.ap, s.shield = DEFAULT_AP, 0
  drawMat(mat)
  broadcastToAll(seat .. " rallies" .. (readied > 0 and (" (readied " .. readied .. " card" .. (readied > 1 and "s" or "") .. ")") or "") .. ".",
    stringColorToRGB(seat))
end
function j_endTurn(obj) local seat = obj.getGMNotes() endTurn(seat) markActed(seat, "Rally") end

local function tweak(obj, field, alt, hiField)
  local _, s = seatOf(obj)
  local hi = hiField and s[hiField] or 99
  s[field] = math.max(0, math.min(hi, s[field] + (alt and -1 or 1)))
  drawMat(obj)
end
function j_hp(obj, c, alt)
  tweak(obj, "hp", alt, "maxhp")
  local seat, s = seatOf(obj)
  if s.hp == 0 then broadcastToAll(seat .. " has been defeated!", {0.9, 0.3, 0.3}) end
end
function j_shield(obj, c, alt) tweak(obj, "shield", alt) end
function j_ap(obj, c, alt)     tweak(obj, "ap", alt) end

-- Cycle slot: a card (or small stack) a player drops here goes to the bottom of that seat's deck.
local CYCLING = {}
-- Merge obj (card or stack) into deck as its bottom card(s), keeping the deck where it is.
local function mergeUnder(seat, deck, obj)
  local dd = deck.getData()
  if dd.Name ~= "Deck" then                          -- deck is down to one card: wrap it
    dd = {Name = "Deck", Transform = dd.Transform, Tags = dd.Tags, Hands = false, SidewaysCard = false,
          DeckIDs = {dd.CardID}, CustomDeck = dd.CustomDeck, ContainedObjects = {dd}}
  end
  dd.CustomDeck = dd.CustomDeck or {}
  local od, add = obj.getData(), {}
  if od.Name == "Deck" then add = od.ContainedObjects or {} else add = {od} end
  for k, v in pairs(od.CustomDeck or {}) do dd.CustomDeck[k] = v end
  for _, c in ipairs(add) do
    for k, v in pairs(c.CustomDeck or {}) do dd.CustomDeck[k] = v end
    table.insert(dd.ContainedObjects, c)            -- last = bottom (takeObject / deal take index 0)
    table.insert(dd.DeckIDs, c.CardID)
  end
  destroyObject(deck); destroyObject(obj)
  spawnObjectData({data = dd})
  broadcastToAll(seat .. " cycled " .. (#add == 1 and (od.Nickname ~= "" and od.Nickname or "a card") or (#add .. " cards")) ..
    " to the bottom of their deck.", stringColorToRGB(seat))
end

-- Lift the deck, slide the card into the deck slot face down, drop the deck back on top, then merge.
function cycleToBottom(seat, obj)
  local mat = matOf(seat)
  if not mat or CYCLING[seat] then return end
  local deck = seatPile(seat, "Deck")
  if deck == obj then return end
  local sl = slot("Deck")
  local spot = imageToWorld(mat, sl.x, 0.3, sl.z)
  local down = {0, mat.getRotation().y, 180}
  if not deck then                                   -- empty deck: the card becomes the deck
    obj.setRotationSmooth(down, false, true)
    obj.setPositionSmooth(spot, false, true)
    return
  end
  CYCLING[seat] = true
  local home = deck.getPosition()
  local hx, hy, hz = home.x or home[1], home.y or home[2], home.z or home[3]
  deck.setLock(true)
  deck.setPositionSmooth({hx, hy + 3.5, hz}, false, true)          -- 1. lift the deck
  Wait.time(function()
    if obj == nil or obj.isDestroyed() or deck == nil or deck.isDestroyed() then CYCLING[seat] = nil return end
    obj.setLock(true)
    obj.setRotationSmooth(down, false, true)                        -- 2. card slides underneath, face down
    obj.setPositionSmooth({hx, hy, hz}, false, true)
    Wait.time(function()
      if obj == nil or obj.isDestroyed() or deck == nil or deck.isDestroyed() then CYCLING[seat] = nil return end
      deck.setPositionSmooth({hx, hy + 0.25, hz}, false, true)     -- 3. deck comes back down on top
      Wait.time(function()
        CYCLING[seat] = nil
        if obj == nil or obj.isDestroyed() or deck == nil or deck.isDestroyed() then return end
        deck.setLock(false); obj.setLock(false)
        mergeUnder(seat, deck, obj)                                 -- 4. one deck again, card at the bottom
      end, 0.5)
    end, 0.55)
  end, 0.35)
end
-- ------------------------------------------------------------------ enemy stacks
-- Six shared stack columns in a row on the Battlefield, all facing the south side, numbered west to east.
-- A stack is a cascade: the rear card at the north end, each card in front of it a little further south,
-- overlapping it so names stay visible. STATE.stacks.S2 = {guid, ...} (rear -> front);
-- STATE.aggro.S2 = "Red" (shown by a token in that player's colour under the stack).
STACK_IDS = {"S1", "S2", "S3", "S4", "S5", "S6"}
local function stackNum(id) return tonumber(id:sub(2)) end
function slotCenter(id)
  return {STACK_X0 + (stackNum(id) - 1) * STACK_DX, 1.02, (STACK_ZMIN + STACK_ZMAX) / 2}
end
-- The nth empty stack (n counts from 0), for summoned enemies.
function emptyStack(n)
  local k = 0
  for _, id in ipairs(STACK_IDS) do
    if not STATE.stacks[id] then
      if k == (n or 0) then return id end
      k = k + 1
    end
  end
end
function cardIdOf(o) return (o.getGMNotes() or ""):match('"id":%s*"([^"]+)"') end
local function stackInfo(o)
  local c = CARDS[cardIdOf(o) or ""]
  return c and c.stack or {role = "Generic", rank = 2, with = "Any"}, c
end
local function stackOf(guid)
  for id, list in pairs(STATE.stacks) do
    for i, g in ipairs(list) do if g == guid then return id, i end end
  end
end
-- Spots under each column (south end): aggro token, then the Aggro button.
local function tokenSpot(id) local c = slotCenter(id) return {c[1] - 0.55, 1.1, STACK_BAR_Z} end
local function buttonSpot(id) local c = slotCenter(id) return {c[1] + 0.45, STACK_BAR_Z} end

function spawnBattlefield()
  local d = tile(BATTLEFIELD_IMAGE, "Battlefield", "Encounter deck, discard, summoned enemies, obstacles and " ..
    "the six enemy stacks. Drop enemies in a stack column; click Aggro under a stack to take its aggro.",
    "", {"J_Battlefield"}, {0, 1.0, 0}, 0, BF_W / 2, BF_D / 2, false)
  d.CustomImage.CustomTile.Thickness = 0.05
  spawnObjectData({data = d, callback_function = function() drawBattlefield() end})
end

-- Aggro tokens follow STATE.aggro: one locked token in the aggro player's colour under each occupied stack.
local function syncAggroTokens()
  local have = {}
  for _, t in ipairs(getObjectsWithTag("J_AggroToken")) do
    local id, color = t.getGMNotes():match("^(S%d):(%a+)$")
    local want = STATE.stacks[id] and STATE.aggro[id]
    if not id or have[id] or want ~= color then destroyObject(t) else have[id] = true end
  end
  for _, id in ipairs(STACK_IDS) do
    local color = STATE.stacks[id] and STATE.aggro[id]
    if color and not have[id] and AGGRO_TOKENS[color] then
      local d = tile(AGGRO_TOKENS[color], "Aggro: " .. color, "This stack is aggro'd to " .. color .. ".",
        id .. ":" .. color, {"J_AggroToken"}, tokenSpot(id), 180, 0.4)
      d.CustomImage.CustomTile.Type = 2
      d.CustomImage.CustomTile.Thickness = 0.12
      spawnObjectData({data = d})
    end
  end
end

-- One Aggro button under each occupied stack; clicking it gives the stack's aggro to whoever clicked.
function drawBattlefield()
  STATE.stacks, STATE.aggro, STATE.hp = STATE.stacks or {}, STATE.aggro or {}, STATE.hp or {}
  local bf = getObjectsWithTag("J_Battlefield")[1]
  if bf then
    bf.clearButtons()
    local sx, sz = BF_W / 2, BF_D / 2
    for _, id in ipairs(STACK_IDS) do
      if STATE.stacks[id] then
        local b = buttonSpot(id)
        local who = STATE.aggro[id]
        bf.createButton({click_function = "j_aggro_" .. id, function_owner = Global, label = "Aggro",
          position = {-b[1] / sx, 0.2, b[2] / sz}, rotation = {0, 180, 0},
          width = 200, height = 50, font_size = 40, scale = {2.62 / sx, 1, 2.62 / sz},     -- playmat-button size
          color = {0.55, 0.18, 0.18, 0.95}, font_color = {1, 1, 1},
          tooltip = "Take this stack's aggro" .. (who and (" (now: " .. who .. ")") or "")})
      end
    end
    -- magnets: encounter deck, discard, and the four obstacle spaces (local = world / board half-size)
    local snaps = {}
    local spots = {ENC_DECK_POS, ENC_DISC_POS}
    for _, o in ipairs(OBSTACLE_SPOTS) do spots[#spots + 1] = o end
    for _, p in ipairs(spots) do
      snaps[#snaps + 1] = {position = {p[1] / sx, 0.2, p[3] / sz}, rotation = {0, 180, 0}, rotation_snap = true}
    end
    bf.setSnapPoints(snaps)
  end
  syncAggroTokens()
end

-- The encounter deck / discard pile: the biggest encounter pile sitting on that spot.
local function encPile(spot)
  local best, bestN
  for _, o in ipairs(getAllObjects()) do
    if (o.type == "Deck" or o.type == "Card") and not o.held_by_color then
      local p = o.getPosition()
      if math.abs((p.x or p[1]) - spot[1]) < 1.2 and math.abs((p.z or p[3]) - spot[3]) < 1.7 and isEncounter(o) then
        local n = o.type == "Deck" and o.getQuantity() or 1
        if not best or n > bestN then best, bestN = o, n end
      end
    end
  end
  return best
end
-- Drawn encounter cards go face up to the top middle of the drawer's playmat (nudged if one is already there).
local DRAW_SPOT = {0, -0.55}                     -- mat image coords
local function drawOne(pile, color)
  local mat = matOf(color)
  if not mat then pile.deal(1, color) return end
  local w = imageToWorld(mat, DRAW_SPOT[1], 0.8, DRAW_SPOT[2])
  local x, y, z = w.x or w[1], w.y or w[2], w.z or w[3]
  for _, o in ipairs(getAllObjects()) do                          -- something already there: offset a little
    if o.type == "Card" and o ~= pile then
      local p = o.getPosition()
      if math.abs((p.x or p[1]) - x) < 0.6 and math.abs((p.z or p[3]) - z) < 0.6 then x = x + 0.5 y = y + 0.2 end
    end
  end
  local rot = {0, mat.getRotation().y, 0}
  if pile.type == "Deck" then
    pile.takeObject({position = {x, y, z}, rotation = rot, smooth = true})
  else
    pile.setRotationSmooth(rot, false, true)
    pile.setPositionSmooth({x, y, z}, false, true)
  end
end
function j_matDraw(mat) local seat = mat.getGMNotes() drawEncounter(seat) markActed(seat, "Encounter") end      -- Draw Encounter on a playmat: draws for that seat
function drawEncounter(color)
  if not SEATS[color] then return end
  local deck = encPile(ENC_DECK_POS)
  if deck then drawOne(deck, color) broadcastToAll(color .. " draws an encounter card.", stringColorToRGB(color)) return end
  local disc = encPile(ENC_DISC_POS)
  if not disc then broadcastToAll("The encounter deck and discard are both empty.", {1, 0.6, 0.2}) return end
  disc.setRotation({0, 180, 180})                                   -- face down
  disc.setPositionSmooth(ENC_DECK_POS, false, true)
  broadcastToAll("The encounter discard is shuffled into a new encounter deck.", {0.9, 0.8, 0.5})
  Wait.time(function()
    if disc == nil or disc.isDestroyed() then return end
    if disc.type == "Deck" then disc.shuffle() end
    drawOne(disc, color)
    broadcastToAll(color .. " draws an encounter card.", stringColorToRGB(color))
  end, 0.8)
end

function setAggro(id, color)
  if not (STATE.stacks[id] and SEATS[color]) or STATE.aggro[id] == color then return end
  STATE.aggro[id] = color
  broadcastToAll("Stack " .. stackNum(id) .. " now has aggro on " .. color .. ".", stringColorToRGB(color))
  drawBattlefield()
end
function j_aggro_S1(o, pc) setAggro("S1", pc) end
function j_aggro_S2(o, pc) setAggro("S2", pc) end
function j_aggro_S3(o, pc) setAggro("S3", pc) end
function j_aggro_S4(o, pc) setAggro("S4", pc) end
function j_aggro_S5(o, pc) setAggro("S5", pc) end
function j_aggro_S6(o, pc) setAggro("S6", pc) end

-- ------------------------------------------------------------------ enemy health / horde bodies
-- Every enemy in a stack gets a counter just under its header, on the right (power and health sit in the header's
-- top-right corner on the new frame; this row still shows in a cascade).
-- Normal enemies count damage taken, starting at 0. Hordes count bodies: a horde enters with its health
-- (x players if starred) in bodies, damage removes bodies, Reinforce adds one.
-- Click +1, right-click -1. STATE.hp[guid] = damage (or bodies for a horde).
local function playerCount()
  local n = 0
  for _, s in pairs(STATE.seats) do if s.built then n = n + 1 end end
  if n == 0 then local ok, seated = pcall(getSeatedPlayers) if ok and seated then n = #seated end end
  return math.max(1, n)
end
local function enemyCard(o) return CARDS[cardIdOf(o) or ""] end
local function isHorde(c)
  local kw = c and (c.keywords or "") or ""
  return c and (c.name:find("Horde", 1, true) or kw:find("Reinforce", 1, true) or kw:find("Horde", 1, true)) and true or false
end
local function startingHP(c)
  local base, star = (c and c.health or ""):match("^%s*(%d*)%s*(%*?)%s*$")
  if not base or base == "" then return 0 end                      -- "*" alone (e.g. Amalgamation): set by hand
  return tonumber(base) * (star == "*" and playerCount() or 1)
end
function drawEnemyHP(o)
  if not o or o.isDestroyed() then return end
  o.clearButtons()
  local v = STATE.hp[o.getGUID()]
  if v == nil then return end
  local c = enemyCard(o)
  local label, tip
  if isHorde(c) then
    local need, bonus = (c.text or ""):match("(%d+) or more bodies, it gets %+(%d+)P")
    label = v .. " bodies" .. ((need and v >= tonumber(need)) and (" +" .. bonus .. "P") or "")
    tip = "Horde bodies. Click: +1 (reinforce)   |   Right-click: -1 (damage)"
  else
    local hp = startingHP(c)
    label = "DMG " .. v
    tip = "Damage taken" .. (hp > 0 and (" (health " .. hp .. ")") or "") .. ". Click: +1   |   Right-click: -1"
  end
  o.createButton({click_function = "j_enemyHP", function_owner = Global, label = label, tooltip = tip,
    position = {0.62, 0.3, -1.0}, rotation = {0, 0, 0}, width = 360, height = 120, font_size = 90,
    color = {0.45, 0.08, 0.08, 0.92}, font_color = {1, 1, 1}})
end
function initEnemyHP(o)
  local g = o.getGUID()
  if (enemyCard(o) or {}).type ~= "Enemy" then return end
  if STATE.hp[g] == nil then
    local c = enemyCard(o)
    STATE.hp[g] = isHorde(c) and startingHP(c) or 0
    if isHorde(c) then broadcastToAll(c.name .. " enters with " .. STATE.hp[g] .. " bodies.", {0.9, 0.8, 0.5}) end
  end
  drawEnemyHP(o)
end
function clearEnemyHP(o)
  STATE.hp[o.getGUID()] = nil
  if not o.isDestroyed() then o.clearButtons() end
end
function j_enemyHP(o, color, alt)
  local g = o.getGUID()
  local before = STATE.hp[g] or 0
  STATE.hp[g] = math.max(0, before + (alt and -1 or 1))
  drawEnemyHP(o)
  local c = enemyCard(o)
  if isHorde(c) then
    if STATE.hp[g] == 0 and before > 0 then broadcastToAll(c.name .. " has no bodies left.", {1, 0.6, 0.2}) end
  else
    local hp = startingHP(c)
    if hp > 0 and STATE.hp[g] >= hp and before < hp then
      broadcastToAll((c and c.name or "Enemy") .. " has taken lethal damage (" .. STATE.hp[g] .. "/" .. hp .. ").", {1, 0.6, 0.2})
    end
  end
end

-- Lay a stack's cards out as a cascade. Drops cards that were moved out of the column some other way.
function layoutStack(id)
  local list, keep = STATE.stacks[id] or {}, {}
  for _, g in ipairs(list) do
    local o = getObjectFromGUID(g)
    if o and not o.isDestroyed() and not o.held_by_color then keep[#keep + 1] = o end
  end
  local c = slotCenter(id)
  local step = #keep > 1 and math.min(STACK_STEP, STACK_SPAN / (#keep - 1)) or 0
  local guids = {}
  for k, o in ipairs(keep) do
    guids[k] = o.getGUID()
    initEnemyHP(o)
    o.setRotationSmooth({0, 180, 0}, false, true)
    o.setPositionSmooth({c[1], 1.15 + k * 0.12, STACK_REAR_Z - (k - 1) * step}, false, true)
  end
  STATE.stacks[id] = #guids > 0 and guids or nil
  if not STATE.stacks[id] then STATE.aggro[id] = nil end
  drawBattlefield()
end

-- Where a new card goes: just in front of the last card of the same or lower rank (existing order is kept,
-- so a hand-arranged stack isn't reshuffled). Rank 0 ("Behind Any") goes to the very back.
local function ruleIndex(list, info)
  if info.rank == 0 then return 1 end
  local idx = 1
  for i, g in ipairs(list) do
    local o = getObjectFromGUID(g)
    local r = o and stackInfo(o).rank or 2
    if r <= info.rank then idx = i + 1 end
  end
  return idx
end
-- Where a card dragged within its own stack goes: by how far out along the column it was dropped.
local function dropIndex(list, obj)
  local p = obj.getPosition()
  local dz = p.z or p[3]
  local idx = 1
  for i, g in ipairs(list) do
    local o = getObjectFromGUID(g)
    if o then local q = o.getPosition() if (q.z or q[3]) > dz then idx = i + 1 end end    -- further north = further back
  end
  return idx
end

local PICKED = {}       -- card guid -> stack it was lifted out of
function onObjectPickUp(color, obj)
  if obj.type ~= "Card" then return end
  local id, i = stackOf(obj.getGUID())
  if not id then return end
  table.remove(STATE.stacks[id], i)
  PICKED[obj.getGUID()] = id
  if #STATE.stacks[id] == 0 then STATE.stacks[id] = nil end
  layoutStack(id)
end

-- Which stack column (if any) a world position is in.
function slotUnder(pos)
  local x, z = pos.x or pos[1], pos.z or pos[3]
  for _, id in ipairs(STACK_IDS) do
    local c = slotCenter(id)
    if math.abs(x - c[1]) <= 1.3 and z >= STACK_ZMIN - 0.2 and z <= STACK_ZMAX + 0.2 then return id end
  end
end

function addToStack(id, obj, color, from)
  local cur, ci = stackOf(obj.getGUID())                 -- already tracked (e.g. pulled back out of a merged deck)
  if cur then table.remove(STATE.stacks[cur], ci) if #STATE.stacks[cur] == 0 then STATE.stacks[cur] = nil end end
  STATE.stacks[id] = STATE.stacks[id] or {}
  local list = STATE.stacks[id]
  if from == id then
    table.insert(list, dropIndex(list, obj), obj.getGUID())       -- rearranging by hand
    layoutStack(id)
    return
  end
  -- Any enemy can join any stack (stack-linking was dropped 2026-11-24); its rank still sets where it sits.
  local info = stackInfo(obj)
  table.insert(list, ruleIndex(list, info), obj.getGUID())
  -- A unit joining a stack pulls its aggro onto the player who put it there (the one who drew it).
  if color and SEATS[color] then STATE.aggro[id] = color end
  layoutStack(id)
end

-- Cards dropped onto a stack card can merge into a deck: split it back into single cards and stack them.
function splitDeck(deck, id, color)
  local n, pos = deck.getQuantity(), deck.getPosition()
  local px, py, pz = pos.x or pos[1], pos.y or pos[2], pos.z or pos[3]
  for i = 1, n - 1 do
    deck.takeObject({position = {px, py + i * 0.4, pz}, smooth = false,
      callback_function = function(c) addToStack(id, c, color, nil) end})
  end
  Wait.frames(function()
    local ok, r = pcall(function() return deck.remainder end)
    if ok and r then addToStack(id, r, color, nil) end
  end, 10)
end
-- Pick up anything in a column that isn't tracked yet (merged decks, leftovers).
local function absorb(id, color)
  for _, o in ipairs(getAllObjects()) do
    if (o.type == "Card" or o.type == "Deck") and not o.held_by_color and isEncounter(o) and slotUnder(o.getPosition()) == id then
      if o.type == "Deck" then splitDeck(o, id, color)
      elseif not stackOf(o.getGUID()) then addToStack(id, o, color, nil) end
    end
  end
end

function onObjectDrop(color, obj)
  if obj.type ~= "Card" and obj.type ~= "Deck" then return end
  local from = PICKED[obj.getGUID()]
  PICKED[obj.getGUID()] = nil
  local dropSlot = slotUnder(obj.getPosition())
  Wait.condition(function()
      if obj == nil or obj.isDestroyed() then                   -- merged into another card/deck
        if dropSlot then Wait.frames(function() absorb(dropSlot, color) end, 5) end
        return
      end
      if obj.held_by_color then return end
      for _, seat in ipairs(SEAT_ORDER) do
        local s, mat = STATE.seats[seat], matOf(seat)
        if s and s.built and mat and onSlot(mat, obj.getPosition(), "Cycle") then cycleToBottom(seat, obj) return end
      end
      if not isEncounter(obj) then return end
      local id = slotUnder(obj.getPosition())
      if not id then
        if from and obj.type == "Card" then clearEnemyHP(obj) end       -- taken out of a stack (defeated, moved...)
        return
      end
      if obj.type == "Deck" then splitDeck(obj, id, color) else addToStack(id, obj, color, from) end
    end,
    function() return obj == nil or obj.isDestroyed() or obj.held_by_color or obj.resting end, 10)
end

local function subclassNames(cls) return keys(CLASSES[cls].subclasses, "name") end

function subclassOf(s)
  for _, v in ipairs(CLASSES[s.class].subclasses) do if v.name == s.subclass then return v end end
end
-- Pick-one group (e.g. Scaleborn Transformations): keep s.pick valid for the current subclass.
function fixPick(s)
  local sub = subclassOf(s)
  if not (sub and sub.choose) then s.pick = nil return end
  for _, id in ipairs(sub.choose) do if id == s.pick then return end end
  s.pick = sub.choose[1]
end
-- Subclass cards that go in the starting deck: everything except the unpicked group cards.
function subclassDeck(s)
  local sub = subclassOf(s)
  local inGroup = {}
  for _, id in ipairs(sub.choose or {}) do inGroup[id] = true end
  local r = {}
  for _, id in ipairs(SETS[sub.set].cards) do
    if not inGroup[id] or id == s.pick then r[#r + 1] = id end
  end
  return r
end

function buildCharacter(seat, color)
  local obj = matOf(seat)
  local s = STATE.seats[seat]
  if s.built then return end
  local cls = CLASSES[s.class]
  fixPick(s)
  local anc
  for _, v in ipairs(ANCESTRIES) do if v.name == s.ancestry then anc = v end end

  -- level 1 starting deck: class core + subclass + ancestry
  local ids = {}
  for _, id in ipairs(expand(SETS[cls.core].cards)) do if id ~= cls.weapon then ids[#ids + 1] = id end end
  for _, id in ipairs(expand(subclassDeck(s))) do ids[#ids + 1] = id end
  ids[#ids + 1] = anc.id

  local tags = {"J_Seat_" .. seat}
  local rot = obj.getRotation().y
  local function at(name) local sl = slot(name) return imageToWorld(obj, sl.x, 0.5, sl.z) end
  spawnCards({cls.hero},   at("Hero"),   rot, false, tags, seat)
  if cls.weapon ~= "" then spawnCards({cls.weapon}, at("Weapon"), rot, false, tags, seat) end
  spawnCards(shuffle(ids), at("Deck"),   rot, true,  tags, seat)

  spawnClassTokens(seat, {[cls.core] = true, [subclassOf(s).set] = true})

  s.maxhp = cls.health; s.hp = cls.health; s.shield = 0; s.ap = DEFAULT_AP
  s.built = true
  drawMat(obj)
  broadcastToAll(seat .. ": Level " .. s.level .. " " .. s.subclass .. " " .. s.class .. " (" .. s.ancestry .. ")" ..
    (s.pick and (" - " .. CARDS[s.pick].name) or ""), stringColorToRGB(seat))
  if s.level > 1 then
    broadcastToColor("Talent trees aren't in the mod yet - this character has " .. (s.level - 1) ..
      " talent point(s) to apply by hand.", color, {1, 0.6, 0.2})
  end
  buildUI()
end

-- Re-sticker every card this seat owns, wherever it is (table, hand, inside any deck).
local function cardSeat(gm) local ok, t = pcall(JSON.decode, gm or "") return ok and type(t) == "table" and t.seat, ok and type(t) == "table" and t.id end
function applyStickers(seat)
  local n = 0
  for _, o in ipairs(getAllObjects()) do
    if o.type == "Card" then
      local st, id = cardSeat(o.getGMNotes())
      if st == seat then o.setDecals(stickerList(seat, id)) n = n + 1 end
    elseif o.type == "Deck" then
      local data, mine = o.getData(), false
      for _, c in ipairs(data.ContainedObjects or {}) do
        local st, id = cardSeat(c.GMNotes)
        if st == seat then
          mine = true
          local dl = stickerList(seat, id)
          c.AttachedDecals = #dl > 0 and decalData(dl) or nil
          n = n + 1
        end
      end
      if mine then                                   -- decks can't take decals on contained cards: respawn it
        local pos, rot = o.getPosition(), o.getRotation()
        destroyObject(o)
        spawnObjectData({data = data, position = pos, rotation = rot})
      end
    end
  end
  return n
end

function removeCharacter(seat)
  for _, o in ipairs(getObjectsWithTag("J_Seat_" .. seat)) do destroyObject(o) end
  STATE.seats[seat].built = false
  local m = matOf(seat) if m then drawMat(m) end
  buildUI()
end

function changeLevel(seat, color, dir)
  local s = STATE.seats[seat]
  local new = math.max(1, math.min(10, s.level + dir))
  if new == s.level then return end
  s.level = new
  if s.built then
    local m = matOf(seat) if m then drawMat(m) end
    broadcastToAll(seat .. " is now level " .. s.level .. ".", stringColorToRGB(seat))
    if dir > 0 then broadcastToColor("+1 talent point (" .. (s.level - 1) .. " total) - apply it by hand until talent trees are in.", color, {1, 0.6, 0.2}) end
  end
  buildUI()
end

-- ------------------------------------------------------------------ on-screen menu (Global XML UI)
-- Two launcher buttons bottom-right open near-full-screen panels, one set per seat colour, each visible only
-- to that player. Only open panels are rendered. buildUI() regenerates everything from STATE + data.
UIOPEN = {}
local UC = {bg = "#1E1B26F7", row = "#2A2635", gold = "#D2B464", text = "#EEE3C8", dim = "#A49CB4",
            btn = "#3A3448", sel = "#6B5A2A", green = "#2E6B37", red = "#7A2323"}
local PW, PH = 1720, 960            -- panel size (TTS UI is laid out on a 1920x1080 canvas)
local SCROLL = 'scrollbarBackgroundColor="#00000040" scrollbarColors="#5A5070|#7A7090|#4A4060|#333333" scrollSensitivity="40"'

local function xe(v) return (tostring(v):gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;")) end
local function ui(c) UIOPEN[c] = UIOPEN[c] or {char = false, enc = false, tab = "adv", adv = 1, set = nil} return UIOPEN[c] end
local function idParts(id) local t = {} for p in tostring(id):gmatch("[^_]+") do t[#t + 1] = p end return t end

local function uText(text, size, color, extra)
  return '<Text fontSize="' .. (size or 18) .. '" color="' .. (color or UC.text) .. '" ' .. (extra or "") .. '>' .. xe(text) .. '</Text>'
end
local function uBtn(id, text, fn, w, h, color, size, extra)
  return '<Button id="' .. id .. '" onClick="' .. fn .. '" preferredWidth="' .. w .. '" minWidth="' .. w .. '" preferredHeight="' .. h ..
         '" minHeight="' .. h .. '" color="' .. (color or UC.btn) .. '" textColor="' .. UC.text .. '" fontSize="' .. (size or 20) .. '" ' ..
         (extra or "") .. '>' .. xe(text) .. '</Button>'
end
local function hRow(h, inner, align)     -- align: TTS childAlignment, default MiddleLeft
  return '<HorizontalLayout preferredHeight="' .. h .. '" minHeight="' .. h .. '" spacing="10" childForceExpandWidth="false" childForceExpandHeight="false" childAlignment="' ..
         (align or "MiddleLeft") .. '">' .. inner .. '</HorizontalLayout>'
end
local function spacer() return '<Text flexibleWidth="1"> </Text>' end
local function vScroll(h, contentH, inner, width)       -- width nil = take the remaining space
  local w = width and ('preferredWidth="' .. width .. '" minWidth="' .. width .. '" flexibleWidth="0"') or 'flexibleWidth="1"'
  return '<VerticalScrollView preferredHeight="' .. h .. '" minHeight="' .. h .. '" ' .. w .. ' color="#00000000" ' .. SCROLL .. '>' ..
         '<VerticalLayout height="' .. math.max(contentH, h - 4) .. '" spacing="10" padding="6 16 6 6" childForceExpandHeight="false">' .. inner ..
         '</VerticalLayout></VerticalScrollView>'
end
local function cardGrid(ids, cw)
  cw = cw or 190
  local x = {'<GridLayout cellSize="' .. cw .. ' ' .. math.floor(cw * 1.4) .. '" spacing="12 12" childAlignment="UpperLeft" preferredHeight="' ..
             (math.floor(cw * 1.4) + 12) * math.ceil(#ids / math.floor(1620 / (cw + 12))) .. '">'}
  for _, id in ipairs(ids) do x[#x + 1] = '<Image image="' .. id .. '" preserveAspect="true" tooltip="' .. xe(CARDS[id].name) .. '"/>' end
  return table.concat(x) .. '</GridLayout>'
end
local function gridHeight(n, cw) cw = cw or 190 return (math.floor(cw * 1.4) + 12) * math.ceil(n / math.floor(1620 / (cw + 12))) end
local function uPanel(id, color, open, inner)
  return '<Panel id="' .. id .. '" visibility="' .. color .. '" active="' .. tostring(open) .. '" rectAlignment="MiddleCenter" width="' .. PW ..
         '" height="' .. PH .. '" color="' .. UC.bg .. '" outline="' .. UC.gold .. '" outlineSize="2 2">' ..
         '<VerticalLayout padding="24 24 18 18" spacing="12" childForceExpandHeight="false" childForceExpandWidth="true">' .. inner .. '</VerticalLayout></Panel>'
end
local function header(c, title, which)
  return hRow(46, uText(title, 30, UC.gold, 'fontStyle="Bold" flexibleWidth="1"') .. uBtn(c .. "_close_" .. which, "Close", "j_ui_close", 110, 42, UC.red))
end
-- Rough line count for sizing a scroll area. Plain find, no patterns: TTS's Lua rejects lazy patterns on long text.
local function lines(text)
  local n, pos = 0, 1
  while true do
    local i = text:find("\n", pos, true)
    local len = (i or (#text + 1)) - pos
    n = n + math.max(1, math.ceil(len / 95))
    if not i then return n end
    pos = i + 1
  end
end

-- ---------------- Character panel: choices across the top, the resulting cards below
local function choiceRow(c, label, kind, names, current, locked)
  local x = uText(label, 20, UC.dim, 'preferredWidth="130" minWidth="130"')
  for i, n in ipairs(names) do
    x = x .. uBtn(c .. "_" .. kind .. "_" .. i, n, locked and "j_noop" or "j_ui_pick", 190, 46, n == current and UC.sel or UC.btn)
  end
  return hRow(50, x)
end

-- ---------------- Forge: socket gems / apply enhancement stickers (permanent once sealed)
local function forgeState(s)
  s.gems = s.gems or {}; s.sockets = s.sockets or {}; s.pending = s.pending or {}
  s.enh = s.enh or {}; s.penh = s.penh or {}
end
local function gemsUsed(s, key)
  local n = 0
  for _, t in ipairs({s.sockets, s.pending}) do
    for _, list in pairs(t) do for _, k in ipairs(list) do if k == key then n = n + 1 end end end
  end
  return n
end
local function gemsFree(s, key) return (s.gems[key] or 0) - gemsUsed(s, key) end
local function onCard(s, id) return #(s.sockets[id] or {}) + #(s.pending[id] or {}) end
local function countPending(s)
  local n = 0
  for _, l in pairs(s.pending) do n = n + #l end
  for _, l in pairs(s.penh) do n = n + #l end
  return n
end
local function contains(list, v) for _, x in ipairs(list or {}) do if x == v then return true end end return false end

-- cards this character can forge: the deck cards only (heroes, weapons and ancestries take no gems)
NO_GEMS = {Hero = true, Weapon = true, Ancestry = true}
local function forgeCards(s, cls, sub, anc)
  local r = {}
  for _, id in ipairs(SETS[cls.core].cards) do if id ~= cls.weapon then r[#r + 1] = id end end
  for _, id in ipairs(subclassDeck(s)) do r[#r + 1] = id end
  return r
end

function forgeBody(c, s, cls, sub, anc)
  forgeState(s)
  local u = ui(c)
  local pool = uText("Gem pool", 20, UC.dim, 'preferredWidth="130" minWidth="130"')
  for i, g in ipairs(GEMS) do
    local col = string.format("#%02X%02X%02X", math.floor(g.rgb[1] * 150), math.floor(g.rgb[2] * 150), math.floor(g.rgb[3] * 150))
    pool = pool .. uBtn(c .. "_gsel_" .. i, g.label .. "   x" .. gemsFree(s, g.key), "j_ui_gsel", 196, 46,
                        u.gem == g.key and UC.sel or col, 18, 'tooltip="Select, then click a card to socket it"')
  end
  local grant = uText("Grant gems", 20, UC.dim, 'preferredWidth="130" minWidth="130"')
  for i, g in ipairs(GEMS) do
    grant = grant .. uBtn(c .. "_grant_" .. i, "+ " .. g.label, "j_ui_grant", 130, 38, UC.btn, 15,
                          'tooltip="Until talents are in: click to add one, right-click to take back an unused one"')
  end
  local np = countPending(s)
  local seal = (np > 0 and uBtn(c .. "_seal", "Seal " .. np .. " pending", "j_ui_seal", 230, 48, UC.green, 20,
                               'tooltip="Lock pending gems and stickers in - permanent"') ..
                           uBtn(c .. "_clear", "Clear pending", "j_ui_clearPending", 170, 48, UC.btn, 18) or "") ..
    uText("Pick a gem, then click a deck card (max " .. GEMS_PER_CARD .. " per card; heroes, weapons and ancestries take none). Right-click a card to remove a pending gem. " ..
          "Sealed gems are permanent" .. (s.built and " and appear on your cards." or " and go on when you create the character."), 15, UC.dim, 'flexibleWidth="1"')
  local body = hRow(50, pool) .. hRow(42, grant) .. hRow(52, seal)

  local ids = forgeCards(s, cls, sub, anc)
  local enhRow, haveEnh = uText("Stickers", 20, UC.dim, 'preferredWidth="130" minWidth="130"'), false
  local inDeck = {} for _, id in ipairs(ids) do inDeck[id] = true end
  for _, e in ipairs(ENHANCEMENTS) do
    if inDeck[e.card] then
      haveEnh = true
      local sealed, pend = contains(s.enh[e.card], e.id), contains(s.penh[e.card], e.id)
      enhRow = enhRow .. uBtn(c .. "_enh_" .. e.id, e.name .. (sealed and "  (sealed)" or (pend and "  (pending)" or "")),
                              sealed and "j_noop" or "j_ui_enh", 260, 44, sealed and UC.green or (pend and UC.sel or UC.btn), 15,
                              'tooltip="' .. xe(CARDS[e.card].name .. ": " .. e.text) .. '"')
    end
  end
  if haveEnh then body = body .. hRow(48, enhRow) end

  local cells = {}
  for _, id in ipairs(ids) do
    local parts = {}
    for _, k in ipairs(s.sockets[id] or {}) do parts[#parts + 1] = GEM_BY_KEY[k].label end
    for _, k in ipairs(s.pending[id] or {}) do parts[#parts + 1] = GEM_BY_KEY[k].label .. "*" end
    local label = #parts > 0 and table.concat(parts, "  ") or "+ socket"
    cells[#cells + 1] = '<VerticalLayout spacing="4" childForceExpandHeight="false">' ..
      '<Image image="' .. id .. '" preserveAspect="true" preferredHeight="238" tooltip="' .. xe(CARDS[id].name) .. '"/>' ..
      uBtn(c .. "_sock_" .. id, label, "j_ui_sock", 170, 52, onCard(s, id) > 0 and UC.sel or UC.btn, 14,
           'tooltip="Click: socket the selected gem  |  Right-click: remove a pending gem"') ..
      '</VerticalLayout>'
  end
  local perRow = math.floor(1620 / 182)
  local gridH = 312 * math.ceil(#ids / perRow)
  body = body .. vScroll(PH - 46 - 56 - 50 - 42 - 52 - (haveEnh and 48 or 0) - 110, gridH,
    '<GridLayout cellSize="170 300" spacing="12 12" childAlignment="UpperLeft" preferredHeight="' .. gridH .. '">' .. table.concat(cells) .. '</GridLayout>')
  return body
end

local function charPanel(c)
  local s, u = STATE.seats[c], ui(c)
  if not u.char then return uPanel(c .. "_char", c, false, "") end
  local cls = CLASSES[s.class]
  fixPick(s)
  local sub = subclassOf(s)
  local anc; for _, v in ipairs(ANCESTRIES) do if v.name == s.ancestry then anc = v end end
  local body = header(c, s.built and ("Your Character - " .. c .. " seat") or ("Create a Character - " .. c .. " seat"), "char") ..
    hRow(50, uBtn(c .. "_ctab_char", "Character", "j_ui_ctab", 220, 46, u.ctab ~= "forge" and UC.sel or UC.btn, 20) ..
             uBtn(c .. "_ctab_forge", "Forge", "j_ui_ctab", 220, 46, u.ctab == "forge" and UC.sel or UC.btn, 20))
  if u.ctab == "forge" then return uPanel(c .. "_char", c, true, body .. forgeBody(c, s, cls, sub, anc)) end
  body = body .. choiceRow(c, "Class", "class", CLASS_ORDER, s.class, s.built)
             .. choiceRow(c, "Subclass", "sub", keys(cls.subclasses, "name"), s.subclass, s.built)
             .. choiceRow(c, "Ancestry", "anc", keys(ANCESTRIES, "name"), s.ancestry, s.built)
  local rows = 4
  if sub.choose then
    local names = {} for _, id in ipairs(sub.choose) do names[#names + 1] = CARDS[id].name end
    body = body .. choiceRow(c, sub.choose_label, "pick", names, CARDS[s.pick].name, s.built)
    rows = 5
  end
  local lvl = uText("Level", 20, UC.dim, 'preferredWidth="130" minWidth="130"') ..
              uBtn(c .. "_lvl_-1", "-", "j_ui_level", 56, 46) .. uText(tostring(s.level), 26, UC.text, 'preferredWidth="60" alignment="MiddleCenter"') ..
              uBtn(c .. "_lvl_1", "+", "j_ui_level", 56, 46) ..
              uText("Talent points: " .. (s.level - 1) .. (s.level > 1 and "  (apply by hand until talent trees are in)" or ""), 16, UC.dim, 'flexibleWidth="1"')
  if s.built then
    lvl = lvl .. uBtn(c .. "_remove", "Remove Character", "j_ui_remove", 260, 54, UC.red, 22)
  else
    lvl = lvl .. uBtn(c .. "_create", "Create Character", "j_ui_create", 320, 58, UC.green, 24)
  end
  body = body .. hRow(62, lvl)
  if s.built then                                -- rolled loot weapons for this class + subclass (tts/build/loot.py)
    local loot = uText("Loot", 20, UC.dim, 'preferredWidth="130" minWidth="130"') .. uText("Roll a weapon:", 18, UC.text, 'preferredWidth="150"')
    for _, t in ipairs({2, 3, 4}) do
      loot = loot .. uBtn(c .. "_loot_" .. t, "Tier " .. ROMAN[t] .. "  (" .. #lootFor(s, t) .. ")", "j_ui_loot", 170, 46, UC.btn, 20)
    end
    body = body .. hRow(62, loot .. uText("Spawns on Weapon 2", 16, UC.dim, 'flexibleWidth="1"'))
    rows = rows + 1
  end

  local core = {}
  for _, id in ipairs(SETS[cls.core].cards) do if id ~= cls.weapon then core[#core + 1] = id end end
  local top = {cls.hero}
  if cls.weapon ~= "" then top[#top + 1] = cls.weapon end
  top[#top + 1] = anc.id
  local sections = {
    {cls.weapon ~= "" and "Hero, Weapon & Ancestry" or "Hero & Ancestry   (no weapon for this class yet)", top},
    {s.class .. " - Core", core},
    {s.subclass .. " - Subclass" .. (sub.choose and ("  (with your " .. sub.choose_label .. ")") or ""), subclassDeck(s)},
  }
  if sub.choose then
    local others = {} for _, id in ipairs(sub.choose) do if id ~= s.pick then others[#others + 1] = id end end
    sections[#sections + 1] = {"Other " .. sub.choose_label .. " options  (not in your deck)", others}
  end
  local inner, h = {}, 0
  for _, sec in ipairs(sections) do
    inner[#inner + 1] = uText(sec[1], 22, UC.gold, 'fontStyle="Bold" preferredHeight="32"') .. cardGrid(sec[2], 170)
    h = h + 42 + gridHeight(#sec[2], 170)
  end
  body = body .. vScroll(PH - 46 - 56 - rows * 62 - 90, h, table.concat(inner))
  return uPanel(c .. "_char", c, true, body)
end

-- ---------------- Encounters panel: list on the left, detail page on the right
local function encSets()
  local r = {}
  for _, code in ipairs(SET_ORDER) do local st = SETS[code] if #st.cards > 0 and CARDS[st.cards[1]].enc then r[#r + 1] = code end end
  return r
end
local function breakdown(ids)
  local n, by = 0, {}
  for _, id in ipairs(ids) do local q = CARDS[id].qty or 1 n = n + q local t = CARDS[id].type by[t] = (by[t] or 0) + q end
  local parts = {}
  local plural = {Enemy = "enemies", Event = "events", Obstacle = "obstacles"}
  for _, t in ipairs({"Enemy", "Event", "Obstacle"}) do
    if by[t] then parts[#parts + 1] = by[t] .. " " .. (by[t] == 1 and t:lower() or plural[t]) end
  end
  return n .. " cards" .. (#parts > 0 and (":  " .. table.concat(parts, ",  ")) or "")
end
local USE_TEXT = {all = "shuffled into the encounter deck", staged = "set aside until a stage shuffles it in", setaside = "kept in the Set Aside bag"}

local function adventureText(a)
  local t = {}
  if a.description ~= "" then t[#t + 1] = a.description .. "\n" end
  t[#t + 1] = "SETUP"
  for _, e in ipairs(a.sets) do
    local line = "-  " .. SETS[e.set].name .. "  (" .. breakdown(SETS[e.set].cards) .. ") - " .. (USE_TEXT[e.use] or e.use)
    if #e.set_aside > 0 then
      local nm = {} for _, id in ipairs(e.set_aside) do nm[#nm + 1] = CARDS[id].name end
      line = line .. "; " .. table.concat(nm, ", ") .. " set aside"
    end
    t[#t + 1] = line
  end
  local j = JOURNEYS[a.id]
  if j then
    t[#t + 1] = "\nJOURNEY"
    for _, id in ipairs(j.order) do t[#t + 1] = id .. "  " .. j.nodes[id].name .. "\n" .. j.nodes[id].rules .. "\n" end
    local seen = {}
    for _, id in ipairs(j.order) do
      for _, act in ipairs(j.nodes[id].actions) do
        local b = act:match("^boss:([^:]+)")
        if b and not seen[b] then
          seen[b] = true
          t[#t + 1] = "BOSS  (" .. id .. ")  " .. BOSSES[b].name .. "\n" .. BOSSES[b].text .. "\n"
        end
      end
    end
  end
  return table.concat(t, "\n")
end

local function encPanel(c)
  local u = ui(c)
  if not u.enc then return uPanel(c .. "_enc", c, false, "") end
  local sets = encSets()
  u.set = u.set or sets[1]
  local body = header(c, "Encounters", "enc") ..
    hRow(54, uBtn(c .. "_tab_adv", "Adventures", "j_ui_tab", 260, 50, u.tab == "adv" and UC.sel or UC.btn, 22) ..
             uBtn(c .. "_tab_sets", "Encounter Sets", "j_ui_tab", 260, 50, u.tab == "sets" and UC.sel or UC.btn, 22) .. spacer() ..
             (STATE.adventure and (uText("Now playing: " .. ADVENTURE_BY_ID[STATE.adventure].name, 20, UC.gold, 'preferredWidth="520" alignment="MiddleRight"') ..
               uBtn(c .. "_reset", "Reset Table", "j_ui_reset", 220, 50, UC.red, 22)) or ""))
  local listH = PH - 46 - 54 - 80
  local list, detail = {}, ""
  if u.tab == "adv" then
    for i, a in ipairs(ADVENTURES) do
      list[#list + 1] = uBtn(c .. "_adv_" .. i, a.name .. "\nLevel " .. a.level .. "  |  " .. a.players .. " players", "j_ui_selAdv", 360, 76,
                             i == u.adv and UC.sel or UC.btn, 19)
    end
    local a = ADVENTURES[u.adv]
    local txt = adventureText(a)
    local img = JOURNEYS[a.id] and ("MAP_" .. a.id) or ("ADV_" .. a.id)
    detail = hRow(48, uText(a.name, 30, UC.gold, 'fontStyle="Bold" flexibleWidth="1"') ..
                      uText("Level " .. a.level .. "   |   " .. a.players .. " players", 22, UC.text, 'preferredWidth="360" alignment="MiddleRight"')) ..
      '<HorizontalLayout preferredHeight="' .. (listH - 140) .. '" spacing="18" childForceExpandWidth="false" childForceExpandHeight="false">' ..
        '<Image image="' .. img .. '" preserveAspect="true" preferredWidth="560" preferredHeight="560"/>' ..
        vScroll(listH - 140, lines(txt) * 25 + 40, uText(txt, 18, UC.text, 'preferredHeight="' .. (lines(txt) * 25 + 20) .. '" alignment="UpperLeft"')) ..
      '</HorizontalLayout>' ..
      hRow(70, spacer() .. (STATE.adventure == a.id
        and uBtn(c .. "_reset2", "Reset Table", "j_ui_reset", 300, 64, UC.red, 26)
        or uBtn(c .. "_start_" .. a.id, "Start Adventure", "j_ui_start", 340, 64, UC.green, 26)))
  else
    for _, code in ipairs(sets) do
      list[#list + 1] = uBtn(c .. "_set_" .. code, SETS[code].name, "j_ui_selSet", 360, 60, code == u.set and UC.sel or UC.btn, 19)
    end
    local st = SETS[u.set]
    local gh = gridHeight(#st.cards, 180)
    detail = hRow(48, uText(st.name, 30, UC.gold, 'fontStyle="Bold" flexibleWidth="1"')) ..
      uText(breakdown(st.cards) .. "   (hover a card for its name; copies show once)", 18, UC.dim, 'preferredHeight="30"') ..
      vScroll(listH - 170, gh, cardGrid(st.cards, 180)) ..
      hRow(70, spacer() .. uBtn(c .. "_spawn_" .. u.set, "Spawn at my seat", "j_ui_spawn", 300, 64, UC.btn, 24) ..
                          uBtn(c .. "_shufin_" .. u.set, "Shuffle into Encounter Deck", "j_ui_shufin", 400, 64, UC.green, 24))
  end
  body = body .. '<HorizontalLayout preferredHeight="' .. listH .. '" spacing="20" childForceExpandWidth="false" childForceExpandHeight="false">' ..
    vScroll(listH, #list * 86, table.concat(list), 390) ..
    '<VerticalLayout flexibleWidth="1" spacing="10" childForceExpandHeight="false">' .. detail .. '</VerticalLayout>' ..
    '</HorizontalLayout>'
  return uPanel(c .. "_enc", c, true, body)
end

ASSETS_SET = false
function buildUI()
  if not ASSETS_SET then UI.setCustomAssets(UI_ASSETS) ASSETS_SET = true end
  local x = {
    '<Defaults><Text alignment="MiddleLeft" color="' .. UC.text .. '"/></Defaults>',
    '<Panel id="j_launcher" rectAlignment="LowerRight" offsetXY="-16 16" width="190" height="100">',
    '<VerticalLayout spacing="8">',
    uBtn("j_launch_char", "Character", "j_ui_toggleChar", 190, 46, "#3A3448F0", 22),
    uBtn("j_launch_enc", "Encounters", "j_ui_toggleEnc", 190, 46, "#3A3448F0", 22),
    '</VerticalLayout></Panel>',
  }
  if STATE.turn then          -- turn bar: bottom-right above the launcher, clear of the hand; everyone sees the same thing
    x[#x + 1] = '<Panel id="j_turnbar" rectAlignment="LowerRight" offsetXY="-16 128" width="300" height="108">' ..
      '<VerticalLayout spacing="8" childAlignment="LowerRight">' ..
      uBtn("j_phaseBtn", phaseLabel(), "j_ui_nextPhase", 300, 50, "#2E4A30F0", 20) ..
      uBtn("j_dieBtn", dieLabel(), "j_ui_rollDie", 300, 50, "#5A2020F0", 20) ..
      '</VerticalLayout></Panel>'
  end
  for _, c in ipairs(SEAT_ORDER) do
    if STATE.seats[c] then x[#x + 1] = charPanel(c) end
    x[#x + 1] = encPanel(c)
  end
  UI.setXml(table.concat(x))
end

local function needSeat(player)
  if SEATS[player.color] then return true end
  broadcastToColor("Take a seat (White, Red, Green or Blue) to use this menu.", player.color, {1, 0.6, 0.2})
  return false
end

function j_ui_toggleChar(player)
  if not needSeat(player) then return end
  local u = ui(player.color) u.char = not u.char u.enc = false buildUI()
end
function j_ui_toggleEnc(player)
  if not needSeat(player) then return end
  local u = ui(player.color) u.enc = not u.enc u.char = false buildUI()
end
function j_ui_close(player, _, id) local p = idParts(id) ui(p[1])[p[3]] = false buildUI() end

function j_ui_pick(player, _, id)
  local p = idParts(id)
  local c, kind, i = p[1], p[2], tonumber(p[3])
  local s = STATE.seats[c]
  if s.built then return end
  if kind == "class" then s.class = CLASS_ORDER[i] s.subclass = CLASSES[s.class].subclasses[1].name
  elseif kind == "sub" then s.subclass = CLASSES[s.class].subclasses[i].name
  elseif kind == "anc" then s.ancestry = ANCESTRIES[i].name
  elseif kind == "pick" then s.pick = subclassOf(s).choose[i] end
  fixPick(s)
  buildUI()
end
function j_ui_ctab(player, _, id) local p = idParts(id) ui(p[1]).ctab = p[3] buildUI() end
function j_ui_gsel(player, _, id)
  local p = idParts(id) local u = ui(p[1])
  local key = GEMS[tonumber(p[3])].key
  u.gem = (u.gem ~= key) and key or nil
  buildUI()
end
function j_ui_grant(player, mouse, id)
  local p = idParts(id) local s = STATE.seats[p[1]] forgeState(s)
  local key = GEMS[tonumber(p[3])].key
  if mouse == "-2" then
    if gemsFree(s, key) > 0 then s.gems[key] = s.gems[key] - 1
    else broadcastToColor("No unused " .. GEM_BY_KEY[key].label .. " gem to take back.", player.color, {1, 0.6, 0.2}) end
  else s.gems[key] = (s.gems[key] or 0) + 1 end
  buildUI()
end
function j_ui_sock(player, mouse, id)
  local p = idParts(id) local c, card = p[1], p[3]
  local s, u = STATE.seats[c], ui(c) forgeState(s)
  if mouse == "-2" then
    local l = s.pending[card]
    if l and #l > 0 then table.remove(l) else broadcastToColor("No pending gem on that card (sealed gems are permanent).", player.color, {1, 0.6, 0.2}) end
  else
    if NO_GEMS[CARDS[card].type] then broadcastToColor(CARDS[card].type .. " cards can't take gems.", player.color, {1, 0.6, 0.2}) return end
    if not u.gem then broadcastToColor("Pick a gem from the gem pool first.", player.color, {1, 0.6, 0.2}) return end
    if gemsFree(s, u.gem) <= 0 then broadcastToColor("No " .. GEM_BY_KEY[u.gem].label .. " gems left - grant one first.", player.color, {1, 0.6, 0.2}) return end
    if onCard(s, card) >= GEMS_PER_CARD then broadcastToColor(CARDS[card].name .. " already has " .. GEMS_PER_CARD .. " gems.", player.color, {1, 0.6, 0.2}) return end
    s.pending[card] = s.pending[card] or {}
    table.insert(s.pending[card], u.gem)
  end
  buildUI()
end
function j_ui_enh(player, _, id)
  local p = idParts(id) local s = STATE.seats[p[1]] forgeState(s)
  local e = ENH_BY_ID[p[3]]
  local l = s.penh[e.card] or {}
  s.penh[e.card] = l
  for i, x in ipairs(l) do if x == e.id then table.remove(l, i) buildUI() return end end
  l[#l + 1] = e.id
  buildUI()
end
function j_ui_clearPending(player, _, id)
  local s = STATE.seats[idParts(id)[1]] forgeState(s)
  s.pending = {} s.penh = {}
  buildUI()
end
function j_ui_seal(player, _, id)
  local c = idParts(id)[1]
  local s = STATE.seats[c] forgeState(s)
  local n = countPending(s)
  for card, l in pairs(s.pending) do
    s.sockets[card] = s.sockets[card] or {}
    for _, k in ipairs(l) do table.insert(s.sockets[card], k) end
  end
  for card, l in pairs(s.penh) do
    s.enh[card] = s.enh[card] or {}
    for _, e in ipairs(l) do table.insert(s.enh[card], e) end
  end
  s.pending = {} s.penh = {}
  if s.built then applyStickers(c) end
  broadcastToAll(c .. " sealed " .. n .. " upgrade(s) in the Forge.", stringColorToRGB(c))
  buildUI()
end
function j_ui_create(player, _, id) buildCharacter(idParts(id)[1], player.color) end
function j_ui_remove(player, _, id) removeCharacter(idParts(id)[1]) end
-- ---------------- Loot: a random rolled weapon for the seat's class + subclass and the chosen tier
ROMAN = {"I", "II", "III", "IV"}
function lootFor(s, tier)
  local r = {}
  for _, w in ipairs(LOOT or {}) do
    if w.class == s.class and w.subclass == s.subclass and w.tier == tier then r[#r + 1] = w.id end
  end
  return r
end
function rollWeapon(seat, tier)
  local s, obj = STATE.seats[seat], matOf(seat)
  if not (s and s.built and obj) then return end
  local pool = lootFor(s, tier)
  if #pool == 0 then broadcastToColor("No tier " .. ROMAN[tier] .. " " .. s.subclass .. " weapons rolled yet.", seat, {1, 0.6, 0.2}) return end
  local id = pool[math.random(#pool)]
  local sl = slot("Weapon 2")
  spawnCards({id}, imageToWorld(obj, sl.x, 1.5, sl.z), obj.getRotation().y, false, {"J_Seat_" .. seat}, seat)
  broadcastToAll(seat .. " found " .. CARDS[id].name .. " (Tier " .. ROMAN[tier] .. ")", stringColorToRGB(seat))
end
function j_ui_loot(player, _, id) local p = idParts(id) rollWeapon(p[1], tonumber(p[3])) end

function j_ui_level(player, _, id) local p = idParts(id) changeLevel(p[1], player.color, tonumber(p[3])) end

function j_ui_tab(player, _, id) local p = idParts(id) ui(p[1]).tab = p[3] buildUI() end
function j_ui_selAdv(player, _, id) local p = idParts(id) ui(p[1]).adv = tonumber(p[3]) buildUI() end
function j_ui_selSet(player, _, id) local p = idParts(id) ui(p[1]).set = p[3] buildUI() end
function j_ui_start(player, _, id)
  local p = idParts(id)
  ui(p[1]).enc = false                     -- close the menu so the table is visible
  startAdventure(p[3], player.color)
end
function j_ui_reset(player) resetTable(player.color) end

function j_ui_spawn(player, _, id)
  local p = idParts(id)
  local set = SETS[p[3]]
  local m = matOf(p[1])
  local pos = m and imageToWorld(m, 0.62, 0.8, -0.45) or {2, 1.5, -3.6}
  local rot = m and m.getRotation().y or 180
  spawnObjectData({data = deckData(shuffle(expand(set.cards)), {}, set.name, "", true), position = pos, rotation = {0, rot, 180}})
  broadcastToAll(p[1] .. " spawned " .. set.name .. ".", {0.95, 0.85, 0.55})
end
function j_ui_shufin(player, _, id)
  local p = idParts(id)
  if not STATE.adventure then broadcastToColor("Start an adventure first - there's no encounter deck yet.", player.color, {1, 0.6, 0.2}) return end
  local set = SETS[p[3]]
  local objs = zoneCards("J_EncZone")          -- read the current deck before the new cards arrive
  objs[#objs + 1] = spawnObjectData({data = deckData(expand(set.cards), {}, "", "", true),
    position = {ENC_DECK_POS[1], ENC_DECK_POS[2] + 6, ENC_DECK_POS[3]}, rotation = {0, 180, 180}})
  rebuildEncounterDeck(objs)
  broadcastToAll(set.name .. " shuffled into the encounter deck.", {0.95, 0.85, 0.55})
end
