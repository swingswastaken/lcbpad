from bot import bot

import discord
from discord import app_commands

from services.skills import save_skill, delete_skill, load_skill, get_user_skills, get_skill_info
from utils.emojis import HEAD, UNBREAKABLE_HEAD
from utils.helpers import flip_skill

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
async def flip_cmd(
    interaction: discord.Interaction,
    sanity: int,
    skill_name: str = None,
    skill_id: int = None
):
    user_id = str(interaction.user.id)
    sanity = max(-45, min(45, sanity))

    # Load skill by ID or by name
    skill = load_skill(user_id, skill_name, skill_id)

    if skill is None:
        await interaction.response.send_message(
            "Skill not found. You can save a skill using /save_skill. Check the name or ID and try again.",
            ephemeral=True
        )
        return

    # Unpack skill
    skill_name, base_power, coin_power, coins, unbreakable = skill

    total_power, normal_coins, unbreakable, trail = flip_skill(
        user_id,
        skill_name,
        skill_id,
        sanity,
        (base_power, coin_power, coins, unbreakable)
    )

    await interaction.response.send_message(
        f"**{skill_name}**\n{trail}\n**Final Power:** {total_power}"
    )

@bot.tree.command(name="skill_list", description="View your list of saved skills")
async def skill_list_cmd(interaction: discord.Interaction):
    user_id = str(interaction.user.id)

    skills = get_user_skills(user_id)

    if not skills:
        await interaction.response.send_message(
            "You have no saved skills.",
            ephemeral=True
        )
        return

    lines = []

    for s in skills:
        normal_coins = max(0, s["coins"] - s["unbreakable"])

        coin_display = (
            f"{HEAD} " * normal_coins +
            f"{UNBREAKABLE_HEAD} " * s["unbreakable"]
        )

        lines.append(
            f"**ID `{s['user_skill_id']}`**\n"
            f"{s['skill_name']}\n"
            f"{s['base_power']} Base Power | {s['coin_power']} Coin Power\n"
            f"{coin_display}"
        )

    message = "**__Skill List__**\n\n" + "\n\n".join(lines)

    chunks = [message[i:i + 1900] for i in range(0, len(message), 1900)]

    await interaction.response.send_message(chunks[0], ephemeral=True)

    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=True)

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

    skill = get_skill_info(
        user_id,
        skill_name=skill_name,
        skill_id=skill_id
    )

    if skill is None:
        await interaction.response.send_message(
            "Skill not found.",
            ephemeral=True
        )
        return

    normal_coins = max(0, skill["coins"] - skill["unbreakable"])

    coin_display = (
        f"{HEAD} " * normal_coins +
        f"{UNBREAKABLE_HEAD} " * skill["unbreakable"]
    )

    await interaction.response.send_message(
        f"**{skill['skill_name']}**\n\n"
        f"ID `{skill['user_skill_id']}`\n"
        f"{skill['base_power']} Base Power\n"
        f"{skill['coin_power']} Coin Power\n\n"
        f"Coins:\n{coin_display}",
        ephemeral=True
    )