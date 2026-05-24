from dotenv import load_dotenv
import os
import random

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
from discord import Interaction

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
# default to test if not set
MODE = os.getenv("BOT_MODE", "test")  
# needed only for testing
GUILD_ID_ENV = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID_ENV) if GUILD_ID_ENV else None 


intents = discord.Intents.default()
intents.message_content = True

# Supabase table
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


HEAD = "<:limbus_heads:1463921098394439774>"
TAIL = "<:limbus_tails:1463921048704647188>"
UNBREAKABLE_HEAD = "<:limbus_unbreakable_heads:1463921190228721684>"
UNBREAKABLE_TAIL = "<:limbus_unbreakable_tails:1463921283946512566>"
UNBREAKABLE_CRACKED_HEAD = "<:limbus_cracked_unbreakable_heads:1508202401620955378>"
UNBREAKABLE_CRACKED_TAIL = "<:limbus_cracked_unbreakable_tails:1508202503349469264>"
MAX_SANITY = 45
MIN_SANITY = -45
ATTACK_TYPES = ["Slash", "Pierce", "Blunt"]
DEF_ROLES = ["Guard", "Evade", "Counter"]
SIN_AFFINITIES = ["Wrath", "Lust", "Sloth", "Gluttony", "Gloom", "Pride", "Envy"]
SLOTS = ["1", "2", "3", "Guard", "Evade", "Counter"]

EMOJIS_ATK_TYPE = {
"SLASH": "<:Slash:1479599322336198778>",
"PIERCE": "<:Pierce:1479599216551657674>",
"BLUNT": "<:Blunt:1479599265100726332>"
}

EMOJIS_ROLE = {
    "GUARD": "<:Guard:1479784787458916392>",
    "EVADE": "<:Evade:1479784818769399849>",
    "COUNTER": "<:Counter:1479784856916328574>"
}

EMOJIS_SIN = {
    "WRATH": "<:Wrath:1479599693330645083>",
    "LUST": "<:Lust:1479599653006610563>",
    "SLOTH": "<:Sloth:1479599606202372178>",
    "GLUTTONY": "<:Gluttony:1479599563768729792>",
    "GLOOM": "<:Gloom:1479599509179863091>",
    "PRIDE": "<:Pride:1479599460538646700>",
    "ENVY": "<:Envy:1479599410877960377>" 
}

# helper function for emojis
def get_skill_emojis(attack_type=None, sin_affinity=None, role=None):

    role = (role or "").upper()
    attack_type = (attack_type or "").upper()
    sin_affinity = (sin_affinity or "").upper()

    emoji_part = ""

    # Role emoji has priority
    if role and role in EMOJIS_ROLE:
        emoji_part += EMOJIS_ROLE[role]

    # If no role emoji, fallback to attack type emoji
    elif attack_type and attack_type in EMOJIS_ATK_TYPE:
        emoji_part += EMOJIS_ATK_TYPE[attack_type]

    sin_emoji = EMOJIS_SIN.get(sin_affinity, "")

    return emoji_part, sin_emoji

# ----------------------
# Limbus Skill Functions
# ----------------------

# Save Skill Function
def save_skill(user_id, skill_name, base_power, coin_power, coins, unbreakable):
    # Get max skill id for user
    res = (
        supabase
        .table("skills")
        .select("user_skill_id")
        .eq("user_id", user_id)
        .order("user_skill_id", desc=True)
        .limit(1)
        .execute()
    )

    user_skill_id = (res.data[0]["user_skill_id"] if res.data else 0) + 1

    supabase.table("skills").upsert({
        "user_id": user_id,
        "user_skill_id": user_skill_id,
        "skill_name": skill_name,
        "base_power": base_power,
        "coin_power": coin_power,
        "coins": coins,
        "unbreakable": unbreakable
    }).execute()

    return user_skill_id

# Load skill function (for /flip)
def load_skill(user_id, skill_name=None, skill_id=None):
    query = supabase.table("skills").select(
        "skill_name, base_power, coin_power, coins, unbreakable"
    ).eq("user_id", user_id)

    if skill_id is not None:
        query = query.eq("user_skill_id", skill_id)
    elif skill_name is not None:
        query = query.eq("skill_name", skill_name)
    else:
        return None

    res = query.limit(1).execute()

    if not res.data:
        return None

    row = res.data[0]
    return (
        row["skill_name"],
        row["base_power"],
        row["coin_power"],
        row["coins"],
        row["unbreakable"]
    )

# Delete skill function
def delete_skill(user_id, skill_name=None, skill_id=None):
    query = supabase.table("skills").select("skill_name").eq("user_id", user_id)

    if skill_id is not None:
        query = query.eq("user_skill_id", skill_id)
    elif skill_name is not None:
        query = query.eq("skill_name", skill_name)
    else:
        return None

    res = query.limit(1).execute()
    if not res.data:
        return None

    skill_name = res.data[0]["skill_name"]

    delete_query = supabase.table("skills").delete().eq("user_id", user_id)
    if skill_id is not None:
        delete_query = delete_query.eq("user_skill_id", skill_id)
    else:
        delete_query = delete_query.eq("skill_name", skill_name)

    delete_query.execute()
    return skill_name

# Helper function to flip coins (for /clash)
def flip_skill(user_id, skill_name,  skill_id, sanity, skill_data):
    base_power, coin_power, coins, unbreakable = skill_data
    total_power = base_power
    normal_coins = coins - unbreakable
    head_chance = 50 + sanity
    trail = ""

    # Normal coins
    for _ in range(normal_coins):
        roll = random.randint(1, 100)
        if roll <= head_chance:
            total_power += coin_power
            trail += f"{HEAD} "
        else:
            trail += f"{TAIL} "

    # Unbreakable coins
    for _ in range(unbreakable):
        roll = random.randint(1, 100)
        if roll <= head_chance:
            total_power += coin_power
            trail += f"{UNBREAKABLE_HEAD} "
        else:
            trail += f"{UNBREAKABLE_TAIL} "

    return total_power, normal_coins, unbreakable, trail

# ----------------------
# TTRPG Skill Functions
# ----------------------

# Save Skill TTRPG Function
async def save_skill_ttrpg(
    user_id: str,
    skill_slot: str,
    skill_name: str,
    base_power: int,
    dice_power: int,
    attack_type: str = None,
    sin_affinity: str = None
):
    result = supabase.table("ttrpg_skills") \
        .select("user_skill_id") \
        .eq("user_id", user_id) \
        .order("user_skill_id", desc=True) \
        .limit(1) \
        .execute()

    row = result.data[0] if result.data else None
    user_skill_id = (row["user_skill_id"] if row else 0) + 1

    # Insert the skill into the database
    supabase.table("ttrpg_skills").insert({
        "user_id": user_id,
        "user_skill_id": user_skill_id,
        "skill_slot": skill_slot,
        "skill_name": skill_name,
        "base_power": base_power,
        "dice_power": dice_power,
        "attack_type": attack_type,
        "sin_affinity": sin_affinity
    }).execute()

    return user_skill_id

# Load Skill TTRPG Function (for /roll_ttrpg)
async def load_skill_ttrpg(user_id: str, skill_name: str = None, skill_id: int = None):
    query = supabase.table("ttrpg_skills").select("*").eq("user_id", user_id)

    if skill_id is not None:
        query = query.eq("user_skill_id", skill_id)
    elif skill_name is not None:
        query = query.eq("skill_name", skill_name)
    else:
        return None

    result = query.execute()
    if result.data:
        row = result.data[0]
        return row["skill_slot"], row["skill_name"], row["base_power"], row["dice_power"], row["attack_type"], row["sin_affinity"]
    return None

# Delete Skill TTRPG Function
async def delete_skill_ttrpg(user_id: str, skill_name: str = None, skill_id: int = None):
    skill = await load_skill_ttrpg(user_id, skill_name, skill_id)
    if not skill:
        return None

    skill_slot, skill_name = skill[0], skill[1]

    if skill_id is not None:
        supabase.table("ttrpg_skills").delete().eq("user_id", user_id).eq("user_skill_id", skill_id).execute()
    else:
        supabase.table("ttrpg_skills").delete().eq("user_id", user_id).eq("skill_name", skill_name).execute()

    return skill_name

# Helper function to apply sanity effects
def apply_sanity_mod(sanity: int, base_power: int, dice_power: int) -> tuple[int, int]:
    positive_coin = dice_power >= 0
    mod_base = base_power
    mod_dice = abs(dice_power)
    
    if positive_coin:
        if -45 <= sanity <= -41:
            mod_base -= 3
            mod_dice += 2
        elif -40 <= sanity <= -21:
            mod_base -= 2
            mod_dice += 2
        elif -20 <= sanity <= -1:
            mod_base -= 1
            mod_dice += 1
        elif 1 <= sanity <= 20:
            mod_base += 1
            mod_dice -= 1
        elif 21 <= sanity <= 40:
            mod_base += 2
            mod_dice -= 2
        elif 41 <= sanity <= 45:
            mod_base += 3
            mod_dice -= 2
    else:  # negative coins, reverse effects
        if -45 <= sanity <= -41:
            mod_base += 3
            mod_dice -= 2
        elif -40 <= sanity <= -21:
            mod_base += 2
            mod_dice -= 2
        elif -20 <= sanity <= -1:
            mod_base += 1
            mod_dice -= 1
        elif 1 <= sanity <= 20:
            mod_base -= 1
            mod_dice += 1
        elif 21 <= sanity <= 40:
            mod_base -= 2
            mod_dice += 2
        elif 41 <= sanity <= 45:
            mod_base -= 3
            mod_dice += 2

    # Prevent dice from going below 1
    mod_dice = max(1, mod_dice)
    return mod_base, mod_dice

# Helper function to roll ttrpg skills
async def roll_skill_ttrpg(skill_data, sanity: int):
    skill_slot, skill_name, base_power, dice_power, attack_type, sin_affinity = skill_data

    mod_base, mod_dice = apply_sanity_mod(sanity, base_power, dice_power)

    dice_sign = 1 if dice_power >= 0 else -1
    roll = random.randint(1, abs(mod_dice))
    total = mod_base + (dice_sign * roll)

    role = resolve_skill_role(skill_slot)

    return total, roll, mod_base, mod_dice, attack_type, sin_affinity, role

# helper function for classifying skill types
def resolve_skill_role(skill_slot):
    if not skill_slot:
        return "attack"

    slot = str(skill_slot).lower()

    if slot == "guard":
        return "guard"
    if slot == "evade":
        return "evade"
    if slot == "counter":
        return "counter"

    return "attack"

# helper for gathering combat info
def get_combat_identity(skill_slot, attack_type, sin_affinity):
    role = resolve_skill_role(skill_slot)

    visual_type = role if role in ["guard", "evade", "counter"] else attack_type

    return get_skill_emojis(visual_type, sin_affinity)
        
# Sync tree once the bot is ready
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    if MODE == "test":
        if GUILD_ID is None:
            raise RuntimeError("GUILD_ID is required in test mode but was not set")

        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Logged in as {bot.user} (TESTING)")
    else:
        await bot.tree.sync()
        print(f"Logged in as {bot.user} (GLOBAL)")

# ----------------------
# Limbus Slash Commands
# ----------------------

# Save Skill /Command
@bot.tree.command(name="save_skill", description="Save a skill for faster coin flipping")
@app_commands.describe(
    skill_name="Name of the skill",
    base_power="Base power of the skill",
    coin_power="Coin power per head",
    coins="Total number of coins",
    unbreakable="How many unbreakable coins"
)
async def save_skill_cmd(interaction: discord.Interaction,
                         skill_name: str,
                         base_power: int,
                         coin_power: int,
                         coins: int,
                         unbreakable: int):
    user_id = str(interaction.user.id)
    skill_id = save_skill(user_id, skill_name, base_power, coin_power, coins, unbreakable)
    await interaction.response.send_message(
        f"Skill **{skill_name}** saved! (ID: {skill_id})", ephemeral=True
    )

# Delete Skill /Command
@bot.tree.command(name="delete_skill", description="Delete a saved skill by ID or name")
@app_commands.describe(
    skill_name="Name of the saved skill (optional if using ID)",
    skill_id="ID of the saved skill (optional if using name)"
)
async def delete_skill_cmd(interaction: discord.Interaction, skill_name: str = None, skill_id: int = None):
    user_id = str(interaction.user.id)

    if skill_name is None and skill_id is None:
        await interaction.response.send_message(
            "You must provide either a skill name or skill ID to delete.",
            ephemeral=True
        )
        return

    deleted_name = delete_skill(user_id, skill_name=skill_name, skill_id=skill_id)

    if deleted_name is None:
        await interaction.response.send_message(
            "Skill not found. Check the name/ID and try again.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"Skill **{deleted_name}** has been deleted.",
            ephemeral=True
        )

# Flip Saved Skill /Command
@bot.tree.command(name="flip_skill", description="Flip a saved skill")
@app_commands.describe(
    skill_name="Name of the saved skill (optional if using ID)",
    skill_id="ID of the saved skill (optional if using name)",
    sanity="Sanity (-45 to 45)"
)
async def flip_cmd(interaction: discord.Interaction, sanity: int, skill_name: str = None, skill_id: int = None):
    user_id = str(interaction.user.id)
    sanity = max(-45, min(45, sanity))  # clamp sanity

    # Load skill by ID or by name
    skill = load_skill(user_id, skill_name, skill_id)

    if skill is None:
        await interaction.response.send_message(
            "Skill not found. You can save a skill using save_skill. Check the name or ID and try again",
            ephemeral=True
        )
        return

    # Unpack skill
    skill_name, base_power, coin_power, coins, unbreakable = skill
    total_power = base_power
    normal_coins = coins - unbreakable
    head_chance = 50 + sanity
    trail = ""

    # Normal coins
    for _ in range(normal_coins):
        roll = random.randint(1, 100)
        if roll <= head_chance:
            total_power += coin_power
            trail += f"{TAIL} "
        else:
            trail += f"{HEAD} "

    # Unbreakable coins
    for _ in range(unbreakable):
        roll = random.randint(1, 100)
        if roll <= head_chance:
            total_power += coin_power
            trail += f"{UNBREAKABLE_HEAD} "
        else:
            trail += f"{UNBREAKABLE_TAIL} "

    await interaction.response.send_message(
        f"**{skill_name}** \n{trail}\n**Final Power:** {total_power}"
    )

# Skill List / Command

@bot.tree.command(name="skill_list", description="View your list of saved skills")
async def skill_list_cmd(interaction: discord.Interaction):
    user_id = str(interaction.user.id)

    result = (
        supabase.table("skills")
        .select("user_skill_id, skill_name, base_power, coin_power, coins, unbreakable")
        .eq("user_id", user_id)
        .order("user_skill_id")
        .execute()
    )

    if not result.data:
        await interaction.response.send_message(
            "You have no saved skills.",
            ephemeral=True
        )
        return

    lines = []

    for s in result.data:
        normal_coins = max(0, s["coins"] - s["unbreakable"])

        coin_display = (
            f"{TAIL} " * normal_coins +
            f"{UNBREAKABLE_HEAD} " * s["unbreakable"]
        )

        lines.append(
            f"**ID `{s['user_skill_id']}`**\n"
            f"{s['skill_name']}\n"
            f"{s['base_power']} Base Power | {s['coin_power']} Coin Power\n"
            f"{coin_display}"
        )

    message = "**__Skill List__**\n\n" + "\n\n".join(lines)

    # ---- SAFE CHUNKING (prevents "interaction failed") ----
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]

    await interaction.response.send_message(chunks[0], ephemeral=True)

    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=True)

# Skill Info / Command

@bot.tree.command(name="skill_info", description="View the information about a saved skill")
@app_commands.describe(
    skill_name="Skill name (optional if using ID)",
    skill_id="Skill ID (optional if using name)"
)
async def skill_info_cmd(
    interaction: discord.Interaction,
    skill_name: str = None,
    skill_id: int = None
):

    user_id = str(interaction.user.id)

    if skill_name is None and skill_id is None:
        await interaction.response.send_message(
            "Write the skill name or skill ID.",
            ephemeral=True
        )
        return

    # Query database (same pattern as your load_skill function but inline for consistency)
    query = (
        supabase.table("skills")
        .select("user_skill_id, skill_name, base_power, coin_power, coins, unbreakable")
        .eq("user_id", user_id)
    )

    if skill_id is not None:
        query = query.eq("user_skill_id", skill_id)
    else:
        query = query.eq("skill_name", skill_name)

    res = query.limit(1).execute()

    if not res.data:
        await interaction.response.send_message(
            "Skill not found.",
            ephemeral=True
        )
        return

    s = res.data[0]

    normal_coins = max(0, s["coins"] - s["unbreakable"])

    coin_display = (
        f"{TAIL} " * normal_coins +
        f"{UNBREAKABLE_HEAD} " * s["unbreakable"]
    )

    await interaction.response.send_message(
        f"**{s['skill_name']}**\n\n"
        f"ID `{s['user_skill_id']}`\n"
        f"{s['base_power']} Base Power\n"
        f"{s['coin_power']} Coin Power\n\n"
        f"Coins:\n{coin_display}",
        ephemeral=True
    )

# ----------------------
# Limbus Skill Functions
# ----------------------

def save_skill(user_id, skill_name, base_power, coin_power, coins, unbreakable):
    res = (
        supabase
        .table("skills")
        .select("user_skill_id")
        .eq("user_id", user_id)
        .order("user_skill_id", desc=True)
        .limit(1)
        .execute()
    )

    user_skill_id = (res.data[0]["user_skill_id"] if res.data else 0) + 1

    supabase.table("skills").upsert({
        "user_id": user_id,
        "user_skill_id": user_skill_id,
        "skill_name": skill_name,
        "base_power": base_power,
        "coin_power": coin_power,
        "coins": coins,
        "unbreakable": unbreakable
    }).execute()

    return user_skill_id

# Limbus Load Skill
def load_skill(user_id, skill_name=None, skill_id=None):
    query = supabase.table("skills").select(
        "skill_name, base_power, coin_power, coins, unbreakable"
    ).eq("user_id", user_id)

    if skill_id is not None:
        query = query.eq("user_skill_id", skill_id)
    elif skill_name is not None:
        query = query.eq("skill_name", skill_name)
    else:
        return None

    res = query.limit(1).execute()

    if not res.data:
        return None

    row = res.data[0]
    return (
        row["skill_name"],
        row["base_power"],
        row["coin_power"],
        row["coins"],
        row["unbreakable"]
    )

# Limbus Delete Skill
def delete_skill(user_id, skill_name=None, skill_id=None):
    query = supabase.table("skills").select("skill_name").eq("user_id", user_id)

    if skill_id is not None:
        query = query.eq("user_skill_id", skill_id)
    elif skill_name is not None:
        query = query.eq("skill_name", skill_name)
    else:
        return None

    res = query.limit(1).execute()
    if not res.data:
        return None

    skill_name = res.data[0]["skill_name"]

    delete_query = supabase.table("skills").delete().eq("user_id", user_id)
    if skill_id is not None:
        delete_query = delete_query.eq("user_skill_id", skill_id)
    else:
        delete_query = delete_query.eq("skill_name", skill_name)

    delete_query.execute()
    return skill_name


# Limbus Clash / Command
@bot.tree.command(name="clash", description="Clash your skill against another player's skill")
@app_commands.describe(
    skill_name="Your saved skill name (optional if using ID)",
    skill_id="ID of your saved skill (optional if using name)",
    sanity="Your sanity (-45 to 45)"
)
async def clash_cmd(interaction: discord.Interaction, sanity: int, skill_name: str = None, skill_id: int = None):

    original_user = interaction.user
    user1_id = str(original_user.id)
    sanity = max(-45, min(45, sanity))

    await interaction.response.defer()

    # Load original user's skill
    skill1 = load_skill(user1_id, skill_name, skill_id)

    if not skill1:
        await interaction.followup.send(
            "Your skill was not found. Save it first with /save_skill or check your input.",
            ephemeral=True
        )
        return

    skill1_name, base_power1, coin_power1, coins1, unbreakable1 = skill1


    # ----------------------
    # Challenge View
    # ----------------------
    class ChallengeView(View):
        def __init__(self, original_user: discord.User):
            super().__init__(timeout=30)
            self.original_user = original_user
            self.challenger_data = None

        @discord.ui.button(label="Join Clash", style=discord.ButtonStyle.primary)
        async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

            if interaction.user.id == self.original_user.id:
                await interaction.response.send_message(
                    "You can't challenge yourself!", ephemeral=True
                )
                return

            parent_view = self

            class ChallengeModal(discord.ui.Modal, title="Join Clash"):

                sanity_input = discord.ui.TextInput(
                    label="Sanity (-45 to 45)",
                    placeholder="Enter your sanity first",
                    required=True,
                    max_length=5
                )

                skill_input = discord.ui.TextInput(
                    label="Skill name or ID",
                    placeholder="Enter your skill name or ID",
                    required=True,
                    max_length=50
                )

                async def on_submit(self_modal, modal_interaction: discord.Interaction):
                    try:
                        sanity_val = max(-45, min(45, int(self_modal.sanity_input.value)))
                        skill_val = self_modal.skill_input.value.strip()
                        challenger_id = str(modal_interaction.user.id)

                        if skill_val.isdigit():
                            challenger_skill = load_skill(challenger_id, skill_id=int(skill_val))
                        else:
                            challenger_skill = load_skill(challenger_id, skill_name=skill_val)

                        if not challenger_skill:
                            await modal_interaction.response.send_message(
                                f"Skill **{skill_val}** not found. Challenge cancelled.",
                                ephemeral=True
                            )
                            parent_view.stop()
                            return

                        skill_name, base_power, coin_power, coins, unbreakable = challenger_skill

                        parent_view.challenger_data = (
                            modal_interaction.user, skill_name, sanity_val,
                            base_power, coin_power, coins, unbreakable
                        )

                        await modal_interaction.response.send_message(
                            f"You joined the clash using **{skill_name}**!", ephemeral=True
                        )

                        parent_view.stop()

                    except Exception:
                        await modal_interaction.response.send_message(
                            "Invalid input! Challenge cancelled.", ephemeral=True
                        )
                        parent_view.stop()

            await interaction.response.send_modal(ChallengeModal())


    view = ChallengeView(original_user)

    await interaction.followup.send(
        f"⚔️ COMBAT START - CLASH\n{original_user.mention} uses **{skill1_name}**!\nWaiting for an opponent...",
        view=view
    )

    await view.wait()

    if not view.challenger_data:
        await interaction.edit_original_response(
            content="No one challenged in time. Clash cancelled.",
            view=None
        )
        return


    # ----------------------
    # BOTH PLAYERS READY
    # ----------------------
    user2, skill2_name, sanity2, base_power2, coin_power2, coins2, unbreakable2 = view.challenger_data

    coins_list1 = ['N'] * (coins1 - unbreakable1) + ['U'] * unbreakable1
    coins_list2 = ['N'] * (coins2 - unbreakable2) + ['U'] * unbreakable2

    removed_unbreakables1 = 0
    removed_unbreakables2 = 0

    step_count = 1


    # ----------------------
    # FIXED OUTSIDE LOOP
    # ----------------------
    def flip_all(coins_list, base_power, coin_power, sanity_val):
        total = base_power
        trail = ""
        for c in coins_list:
            roll = random.randint(1, 100)
            if roll <= 50 + sanity_val:
                total += coin_power
                trail += TAIL + " " if c == 'N' else UNBREAKABLE_HEAD + " "
            else:
                trail += HEAD + " " if c == 'N' else UNBREAKABLE_TAIL + " "
        return total, trail


    while coins_list1 and coins_list2:

        total1, trail1 = flip_all(coins_list1, base_power1, coin_power1, sanity)
        total2, trail2 = flip_all(coins_list2, base_power2, coin_power2, sanity2)

        if total1 > total2:
            loser_list = coins_list2
            loser_user = user2
        elif total2 > total1:
            loser_list = coins_list1
            loser_user = original_user
        else:
            loser_list = None
            loser_user = None

        if loser_list:
            removed = loser_list.pop(0)
            if removed == 'U':
                if loser_list is coins_list1:
                    removed_unbreakables1 += 1
                else:
                    removed_unbreakables2 += 1

        await interaction.followup.send(
            f"**Clash Step {step_count}:**\n"
            f"{original_user.display_name}: {trail1} ({total1})\n"
            f"{user2.display_name}: {trail2} ({total2})\n"
            + (f"Loser of this step: {loser_user.display_name}" if loser_user else "It's a tie!")
        )

        step_count += 1


    # ----------------------
    # POST CLASH
    # ----------------------

    if coins_list1:
        winner, winner_list, winner_base, winner_coin, winner_sanity, winner_removed = \
            original_user, coins_list1, base_power1, coin_power1, sanity, removed_unbreakables1
        loser, loser_list, loser_base, loser_coin, loser_sanity, loser_removed = \
            user2, coins_list2, base_power2, coin_power2, sanity2, removed_unbreakables2
    else:
        winner, winner_list, winner_base, winner_coin, winner_sanity, winner_removed = \
            user2, coins_list2, base_power2, coin_power2, sanity2, removed_unbreakables2
        loser, loser_list, loser_base, loser_coin, loser_sanity, loser_removed = \
            original_user, coins_list1, base_power1, coin_power1, sanity, removed_unbreakables1


    total_winner, trail_winner = flip_all(
        winner_list + ['U'] * winner_removed,
        winner_base,
        winner_coin,
        winner_sanity
    )

    await interaction.followup.send(
        f"🏆 **{winner.display_name}** flips all remaining coins:\n{trail_winner}\nTotal Power: {total_winner}"
    )

    loser_unbreakables = unbreakable1 if loser == original_user else unbreakable2

    if loser_unbreakables > 0:
        total_loser = loser_base
        trail_loser = ""
        head_chance = 50 + loser_sanity

        for _ in range(loser_unbreakables):
            roll = random.randint(1, 100)

            if roll <= head_chance:
                total_loser += 1
                trail_loser += UNBREAKABLE_HEAD + " "
            else:
                trail_loser += UNBREAKABLE_TAIL + " "

        await interaction.followup.send(
            f"💀 **{loser.display_name}** flips their unbreakable coins:\n{trail_loser}\nTotal Power: {total_loser}"
        )

# ----------------------
# TTRPG Slash Commands
# ----------------------

# TTRPG Save Skill / Command
@bot.tree.command(name="save_skill_ttrpg", description="Save a TTRPG skill for faster rolling")
async def save_skill_ttrpg_cmd(interaction: discord.Interaction):

    class SaveSkillModal(Modal, title="Save Your TTRPG Skill"):
        skill_name = TextInput(label="Skill Name", placeholder="Enter the skill name", required=True, max_length=50)
        base_power = TextInput(label="Base Power", placeholder="Enter base power (integer)", required=True, max_length=5)
        dice_power = TextInput(label="Dice Power", placeholder="Max dice roll (e.g., 1d8 → 8)", required=True, max_length=5)

        async def on_submit(self_modal, modal_interaction: discord.Interaction):
            try:
                skill_name_val = self_modal.skill_name.value.strip()
                base_val = int(self_modal.base_power.value)
                dice_val = int(self_modal.dice_power.value)

                # -------------------------
                # Slot Selection
                # -------------------------
                class SlotSelectView(View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.slot = None

                    @discord.ui.select(
                        placeholder="Choose Skill Slot",
                        options=[
                            discord.SelectOption(label="Slot 1", value="1"),
                            discord.SelectOption(label="Slot 2", value="2"),
                            discord.SelectOption(label="Slot 3", value="3"),
                            discord.SelectOption(label="Guard", value="guard"),
                            discord.SelectOption(label="Evade", value="evade"),
                            discord.SelectOption(label="Counter", value="counter"),
                        ]
                    )
                    async def slot_select(self, interaction_slot: discord.Interaction, select: discord.ui.Select):
                        self.slot = select.values[0]
                        await interaction_slot.response.defer()
                        self.stop()

                slot_view = SlotSelectView()
                await modal_interaction.response.send_message(
                    "Select Skill Slot:",
                    view=slot_view,
                    ephemeral=True
                )
                await slot_view.wait()

                if not slot_view.slot:
                    await modal_interaction.followup.send(
                        "Skill creation cancelled (no slot selected).",
                        ephemeral=True
                    )
                    return

                slot_val = slot_view.slot

                attack_val = None
                sin_val = None

                class AttackSinView(View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.attack = None
                        self.sin = None
                        self.result = None

                        # Sin selector (always present)
                        sin_select = discord.ui.Select(
                            placeholder="Choose Sin Affinity",
                            options=[discord.SelectOption(label=s.capitalize(), value=s) for s in SIN_AFFINITIES]
                        )

                        async def sin_callback(interaction: discord.Interaction):
                            self.sin = sin_select.values[0].lower()
                            await interaction.response.defer()

                            if slot_val in ["guard", "evade"]:
                                self.result = (None, self.sin)
                                self.stop()
                            elif self.attack is not None:
                                self.result = (self.attack, self.sin)
                                self.stop()

                        sin_select.callback = sin_callback
                        self.add_item(sin_select)

                        # Attack selector ONLY for non-defensive slots
                        if slot_val not in ["guard", "evade"]:
                            attack_select = discord.ui.Select(
                                placeholder="Choose Attack Type",
                                options=[discord.SelectOption(label=a.capitalize(), value=a) for a in ATTACK_TYPES]
                            )

                            async def attack_callback(interaction: discord.Interaction):
                                self.attack = attack_select.values[0].lower()
                                await interaction.response.defer()

                                if self.sin is not None:
                                    self.result = (self.attack, self.sin)
                                    self.stop()

                            attack_select.callback = attack_callback
                            self.add_item(attack_select)


                view = AttackSinView()

                await modal_interaction.followup.send(
                    "Select Sin Affinity" if slot_val in ["guard", "evade"] else "Select Attack Type and Sin Affinity:",
                    view=view,
                    ephemeral=True
                )

                await view.wait()

                if not view.result:
                    await modal_interaction.followup.send(
                        "Skill creation cancelled (no sin/attack selected).",
                        ephemeral=True
                    )
                    return

                attack_val, sin_val = view.result

                # -------------------------
                # Save skill in database
                # -------------------------
                user_id = str(modal_interaction.user.id)
                skill_id = await save_skill_ttrpg(
                    user_id, slot_val, skill_name_val, base_val, dice_val, attack_val, sin_val
                )

                await modal_interaction.followup.send(
                    f"TTRPG Skill **{skill_name_val}** saved in slot {slot_val}!\n"
                    f"{'Attack: ' + attack_val.capitalize() + ' | Sin Affinity: ' + sin_val.capitalize() if attack_val else 'Defensive Skill'} | ID: {skill_id}",
                    ephemeral=True
                )

            except Exception as e:
                await modal_interaction.followup.send(
                    f"Error: {str(e)}",
                    ephemeral=True
                )

    await interaction.response.send_modal(SaveSkillModal())

# TTRPG Delete Skill / Command
@bot.tree.command(name="delete_skill_ttrpg", description="Delete a saved TTRPG skill by name or ID")
@app_commands.describe(
    skill_name="Skill name (optional if using ID)",
    skill_id="Skill ID (optional if using name)"
)
async def delete_ttrpg_cmd(
    interaction: discord.Interaction,
    skill_name: str = None,
    skill_id: int = None
):
    user_id = str(interaction.user.id)

    if not skill_name and not skill_id:
        await interaction.response.send_message("Write skill name or ID!", ephemeral=True)
        return

    # Load skill to get the actual name
    skill_data = await load_skill_ttrpg(user_id, skill_name, skill_id)
    if not skill_data:
        await interaction.response.send_message("Skill not found!", ephemeral=True)
        return

    actual_name = skill_data[1] if isinstance(skill_data, (list, tuple)) else skill_data["skill_name"]

    # Confirmation view
    class ConfirmDeleteView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.confirmed = False

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
        async def yes(self, inter: discord.Interaction, button: discord.ui.Button):
            self.confirmed = True
            await inter.response.defer()
            self.stop()

        @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
        async def no(self, inter: discord.Interaction, button: discord.ui.Button):
            self.confirmed = False
            await inter.response.defer()
            self.stop()

    view = ConfirmDeleteView()
    await interaction.response.send_message(
        f"Are you sure you want to delete **{actual_name}**?",
        view=view,
        ephemeral=True
    )

    await view.wait()

    if not view.confirmed:
        await interaction.followup.send("Deletion cancelled.", ephemeral=True)
        return

    deleted = await delete_skill_ttrpg(user_id, skill_name, skill_id)
    if deleted:
        await interaction.followup.send(f"TTRPG Skill **{actual_name}** deleted.", ephemeral=True)
    else:
        await interaction.followup.send("Skill not found!", ephemeral=True)


# TTRPG Skill List / Command
@bot.tree.command(name="skill_list_ttrpg", description="View your list of TTRPG skills")
async def skill_list_ttrpg_cmd(interaction: discord.Interaction):

    user_id = str(interaction.user.id)

    result = (
        supabase.table("ttrpg_skills")
        .select("user_skill_id, skill_slot, skill_name, base_power, dice_power, attack_type, sin_affinity")
        .eq("user_id", user_id)
        .order("skill_slot")
        .execute()
    )

    if not result.data:
        await interaction.response.send_message(
            "You have no saved TTRPG skills.",
            ephemeral=True
        )
        return

    lines = []

    for s in result.data:

        dice = f"+ 1d{s['dice_power']}" if s["dice_power"] >= 0 else f"- 1d{abs(s['dice_power'])}"

        role = resolve_skill_role(str(s["skill_slot"]).lower())

        role_emoji, sin_emoji = get_skill_emojis(
            attack_type=s["attack_type"],
            sin_affinity=s["sin_affinity"],
            role=role
        )

        # Title case formatting
        slot_text = str(s["skill_slot"]).capitalize()

        lines.append(
            f"**Slot {slot_text}** | ID `{s['user_skill_id']}`\n"
            f"{s['skill_name']} {role_emoji}{sin_emoji} → "
            f"{s['base_power']} {dice}"
        )

    await interaction.response.send_message(
        "**__TTRPG Skill List__**\n\n" + "\n\n".join(lines),
        ephemeral=True
    )

# TTRPG Edit Skill / Command
@bot.tree.command(name="skill_edit_ttrpg", description="Edit an existing TTRPG skill")
@app_commands.describe(
    skill_name="Skill name (optional if using ID)",
    skill_id="Skill ID (optional if using name)"
)
async def skill_edit_ttrpg_cmd(
    interaction: discord.Interaction,
    skill_name: str = None,
    skill_id: int = None
):

    user_id = str(interaction.user.id)

    skill = await load_skill_ttrpg(user_id, skill_name, skill_id)

    if not skill:
        await interaction.response.send_message(
            "Skill not found.",
            ephemeral=True
        )
        return

    slot, name, base, dice, attack, sin = skill

    class EditSkillModal(Modal, title="Edit TTRPG Skill"):

        skill_name_input = TextInput(
            label="Skill Name",
            default=name,
            required=True,
            max_length=50
        )

        slot_input = TextInput(
            label="Skill Slot (1,2,3,guard,evade,counter)",
            default=str(slot),
            required=True,
            max_length=10
        )

        base_input = TextInput(
            label="Base Power",
            default=str(base),
            required=True,
            max_length=6
        )

        dice_input = TextInput(
            label="Dice Power",
            default=str(dice),
            required=True,
            max_length=6
        )

        async def on_submit(self_modal, modal_interaction: discord.Interaction):

            await modal_interaction.response.defer(ephemeral=True)

            try:
                new_name = self_modal.skill_name_input.value.strip()
                new_slot = self_modal.slot_input.value.strip().lower()
                new_base = int(self_modal.base_input.value)
                new_dice = int(self_modal.dice_input.value)

                # Defensive slots → no attack type
                if new_slot in ["guard", "evade"]:
                    attack_val = None
                else:
                    attack_val = attack

                sin_val = sin

                # Ask Attack Type Change 
                if new_slot not in ["guard", "evade"]:

                    class ConfirmView(View):
                        def __init__(self):
                            super().__init__(timeout=60)
                            self.choice = None

                        @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
                        async def yes(self, inter: discord.Interaction, button: discord.ui.Button):
                            self.choice = True
                            await inter.response.defer()
                            self.stop()

                        @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
                        async def no(self, inter: discord.Interaction, button: discord.ui.Button):
                            self.choice = False
                            await inter.response.defer()
                            self.stop()

                    view = ConfirmView()

                    await modal_interaction.followup.send(
                        f"Change Attack Type? Current: {attack}",
                        view=view,
                        ephemeral=True
                    )

                    await view.wait()

                    if view.choice:

                        class AttackSelectView(View):
                            def __init__(self):
                                super().__init__(timeout=60)
                                self.result = None

                            @discord.ui.select(
                                placeholder="Choose Attack Type",
                                options=[discord.SelectOption(label=a.capitalize(), value=a) for a in ATTACK_TYPES]
                            )
                            async def select_attack(self_inter, inter: discord.Interaction, select: discord.ui.Select):
                                self_inter.result = select.values[0].lower()
                                await inter.response.defer()
                                self_inter.stop()

                        attack_view = AttackSelectView()

                        await modal_interaction.followup.send(
                            "Select new Attack Type:",
                            view=attack_view,
                            ephemeral=True
                        )

                        await attack_view.wait()

                        if attack_view.result:
                            attack_val = attack_view.result

                # Ask Sin Affinity Change
                view = ConfirmView()

                await modal_interaction.followup.send(
                    f"Change Sin Affinity? Current: {sin}",
                    view=view,
                    ephemeral=True
                )

                await view.wait()

                if view.choice:

                    class SinSelectView(View):
                        def __init__(self):
                            super().__init__(timeout=60)
                            self.result = None

                        @discord.ui.select(
                            placeholder="Choose Sin Affinity",
                            options=[discord.SelectOption(label=s.capitalize(), value=s) for s in SIN_AFFINITIES]
                        )
                        async def select_sin(self_inter, inter: discord.Interaction, select: discord.ui.Select):
                            self_inter.result = select.values[0].lower()
                            await inter.response.defer()
                            self_inter.stop()

                    sin_view = SinSelectView()

                    await modal_interaction.followup.send(
                        "Select new Sin Affinity:",
                        view=sin_view,
                        ephemeral=True
                    )

                    await sin_view.wait()

                    if sin_view.result:
                        sin_val = sin_view.result

                # Update Database
                supabase.table("ttrpg_skills").update({
                    "skill_slot": new_slot,
                    "skill_name": new_name,
                    "base_power": new_base,
                    "dice_power": new_dice,
                    "attack_type": attack_val,
                    "sin_affinity": sin_val
                }).eq("user_id", user_id).eq(
                    "user_skill_id",
                    skill_id if skill_id else skill[0]
                ).execute()

                await modal_interaction.followup.send(
                    "Skill edited successfully!",
                    ephemeral=True
                )

            except Exception as e:
                await modal_interaction.followup.send(
                    f"Error: {str(e)}",
                    ephemeral=True
                )

    await interaction.response.send_modal(EditSkillModal())

# TTRPG Skill Info / Command
@bot.tree.command(name="skill_info_ttrpg", description="View the details of a TTRPG skill")
@app_commands.describe(
    skill_name="Skill name (optional if using ID)",
    skill_id="Skill ID (optional if using name)"
)
async def skill_info_ttrpg_cmd(
    interaction: discord.Interaction,
    skill_name: str = None,
    skill_id: int = None
):

    user_id = str(interaction.user.id)
    skill = await load_skill_ttrpg(user_id, skill_name, skill_id)

    if not skill:
        await interaction.response.send_message(
            "Skill not found.",
            ephemeral=True
        )
        return

    skill_slot, name, base, dice, attack_type, sin_affinity = skill

    dice_txt = f"1d{dice}" if dice >= 0 else f"-1d{abs(dice)}"

    role = resolve_skill_role(str(skill_slot).lower())

    role_emoji, sin_emoji = get_skill_emojis(
        attack_type=attack_type,
        sin_affinity=sin_affinity,
        role=role
    )

    await interaction.response.send_message(
        f"**__Skill Info__**\n\n"
        f"**{name}** {role_emoji}{sin_emoji}\n"
        f"Slot: `{str(skill_slot).capitalize()}`\n"
        f"Base Power: `{base}`\n"
        f"Dice: `{dice_txt}`\n"
        f"Attack Type: `{attack_type.capitalize() if attack_type else 'None'}`\n"
        f"Sin Affinity: `{sin_affinity.capitalize() if sin_affinity else 'None'}`",
        ephemeral=True
    )

# TTRPG Roll Skill / Command
@bot.tree.command(name="roll_skill_ttrpg", description="Roll a saved TTRPG skill")
@app_commands.describe(
    skill_name="Skill name (optional if using ID)",
    skill_id="Skill ID (optional if using name)",
    sanity="Sanity (-45 to 45)"
)
async def roll_ttrpg_cmd(
    interaction: discord.Interaction,
    sanity: int,
    skill_name: str = None,
    skill_id: int = None,
):

    sanity = max(MIN_SANITY, min(MAX_SANITY, sanity))

    user_id = str(interaction.user.id)

    skill = await load_skill_ttrpg(user_id, skill_name, skill_id)

    if not skill:
        await interaction.response.send_message("Skill not found!", ephemeral=True)
        return

    total, roll, mod_base, mod_dice, attack_type, sin_affinity, _ = await roll_skill_ttrpg(skill, sanity)

    skill_slot = skill[0]
    skill_name_val = skill[1]
    dice_power = skill[3]

    dice_text = f"- 1d{mod_dice}" if dice_power < 0 else f"+ 1d{mod_dice}"

    role = resolve_skill_role(str(skill_slot).lower())

    role_emoji, sin_emoji = get_skill_emojis(
        attack_type=attack_type,
        sin_affinity=sin_affinity,
        role=role
    )

    await interaction.response.send_message(
        f"**{skill_name_val}** {role_emoji}{sin_emoji}\n"
        f"{mod_base} {dice_text} ({roll}) → **Total: {total}**"
    )

@bot.tree.command(name="clash_ttrpg", description="Clash your TTRPG skill against another player's TTRPG skill")
@app_commands.describe(
    skill_name="Your skill name (optional if using ID)",
    skill_id="Your skill ID (optional if using name)",
    sanity="Your sanity (-45 to 45)"
)

# TTRPG Clash Skill / Command
async def clash_ttrpg_cmd(interaction: discord.Interaction, sanity: int, skill_name: str = None, skill_id: int = None):

    original_user = interaction.user
    user1_id = str(original_user.id)

    sanity = max(MIN_SANITY, min(MAX_SANITY, sanity))

    # Load original skill
    skill1 = await load_skill_ttrpg(user1_id, skill_name, skill_id)

    if not skill1:
        await interaction.response.send_message(
            "Your TTRPG skill was not found. Save it first with /save_skill_ttrpg or check your input.",
            ephemeral=True
        )
        return

    skill1_slot, skill1_name, base1, dice_power1, attack1, sin1 = skill1

    role1 = resolve_skill_role(skill1_slot)

    attack_emoji1, sin_emoji1 = get_skill_emojis(
        attack_type=attack1,
        sin_affinity=sin1,
        role=role1
    )

    # -------------------------
    # Challenge View
    # -------------------------
    class ChallengeView(View):
        def __init__(self, original_user: discord.User):
            super().__init__(timeout=30)
            self.original_user = original_user
            self.challenger_data = None

        @discord.ui.button(label="Join Clash", style=discord.ButtonStyle.primary)
        async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

            if interaction.user.id == self.original_user.id:
                await interaction.response.send_message(
                    "You can't challenge yourself!",
                    ephemeral=True
                )
                return

            parent_view = self

            class ChallengeModal(Modal, title="Join TTRPG Clash"):

                sanity_input = TextInput(
                    label="Sanity (-45 to 45)",
                    required=True,
                    max_length=5
                )

                skill_input = TextInput(
                    label="Skill name or ID",
                    required=True,
                    max_length=50
                )

                async def on_submit(self_modal, modal_interaction: discord.Interaction):
                    try:
                        sanity_val = max(
                            MIN_SANITY,
                            min(MAX_SANITY, int(self_modal.sanity_input.value))
                        )

                        skill_val = self_modal.skill_input.value.strip()
                        challenger_id = str(modal_interaction.user.id)

                        if skill_val.isdigit():
                            challenger_skill = await load_skill_ttrpg(
                                challenger_id,
                                skill_id=int(skill_val)
                            )
                        else:
                            challenger_skill = await load_skill_ttrpg(
                                challenger_id,
                                skill_name=skill_val
                            )

                        if not challenger_skill:
                            await modal_interaction.response.send_message(
                                "Skill not found! Challenge cancelled.",
                                ephemeral=True
                            )
                            parent_view.stop()
                            return

                        slot2, skill_name2, base2, dice2, attack2, sin2 = challenger_skill

                        parent_view.challenger_data = (
                            modal_interaction.user,
                            skill_name2,
                            sanity_val,
                            base2,
                            dice2,
                            attack2,
                            sin2,
                            slot2
                        )

                        role2 = resolve_skill_role(slot2)

                        attack_emoji2, sin_emoji2 = get_skill_emojis(
                            attack_type=attack2,
                            sin_affinity=sin2,
                            role=role2
                        )

                        await modal_interaction.response.send_message(
                            f"You joined the clash using **{skill_name2}** {attack_emoji2}{sin_emoji2}!",
                            ephemeral=True
                        )

                        parent_view.stop()

                    except Exception:
                        await modal_interaction.response.send_message(
                            "Invalid input! Challenge cancelled.",
                            ephemeral=True
                        )
                        parent_view.stop()

            await interaction.response.send_modal(ChallengeModal())

    view = ChallengeView(original_user)

    await interaction.response.send_message(
        f"⚔️ CLASH START - {original_user.mention} uses **{skill1_name}** {attack_emoji1}{sin_emoji1}!\nWaiting for a challenger...",
        view=view
    )

    await view.wait()

    if not view.challenger_data:
        await interaction.edit_original_response(
            content="No one challenged in time. Clash cancelled.",
            view=None
        )
        return

    # -------------------------
    # Both Players Ready
    # -------------------------
    user2, skill2_name, sanity2, base2, dice_power2, attack2, sin2, skill2_slot = view.challenger_data

    step_count = 1

    while True:
        # Roll skills (fix unpacking for 7 values)
        total1, roll1, mod_base1, mod_dice1, atk1_db, sin1_db, role1_db = await roll_skill_ttrpg(
            skill1,
            sanity
        )

        total2, roll2, mod_base2, mod_dice2, atk2_db, sin2_db, role2_db = await roll_skill_ttrpg(
            (None, skill2_name, base2, dice_power2, attack2, sin2),
            sanity2
        )

        role1 = resolve_skill_role(skill1_slot)
        role2 = resolve_skill_role(skill2_slot)

        attack_emoji1, sin_emoji1 = get_skill_emojis(
            attack_type=atk1_db,
            sin_affinity=sin1_db,
            role=role1
        )
        attack_emoji2, sin_emoji2 = get_skill_emojis(
            attack_type=atk2_db,
            sin_affinity=sin2_db,
            role=role2
        )

        dice_text1 = f"- 1d{mod_dice1}" if dice_power1 < 0 else f"+ 1d{mod_dice1}"
        dice_text2 = f"- 1d{mod_dice2}" if dice_power2 < 0 else f"+ 1d{mod_dice2}"

        clash_text = (
            f"⚔️ Clash Step {step_count}\n\n"
            f"{original_user.display_name}\n**{skill1_name}** {attack_emoji1}{sin_emoji1}\n"
            f"{mod_base1} {dice_text1} ({roll1}) → **Total: {total1}**\n\n"
            f"{user2.display_name}\n**{skill2_name}** {attack_emoji2}{sin_emoji2}\n"
            f"{mod_base2} {dice_text2} ({roll2}) → **Total: {total2}**"
        )

        if interaction.channel:
            await interaction.channel.send(clash_text)

        # -------------------------
        # Defensive Skill Resolution (FULL ORIGINAL)
        # -------------------------
        damage_to_user1 = total2
        damage_to_user2 = total1
        shield_user1 = 0
        shield_user2 = 0

        outcome_text = "Defensive Outcome:\n"
        defensive_triggered = False

        # Evade
        if role1 == "evade" and role2 == "attack":
            defensive_triggered = True
            if total1 > total2:
                damage_to_user1 = 0
                outcome_text += f"{original_user.display_name} successfully evaded!\n"
            else:
                outcome_text += f"{original_user.display_name} failed to evade and took {damage_to_user1} {attack_emoji2}{sin_emoji2} damage!\n"

        if role2 == "evade" and role1 == "attack":
            defensive_triggered = True
            if total2 > total1:
                damage_to_user2 = 0
                outcome_text += f"{user2.display_name} successfully evaded!\n"
            else:
                outcome_text += f"{user2.display_name} failed to evade and took {damage_to_user2} {attack_emoji1}{sin_emoji1} damage!\n"

        # Guard
        if role1 == "guard":
            defensive_triggered = True
            shield_user1 = total1
            damage_to_user1 = total2
            outcome_text += f"{original_user.display_name} gains {shield_user1} shield and takes {damage_to_user1} {attack_emoji2}{sin_emoji2} damage\n"

        if role2 == "guard":
            defensive_triggered = True
            shield_user2 = total2
            damage_to_user2 = total1
            outcome_text += f"{user2.display_name} gains {shield_user2} shield and takes {damage_to_user2} {attack_emoji1}{sin_emoji1} damage\n"

        # Counter
        if role1 == "counter":
            defensive_triggered = True
            counter_damage_user1 = total1
            damage_to_user1 = total2
            outcome_text += f"{original_user.display_name} takes {damage_to_user1} damage and counters for {counter_damage_user1} {attack_emoji1}{sin_emoji1} damage\n"

        if role2 == "counter":
            defensive_triggered = True
            counter_damage_user2 = total2
            damage_to_user2 = total1
            outcome_text += f"{user2.display_name} takes {damage_to_user2} damage and counters for {counter_damage_user2} {attack_emoji2}{sin_emoji2} damage\n"

        if defensive_triggered and interaction.channel:
            await interaction.channel.send(outcome_text)

        # -------------------------
        # Exit Conditions
        # -------------------------
        if role1 in ["guard", "evade", "counter"] or role2 in ["guard", "evade", "counter"]:
            break
        if role1 == "attack" and role2 == "attack" and total1 != total2:
            break
        if step_count > 50:
            break

        step_count += 1

    # -------------------------
    # Winner Resolution
    # -------------------------
    pure_attack_clash = (role1 == "attack" and role2 == "attack")

    if pure_attack_clash:
        winner = original_user if total1 > total2 else user2
        total_winner = max(total1, total2)
        attack_emoji, sin_emoji = get_skill_emojis(skill1[4], skill1[5])

        if interaction.channel:
            await interaction.channel.send(
                f"🏆 **{winner.display_name}**'s Damage Dealt: {total_winner} {attack_emoji}{sin_emoji}"
            )

# Run the bot
bot.run(TOKEN)