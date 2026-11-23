# Journeys – TTS playtest mod

## Load it
1. Copy `Journeys.json` to `Documents\My Games\Tabletop Simulator\Saves\`
2. In TTS: Create → Singleplayer/Multiplayer → Games → Save & Load → **Journeys - Playtest**
3. Images load straight from this folder (`file:///C:/Users/nolan/Desktop/Journeys TTS/...`), so don't move it.
   For online playtesters the images need to be uploaded (TTS Modding → Cloud Manager) and the build re-run with the cloud links.

## Using it
Two buttons sit in the **bottom-right corner of the screen**; each opens a near-full-screen panel only you can see.
- **Character** - click a Class, Subclass and Ancestry along the top; the cards below show exactly what you'll get
  (hero, weapon, ancestry, core, subclass), so it doubles as a card browser. Set the level, then **Create Character**.
  Once built: level -/+ and **Remove Character**.
- **Forge** (tab in the Character panel) - socket gems into any card (hero, weapon, ancestry, deck cards), max 2 per card,
  +1/+2 of the same colour stack. Pick a gem from the pool, click a card; right-click removes a *pending* gem.
  **Seal** makes them permanent and puts the gem stickers on the real cards (wherever they are - deck, hand, table).
  Until talents exist, use **Grant gems** to add gems to the pool. Enhancement stickers come from the Enhancements tab
  (`card_id`, `name`, `sticker_text`) and appear as toggle buttons in the Forge for cards in your deck.
- **Encounters** -
  - *Adventures*: pick one on the left to see its journey map, setup, every stage's rules and the boss.
    **Start Adventure** sets it all up (and closes the menu). While one is running, **Reset Table** is at the top.
  - *Encounter Sets*: pick a set to see its cards and a breakdown. **Spawn at my seat** / **Shuffle into Encounter Deck**.
  - Text in the Adventures tab `description` column (first row of the adventure) appears at the top of its page.
- **Journey board** (left side of the table): only the stages you can go to next are highlighted green - click one to journey there.
  Entering a stage runs its setup automatically (summon set-aside enemies, shuffle new sets + the discard pile into the
  encounter deck, summon the boss). Hover a stage for its rules. The boss tile has Health / Armor / Power trackers.

## During play
- **Playmat** slots: Hero, Weapon, Weapon 2, Cycle, Deck, Discard (cards snap into them).
  - **Cycle**: drop a card (or a small stack) here and it goes to the bottom of your deck.
- **Playmat trackers** (top-right of the mat, after Create Character): Health, Shield, Actions - click -1, right-click +1.
- **End Turn** (under the trackers): readies (straightens) any sideways cards on your mat, draws you up to 4,
  resets Actions to 2 and Shield to 0.
- **Turn bar** (bottom-right of the screen above the menu buttons, while an adventure runs): shows the round and
  phase for everyone. Click to move on, right-click to go back. It's only a tracker - it never moves cards.
  The boss die button under it rolls A A A B B C.
- **Token supply** (column along the right edge): bottomless bags of Burn, Frost, Stun, +1 Power, Armor, Strength,
  Intellect, Agility (stack them to count) and a blue number Counter (TTS's own counter, for Horde bodies etc.).
- **Class tokens** spawn on the top-left of the playmat when you create a character that uses them:
  Ember bag (Dragonheart), Renown bag (Rogue - Outlaw), one Stealth token (Rogue). Edit the TOKENS list in
  tts/build/build.py to add more (the owner column is a class or subclass set code).
- All +/- buttons: click +1, right-click -1.
- **End Turn** draws your deck dry, then shuffles your discard pile in as the new deck and keeps drawing.

## Changing content
Everything comes from `data/journeys-cards.xlsx` (Cards, Sets, Classes, Adventures, Journey, Bosses tabs) + the images in `cards/`.
After adding cards or adventures, ask Claude to rebuild (`tts/build/catalog.py` → `tts/build/build.py`).
Don't edit `tts/src/data.lua` by hand – it's regenerated.

### Journey actions (Journey tab, `actions` column, separated by `;`)
- `summon:<card id>:<n>` – move n set-aside copies to the Summoned area (`1*` = 1 per player)
- `shuffle:<SET>,<SET>` – shuffle those staged sets + the encounter discard into the encounter deck
- `boss:<boss id>[:armor=<n>]` – put the boss on the journey board (health `4*` = 4 per player)

## Battlefield (centre of the table) and enemy stacks
- **One board** in the middle of the table, read from the south side:
  - Encounter Deck over Discard at the west end.
  - Six enemy stacks in a row in the middle.
  - A 2x2 block of Obstacle spaces at the east end.
- **Cascade:** drop an enemy in a stack column and it joins that stack. The rear card sits at the top (north) and each card in front overlaps it a little further down, so every name stays visible.
- **Order** comes from the enemy's type line:
  - Backline goes behind, Generic and other roles in the middle, Vanguard in front.
  - "(Behind ...)" goes to the very back and "(Front ...)" to the very front.
  - The rest of the brackets say what the enemy stacks with. You get a warning if it joins a stack without that type.
- **Aggro:** a token in the player's colour under each stack shows who it's aggro'd to.
  - Click **Aggro** next to the token to take that stack's aggro.
  - Dropping an enemy onto a stack gives its aggro to you (you drew it).
  - The token disappears when the stack is empty.
- **Summoned enemies** (journey actions) each start their own stack in the next empty column, with no aggro yet.
- **By hand:** drag a card within its stack to reorder it, or drag it out of the column to remove it. The cascade closes up.
- **Enemy damage:** every enemy in a stack gets a red DMG counter in its top-right corner (it stays visible in the cascade).
  - It starts at 0. Click +1, right-click -1.
  - A message appears when damage reaches the enemy's health (starred health is multiplied by the number of players).
  - Taking the card out of the stacks clears its counter.
- **Hordes** (Horde in the name, or the Reinforce keyword) count bodies instead.
  - They enter with health x players in bodies (Goblin Horde: 2 per player).
  - Click +1 to reinforce, right-click -1 for damage.
  - The counter shows +1P once the card's body threshold is reached.
- **Draw Encounter** (under the Discard): puts the top encounter card face up at the top middle of your playmat. If the deck is empty, the discard is shuffled face down into a new deck first.
