from utils.emojis import EMOJIS_ROLE, EMOJIS_ATK_TYPE, EMOJIS_SIN, HEAD, TAIL, UNBREAKABLE_HEAD, UNBREAKABLE_TAIL, UNBREAKABLE_CRACKED_HEAD, UNBREAKABLE_CRACKED_TAIL
import random

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
        