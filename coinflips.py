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

        await interaction.channel.send(
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

    await interaction.channel.send(
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

        await interaction.channel.send(
            f"💀 **{loser.display_name}** flips their unbreakable coins:\n{trail_loser}\nTotal Power: {total_loser}"
        )

# Run the bot
bot.run(TOKEN)