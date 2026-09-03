import os
import asyncio
import datetime
import random
import json
import discord
from discord.ext import commands

# ==========================================
# CREATOR METADATA & CONFIGURATION
# ==========================================
BOT_CREATOR_USERNAME = "Monarch SK"
BOT_CREATOR_REAL_NAME = "Subhan Ahmed"
BOT_COMPANY_NAME = "Tire Three"

DISBOARD_BOT_ID = 302050872383422240

# Dynamic Channel ID Storage
ANNOUNCEMENT_CHANNEL_ID = 0
BUMP_CHANNEL_ID = 0
BOT_COMMANDS_CHANNEL_ID = 0
BOT_MEMORY_CHANNEL_ID = 0 

# Leveling System Configuration
BASE_XP_LEVEL_1 = 500
MAX_LEVEL = 60

# Level Tier Mapping (1 to 60)
LEVEL_TIER_ROLES = {
    (1, 9): {"name": "Newbie", "color": discord.Color.teal()},
    (10, 19): {"name": "Explorer", "color": discord.Color.green()},
    (20, 29): {"name": "Veteran", "color": discord.Color.blue()},
    (30, 39): {"name": "Elite", "color": discord.Color.purple()},
    (40, 49): {"name": "Champion", "color": discord.Color.gold()},
    (50, 59): {"name": "Legend", "color": discord.Color.orange()},
    (60, 60): {"name": "Sovereign", "color": discord.Color.dark_red()}
}

# Protected Roles (Owner/Administrator Manual Modifications Only)
RESTRICTED_ADMIN_ROLES = ["authority", "head moderator", "moderator"]

# Pre-defined Hex Color Roles
PRO_HEX_COLORS = {
    "Pro Hex Red": discord.Color.from_rgb(255, 75, 75),
    "Pro Hex Green": discord.Color.from_rgb(75, 255, 125),
    "Pro Hex Blue": discord.Color.from_rgb(75, 150, 255),
    "Pro Hex Pink": discord.Color.from_rgb(255, 105, 180),
    "Pro Hex Yellow": discord.Color.from_rgb(255, 225, 75),
    "Pro Hex Orange": discord.Color.from_rgb(255, 140, 0)
}

CUTE_BUMP_MESSAGES = [
    "You're absolute perfection! Thanks for helping us grow! 💖✨",
    "Sending you virtual warm hugs and lots of appreciation! 🧸🌸",
    "You just brightened up the whole server's day! 🌟✨",
    "Thank you for being so amazing and keeping our cozy home alive! 🐾💌",
    "You're a superstar! Server sparkles everywhere for you! ✨💖"
]

# ==========================================
# BOT SETUP & INTENTS
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True

bot = commands.Bot(command_prefix=".", intents=intents)

# Primary In-Memory Data Structures
afk_users = {}
afk_mentions = {}
user_xp = {}
user_levels = {}
user_warnings = {}
user_mute_counts = {}

last_bump_time = 0
bump_cooldown_seconds = 7200  # 2 Hours

# ==========================================
# HELPER FUNCTIONS & CHECKS
# ==========================================
def is_admin_or_owner():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
        raise commands.CheckFailure("Only the Server Owner or an Administrator can perform this action.")
    return commands.check(predicate)

def is_admin_or_higher():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
        user_roles = [r.name.lower() for r in ctx.author.roles]
        if any(role_name in user_roles for role_name in RESTRICTED_ADMIN_ROLES):
            return True
        raise commands.CheckFailure("You do not have permission to run this command.")
    return commands.check(predicate)

def get_xp_for_level(level):
    if level >= MAX_LEVEL:
        return BASE_XP_LEVEL_1 * (2 ** (MAX_LEVEL - 2))
    return BASE_XP_LEVEL_1 * (2 ** (level - 1))

def get_tier_info_for_level(level):
    for (min_lvl, max_lvl), tier_data in LEVEL_TIER_ROLES.items():
        if min_lvl <= level <= max_lvl:
            return tier_data
    return LEVEL_TIER_ROLES[(1, 9)]

async def ensure_role_exists(guild, role_name, color):
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            role = await guild.create_role(name=role_name, color=color, reason="Auto System Setup")
        except discord.Forbidden:
            return None
    return role

async def update_member_level_role(member, new_level):
    guild = member.guild
    tier_info = get_tier_info_for_level(new_level)
    target_role_name = tier_info["name"]
    target_color = tier_info["color"]

    target_role = await ensure_role_exists(guild, target_role_name, target_color)
    if not target_role:
        return

    all_tier_names = [data["name"] for data in LEVEL_TIER_ROLES.values()]
    roles_to_remove = [r for r in member.roles if r.name in all_tier_names and r.name != target_role_name]

    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove)
        except discord.Forbidden:
            pass

    if target_role not in member.roles:
        try:
            await member.add_roles(target_role)
        except discord.Forbidden:
            pass

# ==========================================
# DYNAMIC CHANNEL MANAGEMENT
# ==========================================
async def get_or_create_announcement_channel(guild):
    global ANNOUNCEMENT_CHANNEL_ID
    if ANNOUNCEMENT_CHANNEL_ID and guild.get_channel(ANNOUNCEMENT_CHANNEL_ID):
        return guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)

    for channel in guild.text_channels:
        if channel.name.lower() in ["announcements", "level-announcements", "level-ups"]:
            ANNOUNCEMENT_CHANNEL_ID = channel.id
            return channel

    try:
        new_ch = await guild.create_text_channel("level-announcements")
        ANNOUNCEMENT_CHANNEL_ID = new_ch.id
        await new_ch.send("📢 **Leveling Announcements Channel Initialized!**")
        return new_ch
    except discord.Forbidden:
        return None

async def get_or_create_bot_commands_channel(guild):
    global BOT_COMMANDS_CHANNEL_ID
    if BOT_COMMANDS_CHANNEL_ID and guild.get_channel(BOT_COMMANDS_CHANNEL_ID):
        return guild.get_channel(BOT_COMMANDS_CHANNEL_ID)

    for channel in guild.text_channels:
        if channel.name.lower() in ["bot-commands", "bot_commands", "team-guide", "team_guide"]:
            BOT_COMMANDS_CHANNEL_ID = channel.id
            return channel

    try:
        new_ch = await guild.create_text_channel("bot-commands")
        BOT_COMMANDS_CHANNEL_ID = new_ch.id
        await new_ch.send("🤖 **Bot Commands Channel Initialized!**")
        return new_ch
    except discord.Forbidden:
        return None

async def get_or_create_bump_channel(guild):
    global BUMP_CHANNEL_ID
    if BUMP_CHANNEL_ID and guild.get_channel(BUMP_CHANNEL_ID):
        return guild.get_channel(BUMP_CHANNEL_ID)

    for channel in guild.text_channels:
        if channel.name.lower() == "bump":
            BUMP_CHANNEL_ID = channel.id
            return channel

    try:
        new_ch = await guild.create_text_channel("bump")
        BUMP_CHANNEL_ID = new_ch.id
        await new_ch.send("🚀 **Bump Channel Initialized!** Use `.bump` here.")
        return new_ch
    except discord.Forbidden:
        return None

async def get_or_create_memory_channel(guild):
    global BOT_MEMORY_CHANNEL_ID
    if BOT_MEMORY_CHANNEL_ID and guild.get_channel(BOT_MEMORY_CHANNEL_ID):
        return guild.get_channel(BOT_MEMORY_CHANNEL_ID)

    for channel in guild.text_channels:
        if channel.name.lower() == "bot-memory":
            BOT_MEMORY_CHANNEL_ID = channel.id
            return channel

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        new_ch = await guild.create_text_channel("bot-memory", overwrites=overwrites)
        BOT_MEMORY_CHANNEL_ID = new_ch.id
        await new_ch.send("💾 **Bot Memory Channel Created.** Dynamic database points will automatically record here.")
        return new_ch
    except discord.Forbidden:
        return None

# ==========================================
# DATABASE BACKUP & RECOVERY ENGINE
# ==========================================
async def save_data_to_channel(guild):
    memory_channel = await get_or_create_memory_channel(guild)
    if not memory_channel:
        return

    data = {
        "user_xp": {str(k): v for k, v in user_xp.items()},
        "user_levels": {str(k): v for k, v in user_levels.items()},
        "user_warnings": {str(k): v for k, v in user_warnings.items()},
        "user_mute_counts": {str(k): v for k, v in user_mute_counts.items()},
        "afk_users": {str(k): v for k, v in afk_users.items()}
    }

    json_payload = f"```json\n{json.dumps(data, indent=2)}\n```"
    await memory_channel.send(f"💾 **[AUTO-SAVE DATABASE SYNC]**\n{json_payload}")

async def restore_data_from_channel(guild):
    global user_xp, user_levels, user_warnings, user_mute_counts, afk_users
    memory_channel = await get_or_create_memory_channel(guild)
    if not memory_channel:
        return False

    async for message in memory_channel.history(limit=30):
        if message.author.id == bot.user.id and "```json" in message.content:
            try:
                raw_json = message.content.split("
