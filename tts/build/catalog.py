"""Journeys card catalog -> data/journeys-cards.xlsx  (source of truth for the TTS build).
Rows: id, name, set, kind, class, subclass, card_type, traits, keywords, text, power, health, channel, qty, source_file, notes
Gem notation: {r} {b} {g}.  qty is read from the filename (" xN"), default 1."""
import re, sys, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo

def qty(f):
    m = re.search(r" x(\d+)\.png$", f); return int(m.group(1)) if m else 1

P = "player"; E = "encounter"
# (id, name, set, card_type, traits, keywords, text, power, health, channel, source, notes)
CARDS = [
# --- character (hero) cards
("CHR-DRG","Dragonheart","CHR","Hero","Dragonheart","","Tap, Recycle a card - Gain an Ember.","","","","character cards/Dragonheart x1.png","No class deck yet"),
("CHR-MAG","Mage","CHR","Hero","Mage","","Tap - Look at the top card of your deck. You may recycle it.","","","","character cards/Mage x1.png",""),
("CHR-PRI","Priest","CHR","Hero","Priest","","Action, Tap - Imbue your next card played this turn.","","","","character cards/Priest x1.png","No class deck yet"),
("CHR-ROG","Rogue","CHR","Hero","Rogue","","Action, Recycle a card - Enter stealth. (While stealthed, you may target or channel any enemy or obstacle in a stack. After you perform an action, you leave stealth.)","","","","character cards/Rogue x1.png","No class deck yet"),
("CHR-WAR","Warrior","CHR","Hero","Warrior","","Tap - Gain 1 Shield. Activate only if you've defeated an enemy this turn.","","","","character cards/Warrior x1.png","Placeholder art"),
# --- ancestry
("ANC-001","Elven Ancestry","ANC","Ancestry","Ancestry","Quickcast","Your next card played this turn gets +1{g}.","","","","ancestry/Elven Ancestry.png",""),
("ANC-002","Human Ancestry","ANC","Ancestry","Ancestry","Quickcast","Your next card played this turn gets +1{b}.","","","","ancestry/Human Ancestry.png",""),
("ANC-003","Orc Ancestry","ANC","Ancestry","Ancestry","Quickcast","Your next card played this turn gets +1{r}.","","","","ancestry/Orc Ancestry.png",""),
# --- mage
("MAG-W01","Gnarled Staff","MAG","Weapon","Mage Weapon","","Weapon I. Activate: recycle a card - 1{r}.","","","","classes/mage/Gnarled Staff x1.png","Weapon icon read as recycle -> 1{r}; confirm"),
("MAG-001","Arcane Barrier","MAG","Skill","Mage Defense Skill","","Gain 2{g} Shield.","","","","classes/mage/Arcane Barrier x1.png",""),
("MAG-002","Counterspell","MAG","Skill","Mage Defense Skill","Quickcast","Play anytime after you draw a non-elite encounter card. Shuffle that card back into the encounter deck, then banish {name}.","","","","classes/mage/Counterspell x1.png","Replaced Comeback (2026-11-26)"),
("MAG-003","Knowledge","MAG","Skill","Mage Defense Skill","Quickcast","Recycle any number of cards. Then Draw 1{b} card.","","","","classes/mage/Knowledge x1.png",""),
("MAG-004","Magic Missile","MAG","Skill","Mage Attack Skill","Focus","Deal 1{b} to any number of enemies.","","","","classes/mage/Magic Missile x1.png",""),
("MAG-FIR-001","Cinder","MAG-FIR","Skill","Fire Attack Skill","","Cinder has Quickcast if it targets an enemy with burn. Deal 2{r} to an enemy.","","","","classes/mage/fire/Cinder x1.png",""),
("MAG-FIR-002","Fire Tornado","MAG-FIR","Skill","Fire Attack Skill","","Distribute 2{b} burn among enemies.","","","","classes/mage/fire/Fire Tornado x1.png",""),
("MAG-FIR-003","Fireball","MAG-FIR","Skill","Fire Attack Skill","Aggro","Deal 3{r} to an enemy.","","","","classes/mage/fire/Fireball x1.png",""),
("MAG-FIR-004","Ritual","MAG-FIR","Skill","Fire Defense Skill","","Create your choice of a Strength, Intellect, or Agility token.","","","","classes/mage/fire/Ritual x1.png",""),
("MAG-FIR-005","Smolder","MAG-FIR","Skill","Fire Attack Skill","","For each enemy with burn, deal damage to them equal to their burn plus 0{r}.","","","","classes/mage/fire/Smolder x1.png","Base 0{r}: only scales with Red gems - intended?"),
("MAG-ICE-001","Chilling Air","MAG-ICE","Skill","Ice Attack Skill","","Deal 1{b} to up to 2{g} enemies. Apply Frost to all enemies dealt damage this way.","","","","classes/mage/ice/Chilling Air x1.png",""),
("MAG-ICE-002","Damage","MAG-ICE","Skill","Ice Attack Skill","","Deal 2{b} to an enemy. Increase this by 1{r} if the enemy has Frost.","","","","classes/mage/ice/Damage x1.png","Name looks like a placeholder"),
("MAG-ICE-003","Freeze","MAG-ICE","Skill","Ice Attack Skill","","Stun a non-elite enemy.","","","","classes/mage/ice/Freeze x1.png","Typed Attack but deals no damage"),
("MAG-ICE-004","Frostbite","MAG-ICE","Skill","Ice Attack Skill","","Deal 1{b} to each enemy with Frostbite.","","","","classes/mage/ice/Frostbite x1.png","Says 'with Frostbite' - other Ice cards apply 'Frost'"),
("MAG-ICE-005","Shatter","MAG-ICE","Skill","Ice Attack Skill","","Deal 2{r} to an enemy, then apply Frost to them. If this defeats an enemy, apply Frost to 1{b} enemy.","","","","classes/mage/ice/Shatter x1.png",""),
# --- warrior
("WAR-W01","Rusty Sword","WAR","Weapon","Warrior Weapon","","Weapon I. Activate: recycle a card - 1{r}.","","","","classes/warrior/Rusty Sword x1.png","Weapon icon read as recycle -> 1{r}; confirm"),
("WAR-001","Bring Down","WAR","Skill","Warrior Attack Skill","Focus, Aggro","Deal 4{r} to an enemy.","","","","classes/warrior/Bring Down x1.png",""),
("WAR-002","Cleave","WAR","Skill","Warrior Attack Skill","","Deal 1{r} to up to 2{g} enemies.","","","","classes/warrior/Cleave x1.png",""),
("WAR-003","Follow Up","WAR","Skill","Warrior Attack Skill","","Follow Up has Quickcast if you've defeated an enemy this turn. Deal 2{g} to an enemy.","","","","classes/warrior/Follow Up x1.png",""),
("WAR-004","Victory Rush","WAR","Skill","Warrior Attack Skill","","Deal 2{r} to an enemy. If this defeats an enemy, heal 1{b}.","","","","classes/warrior/Victory Rush x1.png","Core has no Defense skill (Mage core has 3)"),
("WAR-BLD-001","Duelist Stance","WAR-BLD","Aura","Blade Dancer Aura - Stance","Stance","Whenever you defeat an enemy with a weapon, put a counter on Duelist Stance. Spend 3 Counters: Untap 1{g} weapon you control. Spend 2 Counters: Your next weapon attack gains +1{r} power.","","","","classes/warrior/Blade Dancer/Duelist Stance x1.png",""),
("WAR-BLD-002","Parry","WAR-BLD","Skill","Blade Dancer Defense Skill","","Disarm 1{b} enemies. If {b} is 3 or more, banish Parry.","","","","classes/warrior/Blade Dancer/Parry x1.png",""),
("WAR-BLD-003","Push the Point","WAR-BLD","Skill","Blade Dancer Defense Skill","Quickcast","Until end of turn, weapons you control get +1{g} Power.","","","","classes/warrior/Blade Dancer/Push the Point x1.png","Placeholder art"),
("WAR-BLD-004","Sharpen Steel","WAR-BLD","Aura","Blade Dancer Aura","Lasting 2{g}","Attach this to a weapon you control. Attached weapon gets +1{r} Power.","","","","classes/warrior/Blade Dancer/Sharpen Steel x1.png",""),
("WAR-BLD-005","Swords Up","WAR-BLD","Skill","Blade Dancer Defense Skill","Quickcast","Untap your weapons.","","","","classes/warrior/Blade Dancer/Swords Up x1.png","Placeholder art"),
("WAR-IRC-001","Armor Aura","WAR-IRC","Aura","Ironclad Aura","Lasting 2{b}","When Armor Aura enters and at the start of each round, gain 1{g} shield.","","","","classes/warrior/Ironclad/Armor Aura x1.png","Placeholder art"),
("WAR-IRC-002","Guardian Stance","WAR-IRC","Aura","Ironclad Aura - Stance","Stance","Tap - Gain 1{b} Shield. Activate only if you are engaged by 3{b} or more enemies.","","","","classes/warrior/Ironclad/Guardian Stance x1.png","Placeholder art"),
("WAR-IRC-003","Head Butt","WAR-IRC","Skill","Ironclad Attack Skill","Quickcast, Aggro","Deal 1{r} to an enemy.","","","","classes/warrior/Ironclad/Head Butt x1.png","Placeholder art"),
("WAR-IRC-004","Shields Up","WAR-IRC","Skill","Ironclad Defense Skill","","Gain 2{g} Shield.","","","","classes/warrior/Ironclad/Shields Up x1.png","Placeholder art; same text as Mage's Arcane Barrier"),
("WAR-IRC-005","Stand Behind Me","WAR-IRC","Skill","Ironclad Attack Skill","Aggro","Deal 2{r} to an enemy. When this channels an Obstacle, gain 1{g} shield.","","","","classes/warrior/Ironclad/Stand Behind Me x1.png","Placeholder art; 'Aggro' not bolded like other keywords"),
# --- priest
("PRI-001","Chain Heal","PRI","Skill","Priest Defense Skill","","Heal 2{g} allies 1{b}. Imbued - Return Chain Heal to your hand.","","","","classes/priest/Chain Heal x1.png",""),
("PRI-002","Miracle","PRI","Skill","Priest Defense Skill","Quickcast","Your next card played this turn is imbued.","","","","classes/priest/Miracle x1.png",""),
("PRI-003","Regular Heal","PRI","Skill","Priest Defense Skill","","Heal an ally 2{r}. Imbued - Heal them an additional 2{b}.","","","","classes/priest/Regular Heal x1.png","Name looks like a placeholder"),
("PRI-004","Smite","PRI","Skill","Priest Attack Skill","Aggro","Deal 2{b} to an enemy. Imbued - Deal an additional 2{r}.","","","","classes/priest/Smite x1.png",""),
("PRI-ANO-001","Boon","PRI-ANO","Skill","Anointed Defense Skill","","Choose a player to create their choice of a Strength, Agility, or Intelligence token under that player's control. Imbued - That player creates an Omni token instead.","","","","classes/priest/Anointed/Boon x1.png","Says 'Intelligence' token; Mage's Ritual and the token supply say 'Intellect'"),
("PRI-ANO-002","Divine Blessing","PRI-ANO","Skill","Anointed Defense Skill","","Choose a player. That player chooses one: Draw 2{b} cards. Heal 2{r}. Gain 2{g} Shield. Imbued - That player chooses 2 instead.","","","","classes/priest/Anointed/Divine Blessing x1.png",""),
("PRI-ANO-003","Mind Soothe","PRI-ANO","Skill","Anointed Attack Skill","","Disarm up to 1{g} non-elite enemy for the turn. (Disarmed enemies don't attack) Imbued - Stun those enemies instead.","","","","classes/priest/Anointed/Mind Soothe x1.png",""),
("PRI-ANO-004","Premonition","PRI-ANO","Skill","Anointed Defense Skill","","Look at the top 2{g} cards of the Encounter deck. Leave one on top and recycle the rest. Imbued - Look at an additional 2{b} cards.","","","","classes/priest/Anointed/Premonition x1.png",""),
("PRI-ANO-005","Sanctuary","PRI-ANO","Skill","Anointed Defense Skill","","Choose a player to get 2{g} shield. Imbued - All players gain 1{r} shield instead.","","","","classes/priest/Anointed/Sanctuary x1.png","'Imbued' not bolded like the other cards"),
("PRI-SER-001","Ally Counters","PRI-SER","Skill","Seraph Defense Skill","","Put 1{g} lasting counter on an ally. Imbued - Put 1{b} lasting counters on all your allies instead.","","","","classes/priest/Seraph/Ally Counters x1.png","Name looks like a placeholder"),
("PRI-SER-002","Angel","PRI-SER","Ally","Card Type","Lasting 2{b}","Tap - Heal an ally 1{g}. Increase this by 1{r} if they are at or below half life. Imbued - Angel always heals the additional {r}.","","","","classes/priest/Seraph/Angel x1.png","Type line still says 'Card Type' (probably Seraph Ally)"),
("PRI-SER-003","Cherub","PRI-SER","Ally","Seraph Ally","Lasting 2{b}","Cherub enters under any player. Whenever you are healed, heal an additional 1{g}. Imbued - Whenever you are healed, heal another player 1{r}.","","","","classes/priest/Seraph/Cherub x1.png",""),
("PRI-SER-004","Healing Buddy","PRI-SER","Ally","Seraph Ally","Lasting 2{b}","Tap - Heal an ally 1{g}. Imbued - When Healing Buddy's would be discarded, return it to your hand.","","","","classes/priest/Seraph/Healing Buddy x1.png","Name looks like a placeholder; text 'Healing Buddy's would be discarded' has a stray possessive"),
("PRI-SER-005","Tag Team","PRI-SER","Skill","Seraph Attack Skill","","Deal 1{r} to an enemy. Increase this by 1{b} for each Ally you control.","","","","classes/priest/Seraph/Tag Team x1.png",""),
# --- dragonheart
("DRG-001","Burn Bright","DRG","Skill","Dragonheart Defense Skill","","Gain 2{r} Embers.","","","","classes/dragonheart/Burn Bright x1.png",""),
("DRG-002","Cinders","DRG","Skill","Dragonheart Attack Skill","","Deal 2{r} to an enemy. If this defeats an enemy, gain 1{b} Embers.","","","","classes/dragonheart/Cinders x1.png","Placeholder art"),
("DRG-003","Scorch","DRG","Skill","Dragonheart Attack Skill","","Deal 1{b} to up to 2{g} enemies.","","","","classes/dragonheart/Scorch x1.png",""),
("DRG-004","Tend the Brood","DRG","Skill","Dragonheart Defense Skill","","Heal 2{g}. Gain 1{r} Ember.","","","","classes/dragonheart/Tend the Brood x1.png","Placeholder art"),
("DRG-BRD-001","Card Name","DRG-BRD","Skill","Broodmother Attack Skill","Quickcast","Allies you control get +1{r} this turn.","","","","classes/dragonheart/Broodmother/Card Name x1.png","Still named 'Card Name' - needs a name; placeholder art"),
("DRG-BRD-002","Command the Brood","DRG-BRD","Skill","Broodmother Defense Skill","","Until the end of the turn, ally abilities you control are quickcast.","","","","classes/dragonheart/Broodmother/Command the Brood x1.png","Placeholder art"),
("DRG-BRD-003","Dragon","DRG-BRD","Ally","Broodmother Ally","","Play over a Drake. Pay 5 Embers to do so. Action, Tap - Deal 3{r} to an enemy.","","","","classes/dragonheart/Broodmother/Dragon x1.png","Placeholder art; needs a Drake card"),
("DRG-BRD-004","Many Whelps","DRG-BRD","Skill","Broodmother Defense Skill","","Pay up to 3{b} Embers. Create a Whelp token for each Ember you pay. If you pay 3 or more Embers this way, you may play 1{r} Drake instead.","","","","classes/dragonheart/Broodmother/Many Whelps x1.png","Placeholder art; no Whelp token or Drake card submitted yet"),
("DRG-BRD-005","With Me, Whelps","DRG-BRD","Skill","Broodmother Attack Skill","Aggro","Deal 2{b} to an enemy, plus 1{r} for each ally you control.","","","","classes/dragonheart/Broodmother/With Me, Whelps x1.png","Placeholder art"),
("DRG-SCB-001","Breath that Scorches","DRG-SCB","Aura","Scaleborn Aura - Transformation","","Tap, pay 3 Embers - Put an Ember on this. You get +1{b} for each Ember on this.","","","","classes/dragonheart/Scaleborn/Breath that Scorches x1.png","Transformation (choose one at creation)"),
("DRG-SCB-002","Ember Strike","DRG-SCB","Skill","Scaleborn Attack Skill","Aggro","Deal 2{r} to any enemy and 1{b} to any enemy stacked with it.","","","","classes/dragonheart/Scaleborn/Ember Strike x1.png","Placeholder art"),
("DRG-SCB-003","Face Me","DRG-SCB","Skill","Scaleborn Defense Skill","Aggro","Choose up to 1{g} enemy not engaged with you. Gain Embers equal to the total Power of enemies chosen.","","","","classes/dragonheart/Scaleborn/Face Me x1.png","Placeholder art"),
("DRG-SCB-004","Hardened Scales","DRG-SCB","Skill","Scaleborn Skill","","Spend up to 2{b} Embers. Gain a Shield for each Ember you spend. If you end the turn with Shield, heal 1{g}.","","","","classes/dragonheart/Scaleborn/Hardened Scales x1.png","Type line has no Attack/Defense"),
("DRG-SCB-005","Scaleborn Command","DRG-SCB","Skill","Scaleborn Attack Skill","","Choose One: Deal 2{b} to an enemy. Heal 2{g}. Gain 2{r} Embers.","","","","classes/dragonheart/Scaleborn/Scaleborn Command x1.png","Placeholder art"),
("DRG-SCB-006","Talons that Strike","DRG-SCB","Aura","Scaleborn Aura - Transformation","","Tap, pay 3 Embers - Put an Ember on this. You get +1{r} for each Ember on this.","","","","classes/dragonheart/Scaleborn/Talons that Strike x1.png","Transformation (choose one at creation)"),
("DRG-SCB-007","Wings that Thunder","DRG-SCB","Aura","Scaleborn Aura - Transformation","","Tap, pay 3 Embers - Put an Ember on this. You get +1{g} for each Ember on this.","","","","classes/dragonheart/Scaleborn/Wings that Thunder x1.png","Transformation (choose one at creation)"),
# --- rogue
("ROG-001","Adrenaline","ROG","Skill","Rogue Defense Skill","","Gain 2{g} actions. If {g} is 4 or more, banish {name}.","","","","classes/rogue/Adrenaline x1.png","Text still has the '{name}' placeholder (should be Adrenaline)"),
("ROG-002","Backstab","ROG","Skill","Rogue Attack Skill","","Deal 2{g} to an enemy. Increase this by 2{r} if you are stealthed.","","","","classes/rogue/Backstab x1.png","Placeholder art"),
("ROG-003","Pocket Sand","ROG","Skill","Rogue Defense Skill","","Stun a non-elite enemy.","","","","classes/rogue/Pocket Sand x1.png",""),
("ROG-004","Riposte","ROG","Skill","Rogue Attack Skill","Quickcast","Choose a non-elite enemy that dealt damage to you last turn. Deal 2{g} to it and disarm it.","","","","classes/rogue/Riposte x1.png","Placeholder art; 'Quickcast' not bolded"),
("ROG-ASN-001","Assassin's Toolbelt","ROG-ASN","Skill","Assassin Defense Skill","","Choose One: Your weapons get +1{r} Power this turn. Heal 1{g}. Draw 1{b} cards.","","","","classes/rogue/Assassin/Assassin's Toolbelt x1.png","Placeholder art"),
("ROG-ASN-002","Go for the Throat","ROG-ASN","Skill","Assassin Attack Skill","","Deal 2{r} to an enemy. This damage ignores all damage reduction.","","","","classes/rogue/Assassin/Go for the Throat x1.png","Placeholder art"),
("ROG-ASN-003","Shiv","ROG-ASN","Skill","Assassin Attack Skill","","Deal 2{r} to an enemy. While stealthed, you may play Shiv from your discard. If you do, recycle it.","","","","classes/rogue/Assassin/Shiv x1.png","Placeholder art"),
("ROG-ASN-004","Smokebomb","ROG-ASN","Skill","Assassin Defense Skill","Quickcast","Gain stealth.","","","","classes/rogue/Assassin/Smokebomb x1.png",""),
("ROG-ASN-005","Strike and Fade","ROG-ASN","Skill","Assassin Attack Skill","","Deal 2{g} to an enemy. If this defeats an enemy, enter stealth.","","","","classes/rogue/Assassin/Strike and Fade x1.png","Placeholder art"),
("ROG-OUT-001","Force to Reckon With","ROG-OUT","Skill","Outlaw Attack Skill","","Deal 3{r} to an enemy, then draw the top card of the encounter deck. If the drawn card is an enemy, gain renown.","","","","classes/rogue/Outlaw/Force to Reckon With x1.png",""),
("ROG-OUT-002","Living in Infamy","ROG-OUT","Skill","Outlaw Attack Skill","","Deal 1{g} to an enemy. Repeat this for every 3 renown you have.","","","","classes/rogue/Outlaw/Living in Infamy x1.png","Placeholder art"),
("ROG-OUT-003","Star of the Show","ROG-OUT","Skill","Outlaw Defense Skill","","Heal 1{b} for each renown you have.","","","","classes/rogue/Outlaw/Star of the Show x1.png",""),
("ROG-OUT-004","Trickshot","ROG-OUT","Skill","Outlaw Attack Skill","","Deal 1{g} to an enemy. If this defeats an enemy, gain renown.","","","","classes/rogue/Outlaw/Trickshot x1.png",""),
("ROG-OUT-005","Wild Card","ROG-OUT","Skill","Outlaw Attack Skill","","Roll the boss die (This doesn't activate boss abilities). A - Deal 2{r} to an enemy. B - Deal 3{r} to an enemy. C - Deal 3{r} to an enemy, then gain renown.","","","","classes/rogue/Outlaw/Wild Card x1.png",""),
# --- encounters: Trouble with Goblins
("TWG-001","Backstabber","TWG","Enemy","Goblin - Generic","Stealth","Stealth (I can't be targeted unless I'm engaged with you).","2","2","","encounters/Trouble with Goblins/Backstabber x2.png",""),
("TWG-002","Beast Tamer","TWG","Enemy","Elite Goblin - Unique","","Enter - Create a 1/4 Beast token stacked in front of me.","1","2","","encounters/Trouble with Goblins/Beast Tamer x1.png",""),
("TWG-003","Bow and Arrow Goblin","TWG","Enemy","Goblin - Backline (Generic)","","","2","2","","encounters/Trouble with Goblins/Bow and Arrow Goblin x2.png","No rules text"),
("TWG-004","Goblin Horde","TWG","Enemy","Goblin - Generic (Backline)","Reinforce","At the start of each round, Goblin Horde reinforces (Add a body to Goblin Horde). While Goblin Horde has 5 or more bodies, it gets +1P.","1","2*","","encounters/Trouble with Goblins/Goblin Horde x4.png","Health shown as blue 2* (Horde bodies, * = per player?)"),
("TWG-005","Goblin Lackey","TWG","Enemy","Goblin - Generic","","","1","3","","encounters/Trouble with Goblins/Goblin Lackey x3.png","Vanilla"),
("TWG-006","Goblin Rallyman","TWG","Enemy","Goblin - Backline (Generic)","","Stacks Horde only. When I enter and at the start of each round, reinforce each goblin horde.","1","3","","encounters/Trouble with Goblins/Goblin Rallyman x2.png",""),
("TWG-007","Goblin Shaman","TWG","Enemy","Goblin - Backline (Generic)","","Generics I'm stacked with get +1P. While I'm not stacked, I get +1P.","1","2","","encounters/Trouble with Goblins/Goblin Shaman x2.png",""),
("TWG-008","Goblin with a Bomb","TWG","Enemy","Goblin - Vanguard (Any)","","Act - Discard me and deal 3 damage to the player engaged to me.","0","3","","encounters/Trouble with Goblins/Goblin with a Bomb x2.png",""),
("TWG-009","Rout","TWG","Event","Event","Cascade","Choose an enemy stack or boss. It engages you.","","","","encounters/Trouble with Goblins/Rout x1.png",""),
("TWG-010","Sharp Shooters","TWG","Obstacle","Obstacle","","Whenever a player recycles a card, they take 1 damage.","","","{g}|{g}","encounters/Trouble with Goblins/Sharp Shooters x2.png","Channel shown with laurel icon + G|G"),
# --- Ire of the Goblin King
("IGK-001","CHARGE!","IGK","Event","Event","","If no enemies are engaged to you, this gains cascade. Enemies engaged to you gain +1P until end of turn.","","","","encounters/Ire of the Goblin King/CHARGE! x2.png",""),
("IGK-002","Eye of the Goblin King","IGK","Event","Event","","Roll the boss die. A - Summon a set aside or discarded Goblin Horde. B - The Goblin King engages you. C - Do both.","","","","encounters/Ire of the Goblin King/Eye of the Goblin King x2.png","References The Goblin King - no Goblin King card submitted"),
("IGK-003","Ogre Stomper","IGK","Enemy","Elite Ogre - Vanguard (Backline)","Enrage 2","Enrage 2 (While damaged I get +2P).","1","6","","encounters/Ire of the Goblin King/Ogre Stomper x1.png",""),
("IGK-004","Totem","IGK","Obstacle","Obstacle","","When I enter and at the start of each round, reinforce each Goblin Horde. Goblin Hordes get +1P.","","","{r}|{r}","encounters/Ire of the Goblin King/Totem x2.png","Channel shown with laurel icon + R|R"),
# --- Magical Mishaps
("MMS-001","Amalgamation","MMS","Enemy","Elite Ooze - Unique","","Enter - Stacks to the front of the largest stack. Amalgamation's health is equal to double the enemies in its stack. If there are 3 or more enemies in its stack, Amalgamation gets +1P.","1","*","","encounters/Magical Mishaps/Amalgamation x1.png",""),
("MMS-002","Confounding Concoction","MMS","Event","Event","","Choose a Gem Color, then discard the top card of your deck. If the discarded card has the chosen color, heal 1. Otherwise, take 2 damage.","","","","encounters/Magical Mishaps/Confounding Concoction x2.png","Typo on card: 'Otherise'"),
("MMS-003","Potion Snatcher","MMS","Enemy","Goblin - Unique (Behind Any)","Cascade","Defeat - Create your choice of a Strength, Agility or Intellect token.","1","2","","encounters/Magical Mishaps/Potion Snatcher x1.png",""),
("MMS-004","Solution","MMS","Event","Event","","Remove an armor token from a boss.","","","","encounters/Magical Mishaps/Solution x4.png",""),
# --- Portal to Problems
("PTP-001","Portal to Problems","PTP","Event","Event","","Draw a random card from the & Cache. If you can't, this gains cascade.","","","","encounters/Portal to Problems/Portal to Problems x3.png","Needs an & Cache to be set up"),
# --- Trials and Tribulations
("TAT-001","Exhausted","TAT","Event","Event","","Lose an action unless you discard a {g} card.","","","","encounters/Trials and Tribulations/Exhausted x1.png",""),
("TAT-002","Daunted","TAT","Event","Event","","Banish a card from your hand unless you discard a {b} card.","","","","encounters/Trials and Tribulations/Daunted x1.png","Replaced Lose an Action (Nov 24)"),
("TAT-003","Overwhelmed","TAT","Event","Event","","Tap your hero and weapon unless you discard a {r} card.","","","","encounters/Trials and Tribulations/Overwhelmed x1.png",""),
("SOL-001","Abomination","SOL","Enemy","Elite Undead - Vanguard","Dread","Dread. Whenever a player draws a Dread card, Abomination aggros to them.","2","6","","encounters/Servants of the Lich/Abomination x1.png",""),
("SOL-002","Death Knight","SOL","Enemy","Undead - Vanguard","Armor","Armor 1. Whenever you draw a Dread card, Death Knight gets +1P this turn.","1","4","","encounters/Servants of the Lich/Death Knight x2.png",""),
("SOL-003","Ghoulcaller","SOL","Enemy","Undead - Backline (Horde)","Enter","Enter - If there is no Undead Horde on the field, search the encounter deck and discard pile and summon it stacked with me. Hordes stacked with me get +1 Power.","1","3","","encounters/Servants of the Lich/Ghoulcaller x1.png",""),
("SOL-004","Lich's Servant","SOL","Enemy","Undead - Backline","Dread, Enter","Dread. Enter - For each encounter type in the discard, put a power counter on Lich.","0","4","","encounters/Servants of the Lich/Lich's Servant x1.png",""),
("SOL-005","Power of the Lich","SOL","Event","Event","Dread, Cascade","Dread, Cascade.","","","","encounters/Servants of the Lich/Power of the Lich x2.png",""),
("SOL-006","Undead Horde","SOL","Enemy","Undead - Generic","Reinforce","Whenever a non-horde enemy is defeated, Undead Horde reinforces. Whenever you draw a Dread card, Undead Horde gets +1P this turn.","1","2*","","encounters/Servants of the Lich/Undead Horde x3.png","Horde: 2 bodies per player"),
("SOL-007","Wailing Banshee","SOL","Enemy","Undead - Generic","Act","Whenever a player cycles a card, I deal 1 damage to them. Act: Each player cycles a card.","0","4","","encounters/Servants of the Lich/Wailing Banshee x2.png",""),
("SDK-001","Blue Poison","SDK","Event","Event","Cascade","Gain a {b} Poison, then choose:\n- Cards you play lose 1{b} this turn.\n- Cascade","","","","encounters/The Silken Dark/Blue Poison x1.png","Set aside (poisons are put on heroes)"),
("SDK-002","Green Poison","SDK","Event","Event","Cascade","Gain a {g} Poison, then choose:\n- Cards you play lose 1{g} this turn.\n- Cascade","","","","encounters/The Silken Dark/Green Poison x1.png","Set aside (poisons are put on heroes)"),
("SDK-003","Hatching Room","SDK","Obstacle","Obstacle","Act","Act - Put the top card of the encounter deck onto the field face down as an Egg with Hatch 3.","","","{r}{g}|{r}","encounters/The Silken Dark/Hatching Room x1.png","Room obstacle; set aside"),
("SDK-004","Lurking Webs","SDK","Obstacle","Obstacle","","During the Encounter phase, put cards face down in front of you instead of drawing them. At the end of the hero phase, reveal each face down encounter card and resolve them.","","","{g}|{b}","encounters/The Silken Dark/Lurking Webs x1.png","Room obstacle; set aside"),
("SDK-005","Pouncing Spider","SDK","Enemy","Spider - Generic","Enter","Enter - If I'm drawn or revealed from outside the encounter deck, I get a +1 Power counter.","1","3","","encounters/The Silken Dark/Pouncing Spider x2.png","Set aside"),
("SDK-006","Red Poison","SDK","Event","Event","Cascade","Gain a {r} Poison, then choose:\n- Cards you play lose 1{r} this turn.\n- Cascade","","","","encounters/The Silken Dark/Red Poison x1.png","Set aside (poisons are put on heroes)"),
("SDK-007","Webbed","SDK","Obstacle","Obstacle","Solo","Solo (This obstacle only affects the player who drew it.)\nYou can only spend actions to channel this obstacle. When this obstacle is cleared, add it to the & Cache.","","","{g}","encounters/The Silken Dark/Webbed x4.png","Starts in the & cache"),
("SDK-008","Webbing Spider","SDK","Enemy","Spider - Backline","Act","Act - Draw a Webbed from the & Cache, then Webbing Spider aggros to the player to your left.","1","3","","encounters/The Silken Dark/Webbing Spider x2.png","Set aside"),
("SDK-009","What Awaits","SDK","Event","Event","","Attached enemy gets +1* Health and +1 Power.","","","","encounters/The Silken Dark/What Awaits x1.png","Starts in the $ cache; attached at B1"),
("SDS-001","Broodtender","SDS","Enemy","Spider - Backline","Enter, Act","Enter - Put the top card of the encounter deck onto the field face down as an Egg with Hatch 3.\nAct - Remove a counter from each Egg.","0","3","","encounters/Silken Dark Spiders/Broodtender x2.png",""),
("SDS-002","Giant Red Spider","SDS","Enemy","Elite Spider - Vanguard","Act","Act - Put a {r} Poison on the hero I'm aggroed to. (It deals 1 damage to you at Rally until you recycle a {r} card as an action.)","1","5","","encounters/Silken Dark Spiders/Giant Red Spider x1.png",""),
("SDS-003","Green Spider","SDS","Enemy","Spider - Generic","Act","Act - Put a {g} Poison on the hero I'm aggroed to. (It deals 1 damage to you at Rally until you recycle a {g} card as an action.)","0","3","","encounters/Silken Dark Spiders/Green Spider x2.png",""),
("SDS-004","Mind-Numbing Spider","SDS","Enemy","Spider - Generic","Act","Act - Put a {b} Poison on the hero I'm aggroed to. (It deals 1 damage to you at Rally until you recycle a {b} card as an action.)","0","3","","encounters/Silken Dark Spiders/Mind-Numbing Spider x2.png",""),
("SDS-005","Spider Horde","SDS","Enemy","Spider - Vanguard","","We get +1P while aggroed to a poisoned hero.","1","2*","","encounters/Silken Dark Spiders/Spider Horde x3.png","Horde: 2 bodies per player"),
("SDS-006","Thread Ender","SDS","Enemy","Elite Spider - Unique","Finale, Act","Finale (I resolve and act last.)\nAct - Deal 1 damage to each hero for each poison on them.","0","4","","encounters/Silken Dark Spiders/Thread Ender x1.png",""),
("COC-001","Boots of Swiftness","COC","Journey Asset","Journey Asset - Item","Exhaust","Exhaust - Your cards get +1{g} this turn.\nExhaust - Give this asset to another player.","","","","encounters/Cocooned/Boots of Swiftness x1.png","Starts in the % cache"),
("COC-002","Giant's Belt","COC","Journey Asset","Journey Asset - Item","Exhaust","Exhaust - Your cards get +1{r} this turn.\nExhaust - Give this asset to another player.","","","","encounters/Cocooned/Giant's Belt x1.png","Starts in the % cache"),
("COC-003","Imra, Student","COC","Journey Asset","Journey Asset - Ally","Exhaust","Exhaust - The next time a player plays a defense skill this turn, they draw a card.\n\"Please don't tell my professor you had to save me...\"","","","","encounters/Cocooned/Imra, Student x1.png","Starts in the % cache"),
("COC-004","Old Gorrik","COC","Journey Asset","Journey Asset - Ally","Exhaust","Exhaust - The next time a player attacks with a weapon this turn, that weapon has +1 Power.\n\"I had the situation under control.\"","","","","encounters/Cocooned/Old Gorrik x1.png","Starts in the % cache"),
("COC-005","Tome of Knowledge","COC","Journey Asset","Journey Asset - Item","Exhaust","Exhaust - Your cards get +1{b} this turn.\nExhaust - Give this asset to another player.","","","","encounters/Cocooned/Tome of Knowledge x1.png","Starts in the % cache"),
("COC-006","Wren","COC","Journey Asset","Journey Asset - Ally","Exhaust","Exhaust - The next time a player plays an attack skill this turn, they gain an action.\n\"Thanks for the save, now let's get out of here.\"","","","","encounters/Cocooned/Wren x1.png","Starts in the % cache"),
("CAV-001","Bat Swarm","CAV","Enemy","Beast - Generic","Flight, Horde","Flight (This enemy takes half damage from all sources, rounded up.)","1","2*","","encounters/Cavern Creatures/Bat Swarm x2.png","Horde: 2 bodies per player"),
("CAV-002","Giant Spider","CAV","Enemy","Elite Beast - Vanguard","Act","Act - Reinforce each horde in play.","2","6","","encounters/Cavern Creatures/Giant Spider x1.png",""),
("BOS-001","Boss Horde","BOS","Enemy","Enemy Type - Generic (Any)","","Whenever the boss die is rolled, my power is set based on the result: A - 1, B - 2, C - 3.","0","2*","","encounters/Bosses/Boss Horde x1.png","Generic boss set (works with any boss). Horde: 2 bodies per player"),
("BOS-002","Champion","BOS","Enemy","Enemy Type - Vanguard (Any)","","Bosses get Armor 1.","2","5","","encounters/Bosses/Champion x1.png","Generic boss set"),
("BOS-003","Feel My Wrath","BOS","Event","Event","","Roll the boss die.","","","","encounters/Bosses/Feel My Wrath x1.png","Generic boss set"),
("BOS-004","I Will Not Fall","BOS","Event","Event","Cascade","Remove 1* damage from the Boss. If no damage is removed this way, this gains Cascade.","","","","encounters/Bosses/I Will Not Fall x1.png","Generic boss set"),
("BOS-005","Kneel","BOS","Event","Event","","Each player taps their hero and weapon.","","","","encounters/Bosses/Kneel x1.png","Generic boss set"),
("BOS-006","My Patience Ends","BOS","Event","Event","","Put a +1 Power counter on the boss.","","","","encounters/Bosses/My Patience Ends x1.png","Generic boss set"),
# --- encounter tokens
("ETK-001","Beast","ETK","Enemy","Beast","","","1","4","","encounters/tokens/Beast x1.png","Rules text is the template placeholder 'Card Text'"),
("ETK-002","Peasant","ETK","Obstacle","Obstacle","","\"More work?\"","","","{g}|{b}","encounters/tokens/Peasant x4.png",""),
]

SETS = [  # set, name, kind, class, subclass, back
("CHR","Hero cards","Hero","","",P),("ANC","Ancestry","Ancestry","","",P),
("MAG","Mage - Core","Class core","Mage","",P),("MAG-FIR","Mage - Fire","Subclass","Mage","Fire",P),("MAG-ICE","Mage - Ice","Subclass","Mage","Ice",P),
("WAR","Warrior - Core","Class core","Warrior","",P),("WAR-BLD","Warrior - Blade Dancer","Subclass","Warrior","Blade Dancer",P),("WAR-IRC","Warrior - Ironclad","Subclass","Warrior","Ironclad",P),
("PRI","Priest - Core","Class core","Priest","",P),("PRI-ANO","Priest - Anointed","Subclass","Priest","Anointed",P),("PRI-SER","Priest - Seraph","Subclass","Priest","Seraph",P),
("DRG","Dragonheart - Core","Class core","Dragonheart","",P),("DRG-BRD","Dragonheart - Broodmother","Subclass","Dragonheart","Broodmother",P),("DRG-SCB","Dragonheart - Scaleborn","Subclass","Dragonheart","Scaleborn",P),
("ROG","Rogue - Core","Class core","Rogue","",P),("ROG-ASN","Rogue - Assassin","Subclass","Rogue","Assassin",P),("ROG-OUT","Rogue - Outlaw","Subclass","Rogue","Outlaw",P),
("TWG","Trouble with Goblins","Encounter set","","",E),("IGK","Ire of the Goblin King","Encounter set","","",E),
("MMS","Magical Mishaps","Encounter set","","",E),("PTP","Portal to Problems","Encounter set","","",E),
("TAT","Trials and Tribulations","Encounter set","","",E),("BOS","Bosses","Encounter set","","",E),("SOL","Servants of the Lich","Encounter set","","",E),("SDK","The Silken Dark","Encounter set","","",E),("SDS","Silken Dark Spiders","Encounter set","","",E),("COC","Cocooned","Encounter set","","",E),("CAV","Cavern Creatures","Encounter set","","",E),("ETK","Encounter tokens","Tokens","","",E),
]
CLASSES = [  # class, subclass, hero, weapon (blank = none yet), core_set, subclass_set, health (blank = 10),
             # choose_one: a trait word - subclass cards with it are a pick-one group at creation (e.g. Scaleborn Transformations)
("Mage","Fire","CHR-MAG","MAG-W01","MAG","MAG-FIR",""),("Mage","Ice","CHR-MAG","MAG-W01","MAG","MAG-ICE",""),
("Warrior","Blade Dancer","CHR-WAR","WAR-W01","WAR","WAR-BLD",""),("Warrior","Ironclad","CHR-WAR","WAR-W01","WAR","WAR-IRC",""),
("Priest","Anointed","CHR-PRI","","PRI","PRI-ANO",""),("Priest","Seraph","CHR-PRI","","PRI","PRI-SER",""),
("Dragonheart","Broodmother","CHR-DRG","","DRG","DRG-BRD",""),("Dragonheart","Scaleborn","CHR-DRG","","DRG","DRG-SCB","","Transformation"),
("Rogue","Assassin","CHR-ROG","","ROG","ROG-ASN",""),("Rogue","Outlaw","CHR-ROG","","ROG","ROG-OUT",""),
]
ADVENTURES = [  # adventure_id, name, level, players, set, use, set_aside (card ids kept out of the deck, face up), note
# (the sheet also has a 'description' column - text there on the adventure's first row is shown in the Encounters menu)
("TWG","Trouble with Goblins",1,"1-4","TWG","all","TWG-004","Goblin Hordes are set aside; the rest is shuffled in"),
("TWG","Trouble with Goblins",1,"1-4","TAT","all","","Shuffled into the encounter deck"),
("TWG","Trouble with Goblins",1,"1-4","IGK","staged","","Shuffled in at B2 The Goblin King Arrives"),
("TWG","Trouble with Goblins",1,"1-4","MMS","staged","","Shuffled in at C1 The Wizard's Tower"),
("TWG","Trouble with Goblins",1,"1-4","PTP","staged","","Shuffled in at C1 The Wizard's Tower"),
("TWG","Trouble with Goblins",1,"1-4","ETK","setaside","","Peasant + Beast tokens, face up"),
# use = "cache:<sigil>" puts the set face down in that cache pile; "cache:<sigil>:<ids>" only those cards.
# Cards a row names that way are left out of the set's other rows.
("SDK","The Silken Dark",1,"1-4","SDS","all","","Shuffled into the encounter deck"),
("SDK","The Silken Dark",1,"1-4","TAT","all","","Shuffled into the encounter deck"),
("SDK","The Silken Dark",1,"1-4","CAV","all","","Shuffled into the encounter deck"),
("SDK","The Silken Dark",1,"1-4","SDK","cache:&:SDK-007","","Webbed cards start in the & cache"),
("SDK","The Silken Dark",1,"1-4","SDK","cache:$:SDK-009","","What Awaits starts in the $ cache"),
("SDK","The Silken Dark",1,"1-4","COC","cache:%","","Cocooned cards start in the % cache (the doc's # cache)"),
("SDK","The Silken Dark",1,"1-4","SDK","all","","The rest of The Silken Dark (Poisons, rooms, spiders) is shuffled in too"),
]
# Journey map. col/row place the node on the board (col 0-2 left->right, row 0-2 top->bottom).
# actions (run when the party journeys to the node), separated by ';':
#   summon:<card id>:<n>     move n set-aside copies to the summon area (n may be '1*' = per player)
#   shuffle:<SET>,<SET>      shuffle those staged sets + the encounter discard into the encounter deck
#   boss:<boss id>[:armor=<n>]  put the boss on the journey board
JOURNEY = [  # adventure_id, node, name, col, row, next, actions, rules
("TWG","A1","Attack on the Town",0,1,"B1,C1","summon:TWG-004:1",
 "At Start: Summon 1 set aside Goblin Horde. While Here: At the start of each round, spawn Peasant Obstacles with {g} until there are 1*. Whenever a Peasant Obstacle is cleared, add a counter here. Once there are 2* counters here, Journey Forward."),
("TWG","B1","The Goblin Encampment",1,0,"B2","summon:TWG-004:1",
 "At Start: Summon 1 set aside Goblin Horde. While Here: Whenever you defeat a Goblin, add a counter here. Once there are 2* counters here, Journey Forward."),
("TWG","B2","The Goblin King Arrives",2,0,"","shuffle:IGK;boss:GK-CAMP",
 "Shuffle Ire of the Goblin King along with the discard pile into the encounter deck. Summon The Goblin King. When The Goblin King is defeated, you win!"),
("TWG","C1","The Wizard's Tower",2,2,"","shuffle:MMS,PTP;boss:GK-TOWER:armor=1*",
 "Shuffle Portal to Problems and Magical Mishaps along with the discard pile into the encounter deck. Summon The Goblin King, then put 1* Armor Counters on him. When The Goblin King is defeated, you win!"),
("SDK","A1","Descending through Silk",0,1,"B1,C1","cachetop:%:4; track:Descent:4",
 "Setup: shuffle the top 4 cards of the encounter deck into the % Cache. Start - Place each hero's aggro token at the top of the silken caves. Here - Each hero has Exhaust Action - Move down 1 floor. When you Rally, if all surviving heroes are at the bottom floor, Journey Forward."),
("SDK","B1","What Awaits",1,0,"D1","awaits:$",
 "Enter - Discard cards from the top of the encounter deck until an Elite is discarded. Spawn that enemy and attach the What Awaits card from the $ Cache to it. When you Rally, if the What Awaits enemy is defeated, Journey Forward."),
("SDK","C1","Rescuing the Captured",1,2,"B1","",
 "Here - Each hero has Action - Add the top card of the % Cache to the field face down as a Cocoon with 1 health and 'Loot - Flip and draw me.' When you Rally, if 1* Journey Assets are in play, Journey Forward."),
("SDK","D1","The Weaver Below",2,0,"","boss:WEAVER",
 "Start - Spawn The Weaver Below."),
]
BOSSES = [  # boss_id, name, traits, power, health, text, A, B, C
("WEAVER","The Weaver Below","Elite Enemy - Spider",0,"5*","",
 "Put a {g} Poison on each player.",
 "Put the top 1|2 cards of the encounter deck onto the field face down as Eggs with Hatch 2.",
 "Each player without one draws a set aside Webbed obstacle from the & Cache."),
("GK-CAMP","The Goblin King","Elite Enemy - Goblin",1,"4*","The Goblin King cannot be attacked while there is a Horde in play.",
 "Reinforce all Goblin Hordes twice.",
 "Put a Power Counter on the Goblin Horde with the most bodies. If you can't, put a Power Counter on the Goblin King instead.",
 "Spawn a set aside Goblin Horde or a Goblin Horde from the discard pile."),
("GK-TOWER","The Goblin King","Elite Enemy - Goblin",1,"4*","The Goblin King cannot be attacked while there is a Horde in play.",
 "Discard the top 5 cards of the encounter deck. If a Solution is discarded, a player may banish a {g} card to draw it instead.",
 "If there is a discarded Solution, banish it and put a Power Counter onto the Goblin King.",
 "Each player draws an encounter card. Enemies summoned this way enter stunned."),
]

ENHANCEMENTS = [  # enh_id, card_id, name, sticker_text  (stickers the Forge can put on a card)
]

def write(path):
    wb=Workbook(); H=Font(bold=True,color="FFFFFF"); HF=PatternFill("solid",fgColor="3B3054")
    def tab(ws,headers,rows,widths,name):
        ws.append(headers); [ws.append(list(r)) for r in rows]
        for i,w in enumerate(widths): ws.column_dimensions[chr(65+i)].width=w
        for c in ws[1]: c.font=H; c.fill=HF
        ws.freeze_panes="A2"
        t=Table(displayName=name,ref=f"A1:{chr(64+len(headers))}{len(rows)+1}")
        t.tableStyleInfo=TableStyleInfo(name="TableStyleLight9",showRowStripes=True); ws.add_table(t)
        for row in ws.iter_rows(min_row=2):
            for c in row: c.alignment=Alignment(wrap_text=True,vertical="top")
    ws=wb.active; ws.title="Cards"
    tab(ws,["id","name","set","card_type","traits","keywords","text","power","health","channel","qty","source_file","notes"],
        [(c[0],c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],qty(c[10]),"cards/"+c[10],c[11]) for c in CARDS],
        [13,20,9,10,24,14,52,6,7,9,5,40,40],"Cards")
    tab(wb.create_sheet("Sets"),["set","name","kind","class","subclass","back"],SETS,[10,24,14,9,13,10],"Sets")
    tab(wb.create_sheet("Classes"),["class","subclass","hero","weapon","core_set","subclass_set","health","choose_one"],[c+("",)*(8-len(c)) for c in CLASSES],[11,13,9,9,9,12,8,14],"Classes")
    tab(wb.create_sheet("Adventures"),["adventure_id","name","level","players","set","use","set_aside","note","description"],[a+("",) for a in ADVENTURES],[12,22,6,8,7,9,12,50,60],"Adventures")
    tab(wb.create_sheet("Journey"),["adventure_id","node","name","col","row","next","actions","rules"],JOURNEY,[12,6,24,5,5,8,40,70],"Journey")
    tab(wb.create_sheet("Bosses"),["boss_id","name","traits","power","health","text","A","B","C"],BOSSES,[11,18,20,6,7,40,40,40,40],"Bosses")
    tab(wb.create_sheet("Enhancements"),["enh_id","card_id","name","sticker_text"],
        ENHANCEMENTS or [("(example) ENH-001","PRI-002","Miracle: Quickcast",'Delete this row. "sticker_text" is what the sticker says.')],[16,12,24,60],"Enhancements")
    tab(wb.create_sheet("Talents"),["class","node_id","name","color","parents","cost","reward_type","reward","notes"],
        [("(example)","MAG-T01","","R","","1","gem","+1{r}","Fill in when talent trees are ready")],[9,9,16,6,10,5,11,14,30],"Talents")
    wb.save(path)

if __name__=="__main__":
    write(sys.argv[1])
    print(len(CARDS),"card rows,",sum(qty(c[10]) for c in CARDS),"physical cards")
