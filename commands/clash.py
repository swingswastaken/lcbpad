from bot import bot
import random

import discord
from discord import app_commands
from discord.ui import View

from services.skills import load_skill
from utils.emojis import HEAD, TAIL, UNBREAKABLE_HEAD, UNBREAKABLE_TAIL

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
                trail += HEAD + " " if c == 'N' else UNBREAKABLE_HEAD + " "
            else:
                trail += TAIL + " " if c == 'N' else UNBREAKABLE_TAIL + " "
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