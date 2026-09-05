import os
import sys
import io
import asyncio
import datetime
import random
import json
from collections import defaultdict
from typing import Optional

import discord
from discord.ext import commands, tasks

# ==========================================
# CREATOR METADATA & CONFIGURATION
# ==========================================
BOT_CREATOR_USERNAME = "Monarch SK"
BOT_CREATOR_REAL_NAME = "Subhan Ahmed"
BOT_COMPANY_NAME = "Tire Three"

DISBOARD_BOT_ID = 302050872383422240

# Channel ID Cache per Guild: {guild_id: channel_id}
announcement_channels = {}
bump_channels = {}
bot_commands_channels = {}
bot_memory_channels = {}
birthday_channels = {}
confession_channels = {}
colors_channels = {}
welcome_channels = {}
team_rules_channels = {}
team_news_channels = {}

# Leveling & Cooldown Configuration
MAX_LEVEL = 60
XP_COOLDOWN_SECONDS = 30
MIN_XP_PER_MSG = 20
MAX_XP_PER_MSG = 35
BUMP_COOLDOWN_SECONDS = 7200

# Tenure & Milestone Configuration
OG_ROLE_NAME = "OG"
OG_DAYS_REQUIRED = 365
STAFF_PROMO_MIN_DAYS = 60

ANNIVERSARY_ROLES = {
    1: {"name": "1 Year Veteran", "color": discord.Color.gold(), "xp": 1000},
    2: {"name": "2 Year Veteran", "color": discord.Color.purple(), "xp": 2000},
    3: {"name": "3 Year Legend",  "color": discord.Color.dark_red(), "xp": 3000}
}

LEVEL_TIER_ROLES = {
    (1, 9):   {"name": "Newbie",    "color": discord.Color.teal()},
    (10, 19): {"name": "Explorer",  "color": discord.Color.green()},
    (20, 29): {"name": "Vanguard",  "color": discord.Color.blue()},
    (30, 39): {"name": "Elite",     "color": discord.Color.purple()},
    (40, 49): {"name": "Champion",  "color": discord.Color.gold()},
    (50, 59): {"name": "Legend",    "color": discord.Color.orange()},
    (60, 60): {"name": "Sovereign", "color": discord.Color.dark_red()}
}

RESTRICTED_ADMIN_ROLES = ["authority", "head moderator", "moderator"]

PRO_HEX_COLORS = {
    "Pro Hex Red":    discord.Color.from_rgb(255, 75, 75),
    "Pro Hex Green":  discord.Color.from_rgb(75, 255, 125),
    "Pro Hex Blue":   discord.Color.from_rgb(75, 150, 255),
    "Pro Hex Pink":   discord.Color.from_rgb(255, 105, 180),
    "Pro Hex Yellow": discord.Color.from_rgb(255, 225, 75),
    "Pro Hex Orange": discord.Color.from_rgb(255, 140, 0)
}

GENDER_ROLE_PALETTE = {
    "Male": discord.Color.blue(),
    "Female": discord.Color.magenta(),
    "Non-Binary": discord.Color.purple()
}

TICKET_CHANNEL_FORMATS = {
    "team":   {"emoji": "💼", "tag": "apply"},
    "report": {"emoji": "⚠️", "tag": "complaint"},
    "help":   {"emoji": "❓", "tag": "support"}
}

# ==========================================
# CUTE & LOVING MESSAGE POOLS
# ==========================================
CUTE_BUMP_MESSAGES = [
    "You're absolute perfection! Thanks for helping us grow! 💖✨",
    "Sending you virtual warm hugs and lots of appreciation! 🧸🌸",
    "You just brightened up the whole server's day! 🌟✨",
    "Thank you for being so amazing and keeping our cozy home alive! 🐾💌",
    "You're a superstar! Server sparkles everywhere for you! ✨💖",
    "Breaking news: You are officially the server's favorite human right now! 🥐☕",
    "A wild hero appeared and bumped the server! You dropped this: 👑✨",
    "Our community grows stronger every time you sprinkle your magic! 🪄💫",
    "Sending 1,000,000 warm cookies directly to your inventory for that bump! 🍪🥛",
    "You deserve a gold medal, a sweet hug, and infinite good karma! 🏅💖",
    "The vibe level just shot up by 1000%! Thank you, absolute legend! 🚀🎉",
    "Proof that angels exist: you just took time out of your day to bump us! 🪽🌸",
    "Your kindness is unmatched! Take a bow, server MVP! 🎀💃",
    "May your snacks be forever delicious and your pillows cold on both sides! 🥪❄️",
    "Every time you bump, a puppy gets a treat and a flower blooms! 🐶🌼"
]

AFK_DEFAULT_REASONS = [
    "Recharging my social battery with snacks and naps 🔋🍰",
    "Temporarily wandering in dreamland... wake me up with treats 🧸💤",
    "Plotting world peace (or just taking a very long bath) 🛁🫧",
    "Distracted by something shiny. Send search parties if gone too long ✨🍪",
    "Currently touching grass! Will return shortly 🌿👣",
    "Doing secret undercover missions (definitely not eating cereal in bed) 🕵️‍♂️🥣"
]

AFK_PING_TEMPLATES = [
    "🤫 **Shhh!** {name} is away right now: *\"{reason}\"*. Leave a cookie and be gentle! 🍪💤",
    "💌 **Away from keyboard!** {name} stepped away: *\"{reason}\"*. Don't worry, they still love you! 💖✨",
    "🐾 **AFK Alert!** {name} is currently busy: *\"{reason}\"*. Your ping has been saved for their return! 📬🌸",
    "☁️ **Floating away!** {name} has temporarily vanished: *\"{reason}\"*. I'll let them know you missed them! 🧸💭"
]

AFK_WELCOME_BACK_MESSAGES = [
    "🥰 Look who decided to grace us with their presence again! Welcome back {mention}! ✨",
    "🎉 The legend returns! The chat was way too quiet without you, {mention}! 💖",
    "🔋 Social battery recharged! So happy to see you back in the room, {mention}! 🌸",
    "🥳 Hooray, {mention} is back! The server vibe is officially restored! 🍰💫"
]

BIRTHDAY_WISHES = [
    "Wishing you a fantastic year ahead filled with joy, success, and lots of cake! 🎂✨",
    "May all your wishes come true! Have an incredible celebration today! 🎈🎉",
    "Another trip around the sun! We're so lucky to have you in our community! 🌟🍰",
    "Happy Birthday! May your day be as sweet and bright as you are! 🎁💖",
    "Cheers to you on your special day! Enjoy every single moment! 🥳🎊",
    "Sending you the biggest virtual hugs and happiest birthday vibes! 🧸🌸"
]

# ==========================================
# BOT SETUP & STATE ARRAYS
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True

bot = commands.Bot(command_prefix=".", intents=intents)

MAINTENANCE_MODE = False

user_xp = defaultdict(dict)
user_levels = defaultdict(dict)
user_warnings = defaultdict(dict)
user_mute_counts = defaultdict(dict)
afk_users = defaultdict(dict)
afk_mentions = defaultdict(lambda: defaultdict(list))
user_birthdays = defaultdict(dict)
last_birthday_wished = defaultdict(dict)
last_anniversary_awarded = defaultdict(dict)
confession_counters = defaultdict(int)

last_xp_awarded = defaultdict(dict)
last_bump_times = defaultdict(float)
active_bump_tasks = {}

# ==========================================
# PERMISSION & HIERARCHY GUARDS
# ==========================================
@bot.check
async def global_maintenance_check(ctx):
    if not MAINTENANCE_MODE:
        return True
    if ctx.guild and (ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator):
        return True
    raise commands.CheckFailure("🛠️ **Maintenance Mode Active**: The bot is currently offline for system updates. Please try again shortly!")

def is_admin_or_owner():
    async def predicate(ctx):
        if ctx.guild and (ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator):
            return True
        raise commands.CheckFailure("⛔ **Permission Denied**: Only the Server Owner or an Administrator can use this command.")
    return commands.check(predicate)

def is_admin_or_higher():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
        user_roles = [r.name.lower() for r in ctx.author.roles]
        if any(role in user_roles for role in RESTRICTED_ADMIN_ROLES):
            return True
        raise commands.CheckFailure("⛔ **Permission Denied**: You do not possess the required staff permissions.")
    return commands.check(predicate)

def can_moderate_member(ctx, target: discord.Member) -> bool:
    if target.id == ctx.guild.owner_id:
        return False
    if ctx.guild.me.top_role <= target.top_role:
        return False
    if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= target.top_role:
        return False
    return True

# ==========================================
# PROGRESSION & ROLE ENGINE
# ==========================================
def get_xp_for_level(level: int) -> int:
    """Streamlined XP scaling formula for active chat progression."""
    if level >= MAX_LEVEL:
        return 35 * (MAX_LEVEL ** 2) + 120 * MAX_LEVEL
    return 35 * (level ** 2) + 120 * level

def get_tier_info_for_level(level: int) -> dict:
    for (min_lvl, max_lvl), tier_data in LEVEL_TIER_ROLES.items():
        if min_lvl <= level <= max_lvl:
            return tier_data
    return LEVEL_TIER_ROLES[(1, 9)]

async def ensure_role_exists(guild: discord.Guild, role_name: str, color: discord.Color, mentionable: bool = False) -> Optional[discord.Role]:
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            role = await guild.create_role(name=role_name, color=color, mentionable=mentionable, reason="Auto System Setup")
        except (discord.Forbidden, discord.HTTPException):
            return None
    return role

async def get_or_create_bump_role(guild: discord.Guild) -> Optional[discord.Role]:
    role = discord.utils.find(lambda r: r.name.lower() == "bumppings", guild.roles)
    if not role:
        try:
            role = await guild.create_role(
                name="BumpPings",
                color=discord.Color.gold(),
                mentionable=True,
                reason="Auto-created for server bump reminders"
            )
        except (discord.Forbidden, discord.HTTPException):
            return None
    elif not role.mentionable:
        try:
            await role.edit(mentionable=True)
        except (discord.Forbidden, discord.HTTPException):
            pass
    return role

async def update_member_level_role(member: discord.Member, new_level: int):
    guild = member.guild
    tier_info = get_tier_info_for_level(new_level)
    target_role = await ensure_role_exists(guild, tier_info["name"], tier_info["color"])

    if not target_role or guild.me.top_role <= target_role:
        return

    all_tier_names = [data["name"] for data in LEVEL_TIER_ROLES.values()]
    roles_to_remove = [r for r in member.roles if r.name in all_tier_names and r.id != target_role.id]

    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Level Tier Transition")
        if target_role not in member.roles:
            await member.add_roles(target_role, reason="Level Tier Advancement")
    except (discord.Forbidden, discord.HTTPException):
        pass

async def add_xp(user: discord.Member, amount: int):
    if user.bot or not user.guild:
        return

    gid = user.guild.id
    uid = user.id
    current_level = user_levels[gid].get(uid, 1)

    if current_level >= MAX_LEVEL:
        return

    current_xp = user_xp[gid].get(uid, 0) + amount
    xp_needed = get_xp_for_level(current_level)

    if current_xp >= xp_needed:
        new_level = min(current_level + 1, MAX_LEVEL)
        user_levels[gid][uid] = new_level
        user_xp[gid][uid] = current_xp - xp_needed

        await update_member_level_role(user, new_level)

        target_channel = await get_or_create_announcement_channel(user.guild)
        if target_channel:
            tier_info = get_tier_info_for_level(new_level)
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"{user.mention} has advanced to **Level {new_level}**!",
                color=tier_info["color"]
            )
            embed.add_field(name="Tier Reached", value=tier_info["name"])
            try:
                await target_channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass
    else:
        user_xp[gid][uid] = current_xp

# ==========================================
# PRO HEX NAME COLOR DYNAMICS
# ==========================================
async def apply_member_hex_color(member: discord.Member, role_name: str, color_obj: discord.Color) -> tuple[bool, str]:
    """
    Elevates the selected hex role directly beneath the bot's highest role
    so Discord displays this color above Level and Anniversary roles in chat.
    """
    guild = member.guild
    if not guild.me.guild_permissions.manage_roles:
        return False, "❌ Bot is missing the **Manage Roles** permission."

    target_role = discord.utils.get(guild.roles, name=role_name)
    if not target_role:
        try:
            target_role = await guild.create_role(
                name=role_name,
                color=color_obj,
                reason="Pro Hex Name Color Initialization"
            )
        except (discord.Forbidden, discord.HTTPException):
            return False, "❌ Failed to create color role. Check bot permissions."

    if guild.me.top_role <= target_role:
        return False, "❌ Hierarchy Error: Move the bot's role higher in Server Settings > Roles."

    try:
        bot_pos = guild.me.top_role.position
        desired_pos = max(1, bot_pos - 1)
        if target_role.position < desired_pos:
            await guild.edit_role_positions({target_role: desired_pos})
    except (discord.Forbidden, discord.HTTPException):
        pass

    current_colors = [
        r for r in member.roles 
        if r.name in PRO_HEX_COLORS.keys() or r.name.startswith("Color-")
    ]

    try:
        if current_colors:
            await member.remove_roles(*current_colors, reason="Updating active name color")
        await member.add_roles(target_role, reason="Member equipped Pro Hex color")
        return True, f"🎨 **Name Color Updated**: Your name is now styled with **{target_role.name}**!"
    except discord.Forbidden:
        return False, "❌ Discord rejected role assignment due to role hierarchy."
    except discord.HTTPException:
        return False, "❌ Network error updating roles. Please try again."

async def remove_member_hex_color(member: discord.Member) -> tuple[bool, str]:
    current_colors = [
        r for r in member.roles 
        if r.name in PRO_HEX_COLORS.keys() or r.name.startswith("Color-")
    ]
    if not current_colors:
        return False, "ℹ️ You do not currently have an active color role equipped."
    try:
        await member.remove_roles(*current_colors, reason="Member reset name color")
        return True, "🗑️ **Color Cleared**: Your name color has been reset to default."
    except (discord.Forbidden, discord.HTTPException):
        return False, "❌ Missing permissions to manage roles."

# ==========================================
# CHANNEL MANAGERS & ACCESS CONTROLS
# ==========================================
async def get_or_create_announcement_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = announcement_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(
        lambda c: c.name.lower() in [
            "announcements", "announcement", "📢・announcements",
            "level-announcements", "server-announcements"
        ],
        guild.text_channels
    )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            mention_everyone=True
        )
    }

    if channel:
        announcement_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("📢・announcements", overwrites=overwrites)
        announcement_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_bot_commands_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = bot_commands_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() in ["bot-commands", "bot_commands", "commands"], guild.text_channels)
    if channel:
        bot_commands_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("bot-commands")
        bot_commands_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_bump_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = bump_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() == "bump", guild.text_channels)
    if channel:
        bump_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("bump")
        bump_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_birthday_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = birthday_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() in ["birthday", "birthdays", "birthday-wishes"], guild.text_channels)
    if channel:
        birthday_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("birthdays")
        birthday_channels[guild.id] = new_ch.id
        await new_ch.send("🎂 **Birthdays Channel Initialized!** Use `.setbirthday DD-MM` here.")
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_confession_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = confession_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: "confession" in c.name.lower(), guild.text_channels)
    if channel:
        confession_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("🚦（︶︶）confession")
        confession_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_welcome_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = welcome_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() in ["welcome", "joins", "👋・welcome"], guild.text_channels)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    if channel:
        welcome_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("👋・welcome", overwrites=overwrites)
        welcome_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_colors_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = colors_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() in ["colours", "colors", "🎨・colours", "🎨・colors"], guild.text_channels)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    if channel:
        colors_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("🎨・colours", overwrites=overwrites)
        colors_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_team_rules_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = team_rules_channels.get(guild.id)
    channel = guild.get_channel(ch_id) if ch_id else None

    if not channel:
        channel = discord.utils.find(
            lambda c: c.name.lower() in ["team-rules", "staff-rules", "🛡️・team-rules"], 
            guild.text_channels
        )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    admin_perms = discord.PermissionOverwrite(view_channel=True, read_messages=True, read_message_history=True, send_messages=True)
    staff_read_only = discord.PermissionOverwrite(view_channel=True, read_messages=True, read_message_history=True, send_messages=False)

    if guild.owner:
        overwrites[guild.owner] = admin_perms

    for role in guild.roles:
        rname = role.name.lower()
        if role.permissions.administrator or rname in ["authority", "admin", "administrator"]:
            overwrites[role] = admin_perms
        elif rname in ["head moderator", "moderator", "team", "helper"]:
            overwrites[role] = staff_read_only

    if channel:
        team_rules_channels[guild.id] = channel.id
        try:
            for target, overwrite in overwrites.items():
                await channel.set_permissions(target, overwrite=overwrite)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return channel

    try:
        new_ch = await guild.create_text_channel("🛡️・team-rules", overwrites=overwrites)
        team_rules_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_team_news_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = team_news_channels.get(guild.id)
    channel = guild.get_channel(ch_id) if ch_id else None

    if not channel:
        channel = discord.utils.find(
            lambda c: c.name.lower() in ["team-news", "staff-news", "📰・team-news", "bot-updates"],
            guild.text_channels
        )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    admin_perms = discord.PermissionOverwrite(view_channel=True, read_messages=True, read_message_history=True, send_messages=True)
    staff_read_only = discord.PermissionOverwrite(view_channel=True, read_messages=True, read_message_history=True, send_messages=False)

    if guild.owner:
        overwrites[guild.owner] = admin_perms

    for role in guild.roles:
        rname = role.name.lower()
        if role.permissions.administrator or rname in ["authority", "admin", "administrator"]:
            overwrites[role] = admin_perms
        elif rname in ["head moderator", "moderator", "team", "helper"]:
            overwrites[role] = staff_read_only

    if channel:
        team_news_channels[guild.id] = channel.id
        try:
            for target, overwrite in overwrites.items():
                await channel.set_permissions(target, overwrite=overwrite)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return channel

    try:
        new_ch = await guild.create_text_channel("📰・team-news", overwrites=overwrites)
        team_news_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

async def get_or_create_ticket_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    cat = discord.utils.find(lambda c: c.name.lower() in ["tickets", "🎫 tickets"], guild.categories)
    if not cat:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
            }
            cat = await guild.create_category("🎫 TICKETS", overwrites=overwrites)
        except (discord.Forbidden, discord.HTTPException):
            return None
    return cat

async def get_or_create_locked_ticket_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    cat = discord.utils.find(lambda c: c.name.lower() in ["locked tickets", "🔒 locked tickets", "archived tickets"], guild.categories)
    if not cat:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
            }
            staff_perms = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, read_message_history=True)
            if guild.owner:
                overwrites[guild.owner] = staff_perms
            for role in guild.roles:
                if role.name.lower() == "authority" or role.permissions.administrator or role.name.lower() in ["admin", "administrator"]:
                    overwrites[role] = staff_perms

            cat = await guild.create_category("🔒 LOCKED TICKETS", overwrites=overwrites)
        except (discord.Forbidden, discord.HTTPException):
            return None
    return cat

async def get_or_create_memory_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    ch_id = bot_memory_channels.get(guild.id)
    channel = guild.get_channel(ch_id) if ch_id else None

    if not channel:
        channel = discord.utils.find(lambda c: c.name.lower() == "bot-memory", guild.text_channels)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False,
            read_messages=False,
            send_messages=False,
            read_message_history=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            attach_files=True,
            manage_channels=True
        )
    }

    if guild.owner:
        overwrites[guild.owner] = discord.PermissionOverwrite(
            view_channel=True,
            read_messages=True,
            read_message_history=True
        )

    for role in guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True
            )

    if channel:
        bot_memory_channels[guild.id] = channel.id
        try:
            for target, overwrite in overwrites.items():
                await channel.set_permissions(target, overwrite=overwrite)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return channel

    try:
        new_ch = await guild.create_text_channel("bot-memory", overwrites=overwrites)
        bot_memory_channels[guild.id] = new_ch.id
        return new_ch
    except (discord.Forbidden, discord.HTTPException):
        return None

# ==========================================
# SECURE DATABASE & BACKUP ENGINE
# ==========================================
async def save_data_to_channel(guild: discord.Guild, keep_last: int = 3):
    memory_channel = await get_or_create_memory_channel(guild)
    if not memory_channel:
        return

    gid = guild.id
    payload = {
        "user_xp": {str(k): v for k, v in user_xp[gid].items()},
        "user_levels": {str(k): v for k, v in user_levels[gid].items()},
        "user_warnings": {str(k): v for k, v in user_warnings[gid].items()},
        "user_mute_counts": {str(k): v for k, v in user_mute_counts[gid].items()},
        "afk_users": {str(k): v for k, v in afk_users[gid].items()},
        "user_birthdays": {str(k): v for k, v in user_birthdays[gid].items()},
        "last_anniversary": {str(k): v for k, v in last_anniversary_awarded[gid].items()},
        "confession_counter": confession_counters[gid],
        "last_bump_time": last_bump_times.get(gid, 0.0)
    }

    raw_json = json.dumps(payload, indent=2).encode("utf-8")
    data_file = discord.File(io.BytesIO(raw_json), filename=f"backup_{gid}.json")
    timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        await memory_channel.send(f"💾 **[DATABASE STATE SYNC]** `{timestamp}`", file=data_file)
    except (discord.Forbidden, discord.HTTPException):
        return

    try:
        backup_messages = []
        async for message in memory_channel.history(limit=50):
            if message.author.id == bot.user.id and message.attachments:
                if any(att.filename.endswith(".json") for att in message.attachments):
                    backup_messages.append(message)

        if len(backup_messages) > keep_last:
            for old_message in backup_messages[keep_last:]:
                try:
                    await old_message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
    except Exception as e:
        print(f"Error purging old backups for {guild.id}: {e}")

async def purge_all_backups(guild: discord.Guild, keep_newest: int = 1) -> int:
    memory_channel = await get_or_create_memory_channel(guild)
    if not memory_channel:
        return 0

    backup_messages = []
    try:
        async for msg in memory_channel.history(limit=100):
            if msg.attachments and any(att.filename.lower().endswith(".json") for att in msg.attachments):
                backup_messages.append(msg)

        to_delete = backup_messages[keep_newest:] if keep_newest > 0 else backup_messages
        deleted_count = 0

        for msg in to_delete:
            try:
                await msg.delete()
                deleted_count += 1
                await asyncio.sleep(0.3)
            except (discord.NotFound, discord.Forbidden):
                pass

        return deleted_count
    except Exception as e:
        print(f"Error purging backups for {guild.id}: {e}")
        return 0

async def restore_data_from_channel(guild: discord.Guild, target_attachment: discord.Attachment = None, target_index: int = None) -> int:
    gid = guild.id

    def parse_payload(data: dict) -> tuple[dict, int, int]:
        if not isinstance(data, dict):
            return {}, 0, 0

        raw_levels = data.get("user_levels") or data.get("levels") or {}
        raw_xp = data.get("user_xp") or data.get("xp") or {}
        raw_warns = data.get("user_warnings") or data.get("warnings") or {}
        raw_mutes = data.get("user_mute_counts") or data.get("mutes") or {}
        raw_afk = data.get("afk_users") or data.get("afk") or {}
        raw_bdays = data.get("user_birthdays") or data.get("birthdays") or {}
        raw_anni = data.get("last_anniversary") or data.get("anniversaries") or {}

        parsed_levels = {int(k): int(v) for k, v in raw_levels.items() if str(k).isdigit()}
        parsed_xp = {int(k): int(v) for k, v in raw_xp.items() if str(k).isdigit()}

        if not parsed_levels and not parsed_xp:
            return {}, 0, 0

        total_xp = sum(parsed_xp.values())
        highest_lvl = max(parsed_levels.values()) if parsed_levels else 1

        clean_dict = {
            "levels": parsed_levels,
            "xp": parsed_xp,
            "warnings": {int(k): int(v) for k, v in raw_warns.items() if str(k).isdigit()},
            "mutes": {int(k): int(v) for k, v in raw_mutes.items() if str(k).isdigit()},
            "afk": {int(k): str(v) for k, v in raw_afk.items() if str(k).isdigit()},
            "birthdays": {int(k): v for k, v in raw_bdays.items() if str(k).isdigit()},
            "anniversary": {int(k): int(v) for k, v in raw_anni.items() if str(k).isdigit()},
            "confession_counter": data.get("confession_counter", 0),
            "last_bump_time": data.get("last_bump_time", 0.0),
            "total_xp": total_xp,
            "highest_lvl": highest_lvl
        }
        return clean_dict, len(parsed_levels), total_xp

    def apply_data(clean: dict):
        user_levels[gid] = clean["levels"]
        user_xp[gid] = clean["xp"]
        user_warnings[gid] = clean["warnings"]
        user_mute_counts[gid] = clean["mutes"]
        afk_users[gid] = clean["afk"]
        user_birthdays[gid] = clean["birthdays"]
        last_anniversary_awarded[gid] = clean["anniversary"]
        confession_counters[gid] = clean["confession_counter"]
        last_bump_times[gid] = clean["last_bump_time"]

    if target_attachment:
        try:
            content = await target_attachment.read()
            clean, count, _ = parse_payload(json.loads(content.decode("utf-8")))
            if count > 0:
                apply_data(clean)
                return count
        except Exception as e:
            print(f"Failed parsing direct attachment: {e}")
            return 0

    memory_channel = await get_or_create_memory_channel(guild)
    if not memory_channel:
        return 0

    candidate_backups = []

    try:
        async for message in memory_channel.history(limit=150):
            if message.attachments:
                for att in message.attachments:
                    if att.filename.lower().endswith(".json"):
                        try:
                            content = await att.read()
                            clean, count, total_xp = parse_payload(json.loads(content.decode("utf-8")))
                            if count > 0:
                                candidate_backups.append({
                                    "clean": clean,
                                    "count": count,
                                    "total_xp": total_xp,
                                    "created_at": message.created_at,
                                    "filename": att.filename
                                })
                        except Exception:
                            continue
    except discord.Forbidden:
        print(f"Missing history permissions in #{memory_channel.name}")
        return 0

    if not candidate_backups:
        return 0

    if target_index is not None and 0 <= target_index < len(candidate_backups):
        chosen = candidate_backups[target_index]
        apply_data(chosen["clean"])
        return chosen["count"]

    for bkp in candidate_backups:
        if bkp["total_xp"] > 0 or bkp["clean"]["highest_lvl"] > 1:
            apply_data(bkp["clean"])
            return bkp["count"]

    chosen = candidate_backups[0]
    apply_data(chosen["clean"])
    return chosen["count"]

# ==========================================
# BACKGROUND SCHEDULED TASKS
# ==========================================
@tasks.loop(minutes=10)
async def periodic_backup_loop():
    for guild in bot.guilds:
        try:
            await save_data_to_channel(guild)
        except Exception as e:
            print(f"Error during backup loop for {guild.id}: {e}")

@periodic_backup_loop.before_loop
async def before_backup():
    await bot.wait_until_ready()

@tasks.loop(hours=1)
async def check_birthdays_loop():
    now = datetime.datetime.now(datetime.timezone.utc)
    current_day = now.day
    current_month = now.month
    current_year = now.year

    for guild in bot.guilds:
        gid = guild.id
        if gid not in user_birthdays:
            continue

        bday_ch = await get_or_create_birthday_channel(guild)
        if not bday_ch:
            continue

        for uid, bday in list(user_birthdays[gid].items()):
            if bday["day"] == current_day and bday["month"] == current_month:
                if last_birthday_wished[gid].get(uid) == current_year:
                    continue

                member = guild.get_member(uid)
                if not member:
                    continue

                last_birthday_wished[gid][uid] = current_year
                wish_line = random.choice(BIRTHDAY_WISHES)

                age_display = ""
                if bday.get("year"):
                    age = current_year - bday["year"]
                    age_display = f" turning **{age}** today"

                embed = discord.Embed(
                    title="🎉 Happy Birthday! 🎂",
                    description=(
                        f"Join us in wishing {member.mention}{age_display} an amazing birthday!\n\n"
                        f"> *\"{wish_line}\"*\n\n"
                        f"🎁 **Birthday Bonus**: Awarded **+500 XP**!"
                    ),
                    color=discord.Color.magenta(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"{guild.name} Celebrations 🎈")

                try:
                    await bday_ch.send(content=f"🎊 Happy Birthday {member.mention}! 🎊", embed=embed)
                    await add_xp(member, 500)
                except (discord.Forbidden, discord.HTTPException):
                    pass

@check_birthdays_loop.before_loop
async def before_birthdays():
    await bot.wait_until_ready()

@tasks.loop(hours=24)
async def check_anniversaries_loop():
    now = datetime.datetime.now(datetime.timezone.utc)

    for guild in bot.guilds:
        gid = guild.id
        announcement_ch = await get_or_create_announcement_channel(guild)
        og_role = await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.magenta())

        for member in guild.members:
            if member.bot or not member.joined_at:
                continue

            days_in_server = (now - member.joined_at).days
            years_in_server = days_in_server // 365

            if days_in_server >= OG_DAYS_REQUIRED and og_role and og_role not in member.roles:
                try:
                    await member.add_roles(og_role, reason="Server Tenure Milestone: 1 Year (OG)")
                except (discord.Forbidden, discord.HTTPException):
                    pass

            if years_in_server > 0 and last_anniversary_awarded[gid].get(member.id) != years_in_server:
                if member.joined_at.month == now.month and member.joined_at.day == now.day:
                    last_anniversary_awarded[gid][member.id] = years_in_server
                    tier_info = ANNIVERSARY_ROLES.get(years_in_server, {
                        "name": f"{years_in_server} Year Veteran",
                        "color": discord.Color.blurple(),
                        "xp": 1000 * years_in_server
                    })

                    milestone_role = await ensure_role_exists(guild, tier_info["name"], tier_info["color"])
                    if milestone_role and milestone_role not in member.roles:
                        try:
                            await member.add_roles(milestone_role, reason=f"Tenure Milestone: Year {years_in_server}")
                        except (discord.Forbidden, discord.HTTPException):
                            pass

                    await add_xp(member, tier_info["xp"])

                    if announcement_ch:
                        embed = discord.Embed(
                            title="🎖️ Server Anniversary Milestone!",
                            description=(
                                f"Congratulations to {member.mention} on reaching **{years_in_server} Year(s)** in {guild.name}!\n\n"
                                f"⭐ **Roles Awarded:** `{tier_info['name']}` and `{OG_ROLE_NAME}`\n"
                                f"🎁 **Tenure Bonus:** Awarded **+{tier_info['xp']} XP**!"
                            ),
                            color=tier_info["color"],
                            timestamp=discord.utils.utcnow()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.set_footer(text=f"Server Loyalty Recognition • {BOT_COMPANY_NAME}")
                        try:
                            await announcement_ch.send(embed=embed)
                        except (discord.Forbidden, discord.HTTPException):
                            pass

@check_anniversaries_loop.before_loop
async def before_anniversaries():
    await bot.wait_until_ready()

# ==========================================
# BUMP REMINDER SCHEDULER
# ==========================================
async def schedule_bump_reminders(guild: discord.Guild, bump_channel: discord.TextChannel):
    try:
        await asyncio.sleep(6300)
        warning_unix = int(datetime.datetime.now(datetime.timezone.utc).timestamp() + 900)
        await bump_channel.send(
            f"⏳ **Bump Heads-Up**: Next bump available in **15 minutes** (<t:{warning_unix}:R>)!"
        )

        await asyncio.sleep(900)
        bump_role = await get_or_create_bump_role(guild)
        role_mention = bump_role.mention if bump_role else "@here"

        await bump_channel.send(
            f"🔔 {role_mention} **It's Time To Bump!** Use `.bump` to promote the server again!",
            allowed_mentions=discord.AllowedMentions(roles=True, everyone=True)
        )
    except asyncio.CancelledError:
        pass
    finally:
        active_bump_tasks.pop(guild.id, None)

# ==========================================
# ONBOARDING: MODAL & DM VIEW
# ==========================================
class WelcomeProfileModal(discord.ui.Modal, title="Server Profile Setup"):
    preferred_name = discord.ui.TextInput(
        label="Preferred Name / Nickname",
        placeholder="How should everyone address you?",
        required=True,
        max_length=32
    )
    gender_input = discord.ui.TextInput(
        label="Gender / Pronouns",
        placeholder="e.g. Male (He/Him), Female (She/Her), Non-Binary",
        required=True,
        max_length=30
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = bot.get_guild(self.guild_id)
        if not guild:
            return await interaction.followup.send("❌ Server connection lost. Please setup inside a server channel.", ephemeral=True)

        try:
            member = guild.get_member(interaction.user.id) or await guild.fetch_member(interaction.user.id)
        except (discord.NotFound, discord.HTTPException):
            return await interaction.followup.send("❌ You are no longer present in this server.", ephemeral=True)

        new_name = self.preferred_name.value.strip()
        gender_raw = self.gender_input.value.strip()

        nickname_updated = False
        if guild.me.guild_permissions.manage_nicknames and guild.me.top_role > member.top_role and member.id != guild.owner_id:
            try:
                await member.edit(nick=new_name, reason="Onboarding self-setup")
                nickname_updated = True
            except (discord.Forbidden, discord.HTTPException):
                nickname_updated = False

        matched_role_name = None
        for key in GENDER_ROLE_PALETTE.keys():
            if key.lower() in gender_raw.lower():
                matched_role_name = key
                break

        assigned_role = None
        if matched_role_name:
            assigned_role = await ensure_role_exists(guild, matched_role_name, GENDER_ROLE_PALETTE[matched_role_name])
            if assigned_role and guild.me.top_role > assigned_role:
                try:
                    await member.add_roles(assigned_role, reason="Onboarding Gender Selection")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        details = [f"• **Preferred Name:** `{new_name}`" + (" *(Nickname applied)*" if nickname_updated else "")]
        if assigned_role:
            details.append(f"• **Gender Role:** `{assigned_role.name}`")
        else:
            details.append(f"• **Gender / Pronouns:** `{gender_raw}`")

        embed = discord.Embed(
            title=f"✅ Welcome to {guild.name}!",
            description="Your profile setup is complete!\n\n" + "\n".join(details) + "\n\nYou're all set to start chatting!",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

class WelcomeProfileButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(
            label="Set Name & Gender",
            style=discord.ButtonStyle.success,
            emoji="📝",
            custom_id=f"persistent_onboard_btn_{guild_id}"
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WelcomeProfileModal(guild_id=self.guild_id))

class WelcomeProfileView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.add_item(WelcomeProfileButton(guild_id))

# ==========================================
# UI COMPONENTS & MODALS
# ==========================================
class ResignConfirmView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("⛔ **Access Denied**: Only the member resigning can choose.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes, Resign", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="⏳ **Processing staff role removal...**", embed=None, view=self)
        self.stop()

    @discord.ui.button(label="No, Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Resignation Cancelled**: Your roles remain untouched.", embed=None, view=self)
        self.stop()

class RestoreConfirmView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("⛔ **Access Denied**: Only the administrator running this command can interact.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Overwrite", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="⏳ **Restoring server database from `#bot-memory`...**", embed=None, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Operation Aborted**: In-memory state remains untouched.", embed=None, view=self)
        self.stop()

class ConfessionModal(discord.ui.Modal, title="Submit Anonymous Confession"):
    confession_input = discord.ui.TextInput(
        label="Your Secret Confession",
        style=discord.TextStyle.paragraph,
        placeholder="Type your confession here... Submissions are 100% anonymous!",
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        confession_ch = await get_or_create_confession_channel(interaction.guild)
        if not confession_ch:
            return await interaction.response.send_message("❌ Could not access the confession channel.", ephemeral=True)

        gid = interaction.guild.id
        confession_counters[gid] += 1
        num = confession_counters[gid]

        embed = discord.Embed(
            title=f"💌 Anonymous Confession #{num}",
            description=self.confession_input.value,
            color=discord.Color.from_rgb(255, 105, 180),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="100% Anonymous Submission • Server Confessions")

        await confession_ch.send(embed=embed)
        await interaction.response.send_message("✅ **Confession posted anonymously!**", ephemeral=True)

class ConfessionButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Send Anonymous Confession", style=discord.ButtonStyle.primary, emoji="🤫", custom_id="persistent_confession_btn")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfessionModal())

class ProHexColorSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Pro Hex Red", emoji="🔴", description="Equip vibrant red name color"),
            discord.SelectOption(label="Pro Hex Green", emoji="🟢", description="Equip vibrant green name color"),
            discord.SelectOption(label="Pro Hex Blue", emoji="🔵", description="Equip ocean blue name color"),
            discord.SelectOption(label="Pro Hex Pink", emoji="🌸", description="Equip pastel pink name color"),
            discord.SelectOption(label="Pro Hex Yellow", emoji="🟡", description="Equip bright yellow name color"),
            discord.SelectOption(label="Pro Hex Orange", emoji="🟠", description="Equip deep orange name color"),
            discord.SelectOption(label="Remove Color", emoji="✖️", description="Reset your name color to default")
        ]
        super().__init__(
            placeholder="🎨 Choose your name color...",
            min_values=1,
            max_values=1,
            custom_id="persistent_member_color_select",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # 1. Instantly acknowledge interaction within Discord's 3-second deadline
        await interaction.response.defer(ephemeral=True)

        user = interaction.user
        selected = self.values[0]

        if selected == "Remove Color":
            _, msg = await remove_member_hex_color(user)
            return await interaction.followup.send(msg, ephemeral=True)

        # 2. Apply color and send feedback via followup
        color_obj = PRO_HEX_COLORS.get(selected, discord.Color.default())
        _, msg = await apply_member_hex_color(user, selected, color_obj)
        await interaction.followup.send(msg, ephemeral=True)

class ColorSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ProHexColorSelect())

# ==========================================
# SUPPORT TICKET CONTROLS & VIEWS
# ==========================================
class TicketCloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30.0)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 **Closing and deleting ticket in 3 seconds...**")
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except (discord.Forbidden, discord.HTTPException):
            pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Ticket closure cancelled.**", view=self)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lock Ticket", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="persistent_ticket_lock")
    async def lock_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        channel = interaction.channel

        is_staff = (
            user.id == guild.owner_id
            or user.guild_permissions.administrator
            or any(r.name.lower() == "authority" or r.name.lower() in ["admin", "administrator"] for r in user.roles)
        )
        if not is_staff:
            return await interaction.response.send_message("⛔ **Access Denied**: Only Authority, Admins, or Owner can lock tickets.", ephemeral=True)

        locked_category = await get_or_create_locked_ticket_category(guild)
        if not locked_category:
            return await interaction.response.send_message("❌ Could not locate the locked category.", ephemeral=True)

        if channel.category_id == locked_category.id:
            return await interaction.response.send_message("⚠️ This ticket is already locked.", ephemeral=True)

        await interaction.response.defer()

        for target, overwrite in list(channel.overwrites.items()):
            if isinstance(target, discord.Member) and target != guild.me and target.id != guild.owner_id:
                overwrite.send_messages = False
                try:
                    await channel.set_permissions(target, overwrite=overwrite)
                except (discord.Forbidden, discord.HTTPException):
                    pass

        clean_tag = channel.name.split("・")[-1] if "・" in channel.name else channel.name
        new_name = f"🔒・{clean_tag}"[:100]

        try:
            await channel.edit(name=new_name, category=locked_category)
        except (discord.Forbidden, discord.HTTPException):
            pass

        embed = discord.Embed(
            title="🔒 Ticket Locked & Archived",
            description=(
                f"This ticket was locked by {user.mention}.\n\n"
                f"• Member typing disabled (Read-Only).\n"
                f"• Transferred to: **{locked_category.name}**.\n"
                f"• Click **Close Ticket** below to delete."
            ),
            color=discord.Color.dark_grey(),
            timestamp=discord.utils.utcnow()
        )
        await channel.send(embed=embed)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="persistent_ticket_close")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TicketCloseConfirmView()
        await interaction.response.send_message("⚠️ **Are you sure you want to permanently delete this ticket channel?**", view=view, ephemeral=True)

async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, title: str, instructions: str, color: discord.Color):
    guild = interaction.guild
    user = interaction.user

    existing_channel = discord.utils.find(lambda c: ticket_type in c.name and str(user.id) in (c.topic or ""), guild.text_channels)
    if existing_channel:
        return await interaction.response.send_message(f"❌ You already have an open ticket in {existing_channel.mention}!", ephemeral=True)

    category = await get_or_create_ticket_category(guild)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, read_messages=False, send_messages=False),
        user: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, manage_channels=True, manage_messages=True)
    }

    staff_permissions = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True)

    if guild.owner:
        overwrites[guild.owner] = staff_permissions

    ticket_staff_mentions = []
    for role in guild.roles:
        is_authority = role.name.lower() == "authority"
        is_admin_role = role.permissions.administrator or role.name.lower() in ["admin", "administrator"]

        if is_authority or is_admin_role:
            overwrites[role] = staff_permissions
            ticket_staff_mentions.append(role.mention)

    clean_username = "".join(c for c in user.name.lower() if c.isalnum())[:10]
    style = TICKET_CHANNEL_FORMATS.get(ticket_type, {"emoji": "🎫", "tag": ticket_type})
    channel_name = f"{style['emoji']}・{style['tag']}-{clean_username}"

    try:
        ticket_ch = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Owner ID: {user.id} | Type: {title}"
        )
    except (discord.Forbidden, discord.HTTPException):
        return await interaction.response.send_message("❌ Bot lacks permission to create/manage channels.", ephemeral=True)

    embed = discord.Embed(
        title=f"{style['emoji']} {title}",
        description=f"Welcome {user.mention}!\n\n{instructions}\n\n🔒 *This ticket is private between you, Server Owner, Authority, and Administrators.*",
        color=color,
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Ticket Owner: {user.display_name} • Click Close when resolved")

    staff_ping_text = " ".join(set(ticket_staff_mentions)) if ticket_staff_mentions else ""
    await ticket_ch.send(content=f"{user.mention} {staff_ping_text}".strip(), embed=embed, view=TicketControlView())
    await interaction.response.send_message(f"✅ **Ticket Created!** Go to {ticket_ch.mention}.", ephemeral=True)

async def build_and_send_ticket(guild: discord.Guild, user: discord.Member, topic: str = "General Inquiry") -> Optional[discord.TextChannel]:
    category = await get_or_create_ticket_category(guild)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True, manage_messages=True)
    }

    staff_perms = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True)
    if guild.owner:
        overwrites[guild.owner] = staff_perms

    staff_mentions = []
    for role in guild.roles:
        if role.name.lower() == "authority" or role.permissions.administrator or role.name.lower() in ["admin", "administrator"]:
            overwrites[role] = staff_perms
            staff_mentions.append(role.mention)

    clean_username = "".join(c for c in user.name.lower() if c.isalnum())[:10]
    channel_name = f"🎫・ticket-{clean_username}"

    try:
        ticket_ch = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Owner ID: {user.id} | Subject: {topic}"
        )
    except (discord.Forbidden, discord.HTTPException):
        return None

    embed = discord.Embed(
        title="🎫 Support Ticket Opened",
        description=(
            f"Hello {user.mention}, thank you for reaching out!\n\n"
            f"📌 **Subject / Reason:**\n> {topic}\n\n"
            "💬 **Instructions:**\n"
            "• Provide any relevant details, screenshots, or context below.\n"
            "• Our leadership team has been alerted and will respond shortly.\n\n"
            "🔒 *This ticket is completely private between you, Authority, and Administrators.*"
        ),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text=f"Ticket Owner: {user.display_name} • Click buttons below to manage")

    ping_header = f"{user.mention} " + " ".join(set(staff_mentions))
    await ticket_ch.send(content=ping_header.strip(), embed=embed, view=TicketControlView())
    return ticket_ch

class TicketLauncherView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join Team", style=discord.ButtonStyle.primary, emoji="💼", custom_id="ticket_btn_team")
    async def join_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(
            interaction,
            ticket_type="team",
            title="Staff & Team Application",
            instructions=(
                "**Thank you for your interest in joining our team!**\n"
                "Please provide the following details:\n"
                "• Role applying for (Moderator / Event Staff)\n"
                "• Your age & timezone\n"
                "• Previous moderation experience\n"
                "• Approximate weekly hours available"
            ),
            color=discord.Color.teal()
        )

    @discord.ui.button(label="File Complaint", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="ticket_btn_complaint")
    async def complaint(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(
            interaction,
            ticket_type="report",
            title="Member Report / Server Complaint",
            instructions=(
                "**Please submit the details of your report below:**\n"
                "• Username(s) / ID(s) of members involved\n"
                "• Detailed explanation of the incident\n"
                "• Attach relevant screenshots or message links"
            ),
            color=discord.Color.red()
        )

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.secondary, emoji="❓", custom_id="ticket_btn_general")
    async def general(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(
            interaction,
            ticket_type="help",
            title="General Support & Inquiries",
            instructions="**How can we help you today?**\nPlease describe your question or issue in detail.",
            color=discord.Color.blue()
        )

# ==========================================
# TEAM RULES & MANUAL PUBLISHERS
# ==========================================
async def publish_or_update_team_rules(guild: discord.Guild) -> Optional[discord.Message]:
    rules_ch = await get_or_create_team_rules_channel(guild)
    if not rules_ch:
        return None

    try:
        async for msg in rules_ch.history(limit=25):
            if msg.author.id == bot.user.id and msg.embeds:
                if any("Staff & Team Code of Conduct" in (e.title or "") for e in msg.embeds):
                    try:
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass
    except Exception as e:
        print(f"Error purging old team rules in {guild.id}: {e}")

    embed = discord.Embed(
        title="🛡️ Server Staff & Team Code of Conduct",
        description=(
            f"Welcome to the official staff roster of **{guild.name}**.\n\n"
            "Holding a staff rank is a responsibility, not a trophy. You represent our community standard. "
            "Every moderator and team member is held strictly accountable to the guidelines below.\n"
        ),
        color=discord.Color.teal(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="✅ WHAT TEAM MEMBERS CAN & MUST DO",
        value=(
            "• **Enforce Rules Neutrally:** Issue warnings and mutes based strictly on server guidelines—never personal bias or drama.\n"
            "• **De-Escalate Situations:** Attempt verbal warnings or topic redirection before executing formal timeouts or kicks.\n"
            "• **Document Actions:** Always supply a clear, legitimate reason when executing `.warn`, `.mute`, `.kick`, or `.ban`.\n"
            "• **Handle Support Tickets:** Claim and address tickets in `🎫 TICKETS` with patience and professionalism.\n"
            "• **Use Channel Controls Responsibly:** Utilize `.lockdown` or `.purge` strictly during raids, spam floods, or severe disruptions.\n"
            "• **Escalate to Leadership:** Report ban-worthy offenses or internal staff disputes directly to `Authority` or Server Owners.\n"
            "• **Resign Honorably:** If real-life commitments arise, step down cleanly using `.resign` without abandoning duties mid-incident."
        ),
        inline=False
    )

    embed.add_field(
        name="❌ WHAT TEAM MEMBERS CANNOT DO (ZERO TOLERANCE)",
        value=(
            "• **Power-Tripping & Harassment:** Never threaten, insult, or punish members because you dislike them or lost an argument.\n"
            "• **Confidentiality Leaks:** Leaking private ticket contents, anonymous confession logs, staff deliberations, or `#bot-memory` results in an **instant ban**.\n"
            "• **Overriding Fellow Staff:** Do not lift mutes, clear warnings, or reverse actions taken by another moderator without consulting them.\n"
            "• **Channel & Role Abuse:** Do not grant unauthorized roles, create rogue channels, or modify bot configurations.\n"
            "• **Public Arguments:** Never argue with fellow staff members in public chat. Settle differences privately or inside staff-only channels.\n"
            "• **Backdoor / Admin Exploitation:** Lower staff may not touch database snapshots (`.savedata`, `.restoredata`) or bypass bot maintenance.\n"
            "• **Solicitation:** Promoting personal projects, external servers, or accepting payment for favors is strictly prohibited."
        ),
        inline=False
    )

    embed.add_field(
        name="⚖️ Escalation Chain & Inactivity",
        value=(
            "1. **First Offense:** Formal warning & internal leadership review.\n"
            "2. **Second Offense:** Demotion to standard member and temporary moderation restriction.\n"
            "3. **Inactivity Policy:** Staff absent for more than **7 consecutive days** without notice will be temporarily relieved of their roles until return."
        ),
        inline=False
    )

    embed.set_footer(text=f"{guild.name} Leadership Guidelines • Enforced by {BOT_COMPANY_NAME}")
    return await rules_ch.send(embed=embed)

async def publish_or_update_botcommands(guild: discord.Guild, update_note: str = None) -> Optional[discord.Message]:
    cmd_ch = await get_or_create_bot_commands_channel(guild)
    if not cmd_ch:
        return None

    try:
        async for msg in cmd_ch.history(limit=50):
            if msg.author.id == bot.user.id and msg.embeds:
                for embed in msg.embeds:
                    if embed.title and ("Command" in embed.title or "Manual" in embed.title or "Reference" in embed.title):
                        try:
                            await msg.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
    except Exception as e:
        print(f"Error purging old manual in {guild.id}: {e}")

    note_text = f"\n> *{update_note}*\n" if update_note else ""
    embed = discord.Embed(
        title="⚙️ Bot Command Manual & System Reference",
        description=f"**Official Server Command Directory**{note_text}\nComplete guide for all member features, leveling, support tickets, and staff controls:",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="🎖️ Leveling & Member Perks (#bot-commands)",
        value=(
            "`.level [@user]` — Check rank, level tier, and progress bar.\n"
            "`.leaderboard` — Display top 10 ranked server members.\n"
            "`.tenure [@user]` — Check exact join date & time in server.\n"
            "`.color <preset/#HEX>` — Equip custom color role in chat.\n"
            "`.userinfo [@user]` — View member profile, joins & strikes.\n"
            "`.serverinfo` — Show guild analytics & member count.\n"
            "`.afk [reason]` — Toggle AFK status with automated ping alerts."
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Old (OG) Veteran System",
        value=(
            "`.old [@user]` — Check if a member qualifies for OG status (365+ days).\n"
            "`.old auto` — Auto-scan server roster & assign OG role to 1yr+ members.\n"
            "`.old manual @user` — Staff override to grant OG status directly.\n"
            "`.old remove @user` — Staff override to revoke OG status.\n"
            "`.old list` — Display all members currently holding the OG role."
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Private Support Tickets (#tickets)",
        value=(
            "`.ticketpanel` — Spawn the interactive support panel.\n"
            "`.createticket [reason]` — Manually open a dedicated ticket channel.\n"
            "• **💼 Join Team** — Private staff/moderator application.\n"
            "• **⚠️ File Complaint** — Report a user or server violation.\n"
            "• **❓ General Support** — Inquiries & general assistance."
        ),
        inline=False
    )

    embed.add_field(
        name="📢 Broadcasts & Announcements",
        value=(
            "`.announce [@everyone/@here] <text>` — Broadcast an official announcement to `#announcements` (supports image uploads).\n"
            "`.botupdate <Title> | <Details>` — Dispatch a new bot capability notice into `#team-news`."
        ),
        inline=False
    )

    embed.add_field(
        name="🚦 Anonymous Confessions (#confession)",
        value=(
            "`.confesspanel` — Post the interactive secret confession button.\n"
            "`.confess <message>` — Submit an anonymous confession (auto-deleted)."
        ),
        inline=False
    )

    embed.add_field(
        name="🚀 Server Growth & Birthdays",
        value=(
            "`.bump` — Bump the server (+200 XP, 2h timer & pings `@BumpPings`).\n"
            "`.setbirthday DD-MM[-YYYY]` — Register birthday for celebration bonuses.\n"
            "`.birthday [@user]` — Look up a registered birthday date."
        ),
        inline=False
    )

    embed.add_field(
        name="🔒 Staff & Role Administration",
        value=(
            "`.promote @user <Role>` — Promote a staff member.\n"
            "`.resign [reason]` — Step down from staff roles (interactive prompt).\n"
            "`.authority @user` — Assign the core Authority staff role.\n"
            "`.assign @user <Role>` / `.revoke @user <Role>` — Manage roles.\n"
            "`.role addall <Role>` / `.role removeall <Role>` — Mass role management.\n"
            "`.role members <Role>` — View non-bot members holding a role.\n"
            "`.autorole_setup` — Initialize tier roles, colors, and `BumpPings`.\n"
            "`.colorpanel` — Post member color dropdown in `#colours`.\n"
            "`.welcomesetup` — Post persistent onboarding card in `#welcome`.\n"
            "`.teamrules` — Refresh code of conduct embed in `#team-rules`."
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation & Channel Controls",
        value=(
            "`.warn @user [reason]` — Issue formal strike (3 strikes = Auto-Ban).\n"
            "`.clearwarns @user` — Reset member strikes.\n"
            "`.mute @user [reason]` — Escalating timeout (1h ➔ 6h ➔ 12h).\n"
            "`.unmute @user` — Lift member timeout.\n"
            "`.kick @user` / `.ban @user` — Evict member from server.\n"
            "`.purge <1-100>` — Bulk clear chat messages.\n"
            "`.lockdown` / `.unlock` — Restrict/restore text channel typing.\n"
            "`.vc_lock` / `.vc_unlock` — Restrict/restore voice connects."
        ),
        inline=False
    )

    embed.add_field(
        name="💾 System & Maintenance Engine (Admin Only)",
        value=(
            "`.savedata` — Save snapshot to `#bot-memory`.\n"
            "`.restoredata [index]` — Smart restore (skips 0-XP snapshots).\n"
            "`.backups` — List all historical backups in `#bot-memory`.\n"
            "`.cleanbackups [keep]` — Delete old backup messages from `#bot-memory`.\n"
            "`.maintenance on/off` — Freeze activity and secure state for updates.\n"
            "`.restart` — Safe pre-backup snapshot & in-place bot process reboot.\n"
            "`.botcommands [note]` — Refresh manual directory & purge outdated post."
        ),
        inline=False
    )

    embed.set_footer(text=f"Official Manual • Maintained by {BOT_CREATOR_USERNAME} ({BOT_COMPANY_NAME})")
    return await cmd_ch.send(embed=embed)

# ==========================================
# SYSTEM EVENT LISTENERS
# ==========================================
@bot.event
async def on_ready():
    if getattr(bot, "has_run_ready", False):
        return
    bot.has_run_ready = True

    bot.add_view(TicketLauncherView())
    bot.add_view(TicketControlView())
    bot.add_view(ConfessionButtonView())
    bot.add_view(ColorSelectView())

    for guild in bot.guilds:
        bot.add_view(WelcomeProfileView(guild.id))

    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"System Creator: {BOT_CREATOR_USERNAME} ({BOT_CREATOR_REAL_NAME}) | {BOT_COMPANY_NAME}")

    if not periodic_backup_loop.is_running():
        periodic_backup_loop.start()
    if not check_birthdays_loop.is_running():
        check_birthdays_loop.start()
    if not check_anniversaries_loop.is_running():
        check_anniversaries_loop.start()

    for guild in bot.guilds:
        await get_or_create_bump_channel(guild)
        await get_or_create_bot_commands_channel(guild)
        await get_or_create_birthday_channel(guild)
        await get_or_create_bump_role(guild)
        await get_or_create_confession_channel(guild)
        await get_or_create_welcome_channel(guild)
        await get_or_create_team_rules_channel(guild)
        await get_or_create_team_news_channel(guild)
        await get_or_create_ticket_category(guild)
        await get_or_create_locked_ticket_category(guild)
        await get_or_create_memory_channel(guild)

        rules_ch = await get_or_create_team_rules_channel(guild)
        if rules_ch:
            history = [m async for m in rules_ch.history(limit=5)]
            if not any(m.author.id == bot.user.id and m.embeds for m in history):
                await publish_or_update_team_rules(guild)

        colors_ch = await get_or_create_colors_channel(guild)
        if colors_ch:
            history = [m async for m in colors_ch.history(limit=5)]
            if not any(m.author.id == bot.user.id and m.embeds for m in history):
                c_embed = discord.Embed(
                    title="🎨 Server Name Color Station",
                    description=(
                        "Personalize your username color in chat!\n\n"
                        "Select any **Pro Hex Color** from the dropdown menu below to change your name color.\n\n"
                        "💡 *You can also type `.color #HEXCODE` in `#bot-commands` for custom colors.*"
                    ),
                    color=discord.Color.gold()
                )
                c_embed.set_footer(text=f"{guild.name} Customization • {BOT_COMPANY_NAME}")
                await colors_ch.send(embed=c_embed, view=ColorSelectView())

        announcement_ch = await get_or_create_announcement_channel(guild)

        restored_count = await restore_data_from_channel(guild)
        if restored_count and announcement_ch:
            await announcement_ch.send(f"♻️ **Database Recovered**: Loaded profiles for **{restored_count} members**.")
        else:
            for member in guild.members:
                if not member.bot and member.id not in user_levels[guild.id]:
                    user_levels[guild.id][member.id] = 1
                    user_xp[guild.id][member.id] = 0

        await publish_or_update_botcommands(guild, update_note="System rebooted online. Modules synchronized.")

@bot.event
async def on_guild_join(guild: discord.Guild):
    bot.add_view(WelcomeProfileView(guild.id))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(f"{error}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Access Denied**: Insufficient Discord permissions.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Missing Argument**: `{error.param.name}` is required.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ **Invalid Parameter**: Check user mentions, roles, or integer inputs.")
    else:
        print(f"Unhandled Error on command {ctx.command}: {error}")

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return

    guild = member.guild
    gid = guild.id

    user_levels[gid][member.id] = 1
    user_xp[gid][member.id] = 0
    await update_member_level_role(member, 1)

    onboard_view = WelcomeProfileView(guild_id=guild.id)

    dm_embed = discord.Embed(
        title=f"🌸 Welcome to {guild.name}!",
        description=(
            f"Hey {member.name}, welcome! 🎉\n\n"
            "To help everyone address you properly, please take 5 seconds to set up your server profile:\n\n"
            "• **Preferred Name / Nickname**\n"
            "• **Gender / Pronoun Role**\n\n"
            "Click the button below to fill out your details:"
        ),
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    dm_embed.set_thumbnail(url=member.display_avatar.url)
    dm_embed.set_footer(text=f"{guild.name} Onboarding • {BOT_COMPANY_NAME}")

    dm_delivered = False
    try:
        await member.send(embed=dm_embed, view=onboard_view)
        dm_delivered = True
    except (discord.Forbidden, discord.HTTPException):
        dm_delivered = False

    welcome_ch = await get_or_create_welcome_channel(guild)
    if welcome_ch:
        total_members = guild.member_count
        public_embed = discord.Embed(
            title=f"👋 Welcome to {guild.name}!",
            description=(
                f"Welcome {member.mention}! You are member **#{total_members}**.\n\n"
                + ("📬 **Check your DMs!** We sent you a quick setup prompt." if dm_delivered 
                   else "⚠️ **Your DMs are closed!** Click the button below to set up your nickname and gender:")
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        public_embed.set_thumbnail(url=member.display_avatar.url)
        public_embed.set_footer(text=f"Welcome • {BOT_COMPANY_NAME}")

        try:
            await welcome_ch.send(
                content=f"Welcome {member.mention}!",
                embed=public_embed,
                view=onboard_view
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

@bot.event
async def on_message(message: discord.Message):
    if not message.guild:
        return

    if MAINTENANCE_MODE:
        if message.author.id == message.guild.owner_id or message.author.guild_permissions.administrator:
            await bot.process_commands(message)
        return

    gid = message.guild.id
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()

    if message.author.id == DISBOARD_BOT_ID:
        bump_ch = await get_or_create_bump_channel(message.guild)
        if bump_ch and message.channel.id == bump_ch.id and message.embeds:
            for embed in message.embeds:
                desc = (embed.description or "").lower()
                if "bump done" in desc:
                    last_bump = last_bump_times[gid]
                    elapsed = now_ts - last_bump

                    if last_bump != 0 and elapsed < BUMP_COOLDOWN_SECONDS:
                        diff = int(BUMP_COOLDOWN_SECONDS - elapsed)
                        m, s = divmod(diff, 60)
                        h, m = divmod(m, 60)
                        await message.channel.send(f"⚠️ **Disboard Cooldown Active**: Next bump ready in **{h}h {m}m**.")
                        return

                    last_bump_times[gid] = now_ts
                    bumper = message.guild.get_member(message.interaction.user.id) if message.interaction and message.interaction.user else None
                    cheer = random.choice(CUTE_BUMP_MESSAGES)

                    if bumper:
                        await add_xp(bumper, 200)
                        await message.channel.send(f"Thank you for bumping, {bumper.mention}! (+200 XP)\n*{cheer}*")
                    else:
                        await message.channel.send(f"Server bumped successfully! (+200 XP)\n*{cheer}*")

                    if gid in active_bump_tasks:
                        active_bump_tasks[gid].cancel()
                    active_bump_tasks[gid] = asyncio.create_task(schedule_bump_reminders(message.guild, bump_ch))
        return

    if message.author.bot:
        return

    uid = message.author.id
    current_time = asyncio.get_event_loop().time()

    if uid in afk_users[gid] and not message.content.startswith(".afk"):
        del afk_users[gid][uid]
        welcome_line = random.choice(AFK_WELCOME_BACK_MESSAGES).format(mention=message.author.mention)
        
        if uid in afk_mentions[gid] and afk_mentions[gid][uid]:
            missed = "\n".join(afk_mentions[gid][uid][-5:])
            welcome_line += f"\n\n📬 **Here are the pings you missed (Last 5):**\n{missed}"
            del afk_mentions[gid][uid]

        await message.channel.send(welcome_line)

    last_xp = last_xp_awarded[gid].get(uid, 0.0)
    if current_time - last_xp >= XP_COOLDOWN_SECONDS:
        last_xp_awarded[gid][uid] = current_time
        earned_xp = random.randint(MIN_XP_PER_MSG, MAX_XP_PER_MSG)
        await add_xp(message.author, earned_xp)

    if message.mentions:
        for target in message.mentions:
            if target.id in afk_users[gid] and target.id != uid:
                user_reason = afk_users[gid][target.id]
                afk_mentions[gid][target.id].append(
                    f"• {message.author.display_name} in {message.channel.mention}: {message.clean_content}"
                )
                ping_notice = random.choice(AFK_PING_TEMPLATES).format(
                    name=f"**{target.display_name}**",
                    reason=user_reason
                )
                await message.channel.send(ping_notice)

    await bot.process_commands(message)

# ==========================================
# COMMANDS: BROADCASTS & TEAM NEWS
# ==========================================
@bot.command(name="announce", aliases=["broadcast", "nounce"])
@is_admin_or_owner()
async def make_announcement(ctx, *, content: str):
    """Broadcasts an official server announcement to #announcements."""
    ann_ch = await get_or_create_announcement_channel(ctx.guild)
    if not ann_ch:
        return await ctx.send("❌ Could not locate or create the `#announcements` channel.")

    clean_text = content.strip()
    ping_header = ""

    if clean_text.startswith("@everyone"):
        ping_header = "@everyone"
        clean_text = clean_text[9:].strip()
    elif clean_text.startswith("@here"):
        ping_header = "@here"
        clean_text = clean_text[5:].strip()

    if not clean_text:
        return await ctx.send("❌ Please provide a message to announce.")

    embed = discord.Embed(
        title="📢 Official Server Announcement",
        description=clean_text,
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )

    if ctx.guild.icon:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        embed.set_thumbnail(url=ctx.guild.icon.url)
    else:
        embed.set_author(name=ctx.guild.name)

    embed.set_footer(
        text=f"Announced by {ctx.author.display_name} • {BOT_COMPANY_NAME}",
        icon_url=ctx.author.display_avatar.url
    )

    if ctx.message.attachments:
        first_att = ctx.message.attachments[0]
        if any(first_att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
            embed.set_image(url=first_att.url)

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    try:
        await ann_ch.send(
            content=ping_header if ping_header else None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True)
        )
        confirm = await ctx.send(f"✅ **Announcement broadcasted successfully to** {ann_ch.mention}!")
        await asyncio.sleep(4)
        try:
            await confirm.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
    except (discord.Forbidden, discord.HTTPException):
        await ctx.send("❌ Failed to broadcast. Ensure the bot has `Send Messages` and `Mention Everyone` permissions.")

@bot.command(name="botupdate", aliases=["newfunction", "teamnews", "featuredrop"])
@is_admin_or_owner()
async def announce_new_function(ctx, *, details: str):
    """Broadcasts a new bot function or update into #team-news."""
    news_ch = await get_or_create_team_news_channel(ctx.guild)
    if not news_ch:
        return await ctx.send("❌ Could not locate or create the `#team-news` channel.")

    if "|" in details:
        feature_name, instructions = [part.strip() for part in details.split("|", 1)]
    else:
        feature_name = "New System Upgrade"
        instructions = details.strip()

    embed = discord.Embed(
        title="🚀 New Bot Function Deployed",
        description=f"A new system capability has been deployed to {bot.user.mention}!",
        color=discord.Color.teal(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🔧 Function / Feature", value=f"**{feature_name}**", inline=False)
    embed.add_field(name="📋 Details & Staff Usage", value=instructions, inline=False)

    if ctx.message.attachments:
        att = ctx.message.attachments[0]
        if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
            embed.set_image(url=att.url)

    embed.set_footer(
        text=f"Added by {ctx.author.display_name} • {BOT_COMPANY_NAME}",
        icon_url=ctx.author.display_avatar.url
    )

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    await news_ch.send(
        content="📢 **Staff Update:** A new function has been added to the bot. Please review the details below:",
        embed=embed
    )

    confirm = await ctx.send(f"✅ **Feature update dispatched to** {news_ch.mention}!")
    await asyncio.sleep(4)
    try:
        await confirm.delete()
    except (discord.NotFound, discord.Forbidden):
        pass

@bot.command(name="teamrules", aliases=["staffrules", "postteamrules"])
@is_admin_or_owner()
async def post_team_rules_cmd(ctx):
    """Generates or updates the official Team Conduct and Rules message in #team-rules."""
    status_msg = await ctx.send("⏳ Setting up `#team-rules` and publishing guidelines...")
    sent_msg = await publish_or_update_team_rules(ctx.guild)
    if sent_msg:
        await status_msg.edit(content=f"✅ **Team rules published successfully in** {sent_msg.channel.mention}!")
    else:
        await status_msg.edit(content="❌ Failed to initialize `#team-rules`. Check bot permissions.")

# ==========================================
# COMMANDS: BIRTHDAY ENGINE (#birthdays)
# ==========================================
@bot.command(name="setbirthday", aliases=["setbday"])
async def set_birthday(ctx, date_str: str):
    bday_ch = await get_or_create_birthday_channel(ctx.guild)
    if bday_ch and ctx.channel.id != bday_ch.id:
        return await ctx.send(f"❌ Birthday commands are restricted to {bday_ch.mention}.")

    parsed_date = None
    has_year = False

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed_date = datetime.datetime.strptime(date_str, fmt)
            has_year = True
            break
        except ValueError:
            continue

    if not parsed_date:
        for fmt in ("%d-%m", "%d/%m"):
            try:
                parsed_date = datetime.datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

    if not parsed_date:
        return await ctx.send("❌ **Invalid Format**: Use `DD-MM` or `DD-MM-YYYY` (e.g. `25-12` or `25-12-2004`).")

    gid = ctx.guild.id
    uid = ctx.author.id

    user_birthdays[gid][uid] = {
        "day": parsed_date.day,
        "month": parsed_date.month,
        "year": parsed_date.year if has_year else None
    }

    display = f"{parsed_date.day:02d}/{parsed_date.month:02d}"
    if has_year:
        display += f"/{parsed_date.year}"

    await ctx.send(f"🎂 **Birthday Saved**: Registered {ctx.author.mention}'s birthday as **{display}**!")

@bot.command(name="birthday", aliases=["bday"])
async def view_birthday(ctx, member: discord.Member = None):
    bday_ch = await get_or_create_birthday_channel(ctx.guild)
    if bday_ch and ctx.channel.id != bday_ch.id:
        return await ctx.send(f"❌ Birthday commands are restricted to {bday_ch.mention}.")

    target = member or ctx.author
    bday_data = user_birthdays[ctx.guild.id].get(target.id)

    if not bday_data:
        msg = "You haven't set a birthday yet! Use `.setbirthday DD-MM`." if target == ctx.author else f"{target.display_name} hasn't registered a birthday."
        return await ctx.send(f"ℹ️ {msg}")

    display = f"{bday_data['day']:02d}/{bday_data['month']:02d}"
    if bday_data.get("year"):
        display += f"/{bday_data['year']}"

    await ctx.send(f"🎈 {target.mention}'s birthday is set for **{display}**.")

# ==========================================
# COMMANDS: LEVELING & TENURE / OG SUITE
# ==========================================
@bot.command(name="level", aliases=["rank"])
async def check_level(ctx, member: discord.Member = None):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Please use {cmd_ch.mention} to check levels.")

    target = member or ctx.author
    gid = ctx.guild.id
    lvl = user_levels[gid].get(target.id, 1)
    xp = user_xp[gid].get(target.id, 0)
    needed = get_xp_for_level(lvl)
    tier_data = get_tier_info_for_level(lvl)

    if lvl >= MAX_LEVEL:
        bar = "🟩" * 10
        progress_text = "Max Level Reached"
    else:
        pct = min(int((xp / needed) * 100), 100)
        filled = min(int(pct / 10), 10)
        bar = "🟩" * filled + "⬛" * (10 - filled)
        progress_text = f"{xp:,} / {needed:,} XP ({pct}%)"

    embed = discord.Embed(
        title=f"📊 Rank Overview — {target.display_name}",
        color=tier_data["color"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Current Level", value=f"**Level {lvl}**", inline=True)
    embed.add_field(name="Active Tier", value=f"**{tier_data['name']}**", inline=True)
    embed.add_field(name="Progress to Next Tier", value=f"`{bar}`\n{progress_text}", inline=False)
    embed.set_footer(text=f"{ctx.guild.name} Progression • {BOT_COMPANY_NAME}")

    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
async def show_leaderboard(ctx):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Please use {cmd_ch.mention} to view the leaderboard.")

    gid = ctx.guild.id
    sorted_players = sorted(
        user_levels[gid].items(),
        key=lambda entry: (entry[1], user_xp[gid].get(entry[0], 0)),
        reverse=True
    )[:10]

    if not sorted_players:
        return await ctx.send("📋 No progression records established.")

    embed = discord.Embed(title="🏆 Server Experience Leaderboard", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    for rank, (uid, lvl) in enumerate(sorted_players, start=1):
        member = ctx.guild.get_member(uid)
        username = member.display_name if member else f"ID: {uid}"
        xp = user_xp[gid].get(uid, 0)
        tier = get_tier_info_for_level(lvl)["name"]
        embed.add_field(name=f"#{rank} {username}", value=f"Level {lvl} ({tier}) • {xp} XP", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="tenure", aliases=["joindate", "joined"])
async def check_tenure(ctx, member: discord.Member = None):
    target = member or ctx.author
    if not target.joined_at:
        return await ctx.send("❌ Unable to retrieve member join timestamp.")

    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - target.joined_at
    total_days = delta.days
    years, remaining_days = divmod(total_days, 365)
    months = remaining_days // 30
    days = remaining_days % 30

    joined_unix = int(target.joined_at.timestamp())

    tenure_parts = []
    if years > 0:
        tenure_parts.append(f"**{years}** year(s)")
    if months > 0:
        tenure_parts.append(f"**{months}** month(s)")
    tenure_parts.append(f"**{days}** day(s)")
    tenure_str = ", ".join(tenure_parts)

    embed = discord.Embed(
        title=f"📜 Member Tenure & Records: {target.display_name}",
        color=target.color if target.color != discord.Color.default() else discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="📅 Official Join Date", value=f"<t:{joined_unix}:F>\n(<t:{joined_unix}:R>)", inline=False)
    embed.add_field(name="⏳ Time in Server", value=f"{tenure_str} (Total: **{total_days} days**)", inline=False)

    if total_days >= OG_DAYS_REQUIRED:
        og_status = f"✅ **Unlocked** (Holds `{OG_ROLE_NAME}` Status)"
    else:
        days_left = OG_DAYS_REQUIRED - total_days
        og_status = f"⏳ **In Progress** ({days_left} days remaining until `{OG_ROLE_NAME}`)"
    embed.add_field(name="👑 OG / Loyalty Status", value=og_status, inline=False)

    is_staff = any(r.name.lower() in RESTRICTED_ADMIN_ROLES for r in target.roles)
    if is_staff or target.id == ctx.guild.owner_id:
        if total_days >= STAFF_PROMO_MIN_DAYS:
            staff_promo_status = f"🟢 **Eligible for Promotion Assessment** (Tenure exceeds {STAFF_PROMO_MIN_DAYS} days)"
        else:
            days_needed = STAFF_PROMO_MIN_DAYS - total_days
            staff_promo_status = f"🟡 **Probationary Period** ({days_needed} more days required for review)"
        embed.add_field(name="🛡️ Staff Promotion Evaluation", value=staff_promo_status, inline=False)

    embed.set_footer(text=f"Requested by {ctx.author.display_name} • {BOT_COMPANY_NAME}")
    await ctx.send(embed=embed)

@bot.group(name="old", aliases=["og"], invoke_without_command=True)
async def old_group(ctx, member: discord.Member = None):
    target = member or ctx.author
    if not target.joined_at:
        return await ctx.send("❌ Could not determine member join timestamp.")

    now = datetime.datetime.now(datetime.timezone.utc)
    days_in_server = (now - target.joined_at).days
    og_role = discord.utils.get(ctx.guild.roles, name=OG_ROLE_NAME)
    has_role = og_role in target.roles if og_role else False

    embed = discord.Embed(
        title=f"📜 Old Member Status: {target.display_name}",
        color=discord.Color.magenta() if has_role else discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="📅 Joined On", value=f"<t:{int(target.joined_at.timestamp())}:D> (<t:{int(target.joined_at.timestamp())}:R>)", inline=False)
    embed.add_field(name="⏳ Total Tenure", value=f"**{days_in_server}** / **{OG_DAYS_REQUIRED}** days required", inline=True)
    embed.add_field(name="👑 OG Status", value="✅ **Active Old Member**" if has_role else ("🟡 **Eligible (Role Missing)**" if days_in_server >= OG_DAYS_REQUIRED else "⏳ **In Progress**"), inline=True)
    embed.set_footer(text=f"Use .old auto to sync all server members • {BOT_COMPANY_NAME}")
    await ctx.send(embed=embed)

@old_group.command(name="auto", aliases=["sync", "scan"])
@is_admin_or_higher()
async def old_auto_sync(ctx):
    status_msg = await ctx.send("🔍 **Scanning server roster for Old (OG) members (365+ days)... Please wait.**")
    guild = ctx.guild
    og_role = await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.magenta())

    if not og_role:
        return await status_msg.edit(content="❌ Could not find or initialize the `OG` role.")
    if guild.me.top_role <= og_role:
        return await status_msg.edit(content="❌ Hierarchy Error: Bot role must be higher than the `OG` role.")

    now = datetime.datetime.now(datetime.timezone.utc)
    newly_awarded = 0
    total_eligible = 0

    for member in guild.members:
        if member.bot or not member.joined_at:
            continue

        days = (now - member.joined_at).days
        if days >= OG_DAYS_REQUIRED:
            total_eligible += 1
            if og_role not in member.roles:
                try:
                    await member.add_roles(og_role, reason="Auto-Scan: Server tenure milestone (365+ days)")
                    newly_awarded += 1
                    await asyncio.sleep(0.25)
                except (discord.Forbidden, discord.HTTPException):
                    continue

    embed = discord.Embed(
        title="⚡ Auto-Sync Complete: Old (OG) Members",
        description=f"Completed automated audit of all members in **{guild.name}**.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🎯 Tenure Threshold", value=f"**{OG_DAYS_REQUIRED} Days** (1 Year)", inline=True)
    embed.add_field(name="👥 Total Old Members", value=f"**{total_eligible}** members", inline=True)
    embed.add_field(name="✨ Roles Auto-Assigned", value=f"**{newly_awarded}** new members", inline=True)
    embed.set_footer(text=f"Auto Audit executed by {ctx.author.display_name}")

    await status_msg.edit(content=None, embed=embed)

@old_group.command(name="manual", aliases=["add", "give"])
@is_admin_or_higher()
async def old_manual_grant(ctx, member: discord.Member, *, reason: str = "Manual staff override"):
    og_role = await ensure_role_exists(ctx.guild, OG_ROLE_NAME, discord.Color.magenta())
    if not og_role:
        return await ctx.send("❌ Could not locate or create the `OG` role.")
    if ctx.guild.me.top_role <= og_role:
        return await ctx.send("❌ Hierarchy Error: Bot role must be higher than the `OG` role.")
    if og_role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already holds the **{OG_ROLE_NAME}** role.")

    try:
        await member.add_roles(og_role, reason=f"Manual OG Grant by {ctx.author}: {reason}")
        await ctx.send(f"👑 **Manual Grant**: Assigned **{OG_ROLE_NAME}** role to {member.mention}.\n> *Reason: {reason}*")
    except discord.Forbidden:
        await ctx.send("❌ Discord rejected role assignment. Check bot permissions.")

@old_group.command(name="remove", aliases=["revoke"])
@is_admin_or_higher()
async def old_manual_remove(ctx, member: discord.Member, *, reason: str = "Manual staff removal"):
    og_role = discord.utils.get(ctx.guild.roles, name=OG_ROLE_NAME)
    if not og_role or og_role not in member.roles:
        return await ctx.send(f"⚠️ {member.mention} does not hold the **{OG_ROLE_NAME}** role.")
    if ctx.guild.me.top_role <= og_role:
        return await ctx.send("❌ Hierarchy Error: Bot role must be higher than the `OG` role.")

    try:
        await member.remove_roles(og_role, reason=f"Manual OG Revocation by {ctx.author}: {reason}")
        await ctx.send(f"🗑️ **Revoked**: Removed **{OG_ROLE_NAME}** role from {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ Discord rejected role removal.")

@old_group.command(name="list")
async def old_list(ctx):
    og_role = discord.utils.get(ctx.guild.roles, name=OG_ROLE_NAME)
    if not og_role:
        return await ctx.send("❌ The `OG` role does not exist on this server yet.")

    members = [m.mention for m in og_role.members if not m.bot]
    total = len(members)

    if total == 0:
        return await ctx.send(f"ℹ️ No members currently hold the `{OG_ROLE_NAME}` role. Run `.old auto` to scan.")

    summary = "\n".join(members[:25])
    if total > 25:
        summary += f"\n*...and {total - 25} more.*"

    embed = discord.Embed(
        title=f"👑 Server Old (OG) Members ({total})",
        description=summary,
        color=discord.Color.magenta(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Total Veterans: {total} • {BOT_COMPANY_NAME}")
    await ctx.send(embed=embed)

@bot.command(name="addxp")
@is_admin_or_higher()
async def give_xp(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ XP quantity must be positive.")
    await add_xp(member, amount)
    await ctx.send(f"✨ Transferred **{amount} XP** to {member.mention}.")

@bot.command(name="setlevel")
@is_admin_or_higher()
async def set_user_level(ctx, member: discord.Member, level: int):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Hierarchy violation: Target possesses equal or higher rank.")
    if level < 1 or level > MAX_LEVEL:
        return await ctx.send(f"❌ Level boundary: **1 to {MAX_LEVEL}**.")

    gid = ctx.guild.id
    user_levels[gid][member.id] = level
    user_xp[gid][member.id] = 0
    await update_member_level_role(member, level)
    await ctx.send(f"⚙️ Overrode {member.mention} progression to **Level {level}**.")

@bot.command(name="synclevels")
@is_admin_or_higher()
async def sync_levels(ctx):
    synced = 0
    for member in ctx.guild.members:
        if not member.bot:
            lvl = user_levels[ctx.guild.id].get(member.id, 1)
            await update_member_level_role(member, lvl)
            synced += 1
            await asyncio.sleep(0.1)
    await ctx.send(f"✅ Synchronized level tier roles for **{synced} member(s)**.")

# ==========================================
# COMMANDS: INTERACTIVE PANELS (TICKETS/CONFESSIONS/COLORS/WELCOME)
# ==========================================
@bot.command(name="ticketpanel")
@is_admin_or_owner()
async def post_ticket_panel(ctx):
    embed = discord.Embed(
        title="📩 Server Support & Inquiries",
        description=(
            "Need assistance, want to file a report, or interested in joining our staff team? "
            "Select an option below to open a private ticket with our leadership team:\n\n"
            "💼 **Join Team** — Apply for moderation or staff positions\n"
            "⚠️ **File Complaint** — Privately report a user, issue, or rule violation\n"
            "❓ **General Support** — Questions, role assistance, or other inquiries\n\n"
            "*Please open only one ticket at a time and avoid opening tickets without a clear reason.*"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"{ctx.guild.name} Helpdesk • {BOT_COMPANY_NAME}")
    await ctx.send(embed=embed, view=TicketLauncherView())
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

@bot.command(name="createticket", aliases=["openticket", "newticket"])
async def manual_create_ticket(ctx, member: discord.Member = None, *, reason: str = "General Inquiry"):
    target_user = member if (member and ctx.author.guild_permissions.administrator) else ctx.author
    status_msg = await ctx.send(f"⏳ Creating ticket channel for {target_user.mention}...")
    ticket_ch = await build_and_send_ticket(ctx.guild, target_user, topic=reason)
    if ticket_ch:
        await status_msg.edit(content=f"✅ **Ticket Created!** Go to {ticket_ch.mention}.")
    else:
        await status_msg.edit(content="❌ Failed to create ticket. Check bot permissions.")

@bot.command(name="confesspanel")
@is_admin_or_owner()
async def post_confession_panel(ctx):
    confession_ch = await get_or_create_confession_channel(ctx.guild)
    if not confession_ch:
        return await ctx.send("❌ Unable to access or create the confession channel.")

    embed = discord.Embed(
        title="📮 Anonymous Confessions",
        description=(
            "Click the button below to submit a secret confession.\n\n"
            "🔒 **Privacy Guaranteed:**\n"
            "• Your name and avatar are never recorded.\n"
            "• Submissions are processed via secure pop-up dialogs.\n"
            "• Message logger bots cannot see what you write."
        ),
        color=discord.Color.magenta()
    )
    embed.set_footer(text="Keep it respectful and within server guidelines.")
    await confession_ch.send(embed=embed, view=ConfessionButtonView())
    if ctx.channel.id != confession_ch.id:
        await ctx.send(f"✅ Confession panel placed in {confession_ch.mention}.")

@bot.command(name="confess")
async def manual_confess(ctx, *, confession_text: str = None):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    confession_ch = await get_or_create_confession_channel(ctx.guild)
    if not confession_ch:
        return

    if not confession_text:
        return await ctx.author.send(f"ℹ️ Use `.confess <message>` or click the button in {confession_ch.mention}.")

    gid = ctx.guild.id
    confession_counters[gid] += 1
    num = confession_counters[gid]

    embed = discord.Embed(
        title=f"💌 Anonymous Confession #{num}",
        description=confession_text,
        color=discord.Color.from_rgb(255, 105, 180),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text="100% Anonymous Submission • Server Confessions")
    await confession_ch.send(embed=embed)

@bot.command(name="colorpanel", aliases=["colourpanel", "colourspanel"])
@is_admin_or_owner()
async def post_color_panel(ctx):
    colors_ch = await get_or_create_colors_channel(ctx.guild)
    if not colors_ch:
        return await ctx.send("❌ Could not locate or create the `#colours` channel.")

    embed = discord.Embed(
        title="🎨 Server Name Color Station",
        description=(
            "Personalize your username color in chat!\n\n"
            "Use the dropdown menu below to equip any of our featured **Pro Hex** colors or remove your active color at any time.\n\n"
            "**Available Colors:**\n"
            "🔴 `Pro Hex Red`\n"
            "🟢 `Pro Hex Green`\n"
            "🔵 `Pro Hex Blue`\n"
            "🌸 `Pro Hex Pink`\n"
            "🟡 `Pro Hex Yellow`\n"
            "🟠 `Pro Hex Orange`\n\n"
            "💡 *Looking for a custom color? Use `.color #HEXCODE` in `#bot-commands`!*"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"{ctx.guild.name} Styling • {BOT_COMPANY_NAME}")
    await colors_ch.send(embed=embed, view=ColorSelectView())
    if ctx.channel.id != colors_ch.id:
        await ctx.send(f"✅ Color panel placed in {colors_ch.mention}.")

@bot.command(name="welcomesetup", aliases=["postwelcome"])
@is_admin_or_owner()
async def post_welcome_panel(ctx):
    welcome_ch = await get_or_create_welcome_channel(ctx.guild)
    if not welcome_ch:
        return await ctx.send("❌ Could not locate or create the `#welcome` channel.")

    embed = discord.Embed(
        title="🌟 Welcome & Profile Setup Station",
        description=(
            "Welcome to all new members!\n\n"
            "Please click the **Set Name & Gender** button below to introduce yourself:\n"
            "• Sets your server nickname\n"
            "• Assigns your preferred gender/pronoun role\n\n"
            "🔒 *Your submission is processed privately and can be updated anytime.*"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"{ctx.guild.name} Onboarding • {BOT_COMPANY_NAME}")

    await welcome_ch.send(embed=embed, view=WelcomeProfileView(ctx.guild.id))
    if ctx.channel.id != welcome_ch.id:
        await ctx.send(f"✅ Onboarding card posted in {welcome_ch.mention}.")

@bot.command(name="color", aliases=["colour", "setcolor"])
async def set_color(ctx, *, color_input: str):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Color roles can only be chosen in {cmd_ch.mention}.")

    author = ctx.author
    color_input = color_input.strip()

    if color_input.lower() in ["remove", "clear", "none", "reset"]:
        _, msg = await remove_member_hex_color(author)
        return await ctx.send(msg)

    for name, col in PRO_HEX_COLORS.items():
        if color_input.lower() in name.lower():
            _, msg = await apply_member_hex_color(author, name, col)
            return await ctx.send(msg)

    clean_hex = color_input.lstrip("#")
    if len(clean_hex) == 6 and all(c in "0123456789abcdefABCDEF" for c in clean_hex):
        try:
            hex_val = int(clean_hex, 16)
            role_name = f"Color-#{clean_hex.upper()}"
            _, msg = await apply_member_hex_color(author, role_name, discord.Color(hex_val))
            return await ctx.send(msg)
        except ValueError:
            return await ctx.send("❌ Invalid hex format.")

    options = ", ".join([k.replace("Pro Hex ", "") for k in PRO_HEX_COLORS.keys()])
    await ctx.send(f"❌ Invalid color. Choose a preset (`{options}`) or enter a valid hex (e.g., `.color #FF5733`).")

# ==========================================
# COMMANDS: STAFF MANAGEMENT & RESIGNATION
# ==========================================
@bot.command(name="promote")
@is_admin_or_owner()
async def promote_staff(ctx, member: discord.Member, *, new_role_name: str):
    target_role = discord.utils.get(ctx.guild.roles, name=new_role_name)
    if not target_role:
        return await ctx.send(f"❌ Role `{new_role_name}` not found.")
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Action rejected: Target holds equal or higher role.")
    if ctx.guild.me.top_role <= target_role:
        return await ctx.send("❌ Hierarchy conflict: Bot role is lower than target role.")
    if target_role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already holds the **{target_role.name}** role.")

    await member.add_roles(target_role, reason=f"Promoted by {ctx.author}")
    await ctx.send(f"🎉 **PROMOTION**: {member.mention} promoted to **{target_role.name}** by {ctx.author.mention}!")

@bot.command(name="resign")
@commands.guild_only()
async def resign_staff(ctx, *, reason: str = "Voluntary resignation"):
    author = ctx.author
    guild = ctx.guild
    held_staff_roles = [r for r in author.roles if r.name.lower() in RESTRICTED_ADMIN_ROLES]

    if not held_staff_roles:
        return await ctx.send("❌ You do not currently hold any designated staff roles to resign from.")

    highest_target_role = max(held_staff_roles, key=lambda r: r.position)
    if guild.me.top_role <= highest_target_role:
        return await ctx.send("❌ Hierarchy Conflict: My highest role is below your staff role. Contact Server Owner.")

    role_names = ", ".join(f"`{r.name}`" for r in held_staff_roles)

    view = ResignConfirmView(ctx)
    embed = discord.Embed(
        title="⚠️ Confirm Staff Resignation",
        description=(
            f"{author.mention}, are you sure you want to step down?\n\n"
            f"**Roles to be removed:** {role_names}\n"
            f"**Reason stated:** *{reason}*"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Prompt expires in 30 seconds.")
    prompt_msg = await ctx.send(embed=embed, view=view)

    await view.wait()

    if view.value is None:
        for child in view.children:
            child.disabled = True
        return await prompt_msg.edit(content="⏱️ **Confirmation Timed Out**: Resignation aborted.", embed=None, view=view)

    if not view.value:
        return

    try:
        await author.remove_roles(*held_staff_roles, reason=f"Staff Resignation: {reason}")
    except discord.Forbidden:
        return await prompt_msg.edit(content="❌ Discord rejected role removal due to permission constraints.", view=None)

    await prompt_msg.edit(content=f"🫡 {author.mention} has officially stepped down from: {role_names}.", embed=None, view=None)

    announcement_ch = await get_or_create_announcement_channel(guild)
    if announcement_ch:
        ann_embed = discord.Embed(
            title="📋 Staff Resignation",
            description=f"{author.mention} has stepped down from their staff position.\n\n**Relinquished Roles:** {role_names}\n**Reason:** *{reason}*",
            color=discord.Color.light_grey(),
            timestamp=discord.utils.utcnow()
        )
        ann_embed.set_thumbnail(url=author.display_avatar.url)
        ann_embed.set_footer(text=f"{guild.name} Staff Departures")
        await announcement_ch.send(embed=ann_embed)

@bot.command(name="authority")
@is_admin_or_owner()
async def grant_authority(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Authority")
    if not role:
        return await ctx.send("❌ Role `Authority` doesn't exist. Run `.autorole_setup` first.")
    if role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already has `Authority`.")
    await member.add_roles(role)
    await ctx.send(f"✅ Assigned **Authority** to {member.mention}.")

@bot.command(name="assign")
@is_admin_or_owner()
async def assign_role(ctx, member: discord.Member, *, role: discord.Role):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Action rejected: Target holds equal or higher role.")
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ Cannot assign a role positioned above or equal to bot.")
    if role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already holds `{role.name}`.")
    await member.add_roles(role, reason=f"Assigned by {ctx.author}")
    await ctx.send(f"✅ Assigned **{role.name}** to {member.mention}.")

@bot.command(name="revoke")
@is_admin_or_owner()
async def revoke_role(ctx, member: discord.Member, *, role: discord.Role):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Action rejected: Target holds equal or higher role.")
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ Cannot revoke a role positioned above bot.")
    if role not in member.roles:
        return await ctx.send(f"⚠️ {member.mention} does not have `{role.name}`.")
    await member.remove_roles(role, reason=f"Revoked by {ctx.author}")
    await ctx.send(f"🗑️ Revoked **{role.name}** from {member.mention}.")

@bot.command(name="addrole")
@is_admin_or_owner()
async def add_role_by_name(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` not found.")
    await assign_role(ctx, member, role=role)

@bot.command(name="removerole")
@is_admin_or_owner()
async def remove_role_by_name(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` not found.")
    await revoke_role(ctx, member, role=role)

@bot.group(name="role", invoke_without_command=True)
@is_admin_or_owner()
async def role_group(ctx):
    await ctx.send("Subcommands: `.role addall <Role>`, `.role removeall <Role>`, `.role members <Role>`.")

@role_group.command(name="addall")
@is_admin_or_owner()
async def add_role_to_all(ctx, *, role: discord.Role):
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ Role position exceeds bot hierarchy boundaries.")

    status = await ctx.send(f"Applying `{role.name}` to all non-bot members... Please wait.")
    count = 0
    for member in ctx.guild.members:
        if not member.bot and role not in member.roles:
            try:
                await member.add_roles(role, reason="Mass Role Add")
                count += 1
                await asyncio.sleep(0.3)
            except (discord.Forbidden, discord.HTTPException):
                continue
    await status.edit(content=f"✅ Completed: Added `{role.name}` to **{count}** members.")

@role_group.command(name="removeall")
@is_admin_or_owner()
async def remove_role_from_all(ctx, *, role: discord.Role):
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ Role position exceeds bot hierarchy boundaries.")

    status = await ctx.send(f"Removing `{role.name}` from members... Please wait.")
    count = 0
    for member in list(role.members):
        try:
            await member.remove_roles(role, reason="Mass Role Remove")
            count += 1
            await asyncio.sleep(0.3)
        except (discord.Forbidden, discord.HTTPException):
            continue
    await status.edit(content=f"✅ Completed: Removed `{role.name}` from **{count}** members.")

@role_group.command(name="members")
@is_admin_or_higher()
async def list_role_members(ctx, *, role: discord.Role):
    members = [f"{m.name} ({m.mention})" for m in role.members if not m.bot]
    total = len(members)

    if total == 0:
        return await ctx.send(f"No non-bot members hold `{role.name}`.")

    summary = "\n".join(members[:20])
    if total > 20:
        summary += f"\n*...and {total - 20} more.*"

    embed = discord.Embed(title=f"Members with {role.name} ({total})", description=summary, color=role.color)
    await ctx.send(embed=embed)

@bot.command(name="autorole_setup")
@is_admin_or_owner()
async def auto_role_setup(ctx):
    status = await ctx.send("⚙️ Configuring Level Tiers, Colors, and Staff Structure...")
    guild = ctx.guild

    for _, tier in LEVEL_TIER_ROLES.items():
        await ensure_role_exists(guild, tier["name"], tier["color"])

    await ensure_role_exists(guild, "BumpPings", discord.Color.gold(), mentionable=True)
    await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.magenta())

    if not discord.utils.get(guild.roles, name="Moderator"):
        perms = discord.Permissions(kick_members=True, manage_messages=True, moderate_members=True, mute_members=True)
        await guild.create_role(name="Moderator", permissions=perms, color=discord.Color.blue())

    if not discord.utils.get(guild.roles, name="Authority"):
        perms = discord.Permissions(kick_members=True, ban_members=True, manage_messages=True, moderate_members=True)
        await guild.create_role(name="Authority", permissions=perms, color=discord.Color.dark_red())

    if not discord.utils.get(guild.roles, name="Head Moderator"):
        perms = discord.Permissions(manage_channels=True, kick_members=True, ban_members=True, manage_messages=True, moderate_members=True, mute_members=True, deafen_members=True, move_members=True)
        await guild.create_role(name="Head Moderator", permissions=perms, color=discord.Color.gold())

    for color_name, color_obj in PRO_HEX_COLORS.items():
        await ensure_role_exists(guild, color_name, color_obj)

    for gender_name, gender_color in GENDER_ROLE_PALETTE.items():
        await ensure_role_exists(guild, gender_name, gender_color)

    await status.edit(content="✅ Auto-Role architecture initialized successfully!")

@bot.command(name="createrole")
@is_admin_or_owner()
async def create_custom_role(ctx, name: str, hex_color: str = "#99AAB5"):
    try:
        clean_hex = hex_color.lstrip("#")
        color = discord.Color(int(clean_hex, 16))
        role = await ctx.guild.create_role(name=name, color=color)
        await ctx.send(f"🎨 Created role **{role.name}** (`#{clean_hex}`).")
    except ValueError:
        await ctx.send("❌ Invalid Hex string. Example: `#FF0000`.")

@bot.command(name="deleterole")
@is_admin_or_owner()
async def delete_custom_role(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` not found.")
    await role.delete()
    await ctx.send(f"🗑️ Deleted role **{role_name}**.")

# ==========================================
# COMMANDS: MODERATION & CHANNEL CONTROLS
# ==========================================
@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason specified"):
    if member.bot:
        return await ctx.send("❌ Bots cannot be placed in timeout.")
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Role hierarchy prevents executing timeout on target.")

    gid = ctx.guild.id
    offense_count = user_mute_counts[gid].get(member.id, 0) + 1
    user_mute_counts[gid][member.id] = offense_count

    durations = {
        1: (datetime.timedelta(hours=1), "1 Hour"),
        2: (datetime.timedelta(hours=6), "6 Hours")
    }
    duration, label = durations.get(offense_count, (datetime.timedelta(hours=12), "12 Hours"))

    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(f"🔇 {member.mention} timed out for **{label}** (Offense #{offense_count}). Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ System failure: Discord rejected timeout permission.")

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Role hierarchy prevents modifying target member.")
    try:
        await member.timeout(None, reason=f"Timeout lifted by {ctx.author}")
        await ctx.send(f"🔊 Restored speak capabilities to {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ System failure: Unable to lift timeout.")

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason specified"):
    if member.bot:
        return await ctx.send("❌ Bots cannot receive formal warnings.")
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Role hierarchy prevents issuing warning to target.")

    gid = ctx.guild.id
    count = user_warnings[gid].get(member.id, 0) + 1
    user_warnings[gid][member.id] = count

    await ctx.send(f"⚠️ Warning registered for {member.mention} (**{count}/3**). Reason: {reason}")

    if count >= 3:
        user_warnings[gid][member.id] = 0
        try:
            await member.ban(reason=f"Reached 3 warnings. Latest: {reason}")
            await ctx.send(f"🔨 **AUTO-BAN EXECUTION**: {member.mention} reached 3 strikes.")
        except discord.Forbidden:
            await ctx.send(f"❌ Failed to auto-ban {member.mention}: Missing clearance.")

@bot.command(name="clearwarns")
@commands.has_permissions(kick_members=True)
async def clear_warns(ctx, member: discord.Member):
    user_warnings[ctx.guild.id][member.id] = 0
    await ctx.send(f"✅ Cleared warnings for {member.mention}.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason specified"):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Role hierarchy check failed.")
    await member.kick(reason=reason)
    await ctx.send(f"👢 Removed {member.mention}. Reason: {reason}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason specified"):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Role hierarchy check failed.")
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention}. Reason: {reason}")

@bot.command(name="purge")
@is_admin_or_higher()
async def purge(ctx, amount: int):
    if not (1 <= amount <= 100):
        return await ctx.send("❌ Purge range limited: 1–100.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    status = await ctx.send(f"🧹 Removed **{len(deleted) - 1}** messages.")
    await asyncio.sleep(3)
    await status.delete()

@bot.command(name="lockdown")
@is_admin_or_higher()
async def lockdown_channel(ctx, channel: discord.TextChannel = None):
    target = channel or ctx.channel
    overwrite = target.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔒 Locked message transmissions in {target.mention}.")

@bot.command(name="unlock")
@is_admin_or_higher()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    target = channel or ctx.channel
    overwrite = target.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔓 Restored message transmissions in {target.mention}.")

@bot.command(name="vc_lock")
@is_admin_or_higher()
async def lock_vc(ctx, channel: discord.VoiceChannel):
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.connect = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔒 **VC Locked**: {channel.name}.")

@bot.command(name="vc_unlock")
@is_admin_or_higher()
async def unlock_vc(ctx, channel: discord.VoiceChannel):
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.connect = None
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔓 **VC Unlocked**: {channel.name}.")

@bot.command(name="vc_mute")
@commands.has_permissions(mute_members=True)
async def vc_mute_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(mute=True)
    await ctx.send(f"🔇 Muted {member.mention} in Voice.")

@bot.command(name="vc_unmute")
@commands.has_permissions(mute_members=True)
async def vc_unmute_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(mute=False)
    await ctx.send(f"🔊 Unmuted {member.mention} in Voice.")

@bot.command(name="vc_deafen")
@commands.has_permissions(deafen_members=True)
async def vc_deafen_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(deafen=True)
    await ctx.send(f"🙉 Deafened {member.mention} in Voice.")

@bot.command(name="vc_undeafen")
@commands.has_permissions(deafen_members=True)
async def vc_undeafen_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(deafen=False)
    await ctx.send(f"🎧 Undeafened {member.mention} in Voice.")

@bot.command(name="vc_move")
@commands.has_permissions(move_members=True)
async def vc_move_user(ctx, member: discord.Member, target_channel: discord.VoiceChannel):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.move_to(target_channel)
    await ctx.send(f"🚚 Moved {member.mention} to **{target_channel.name}**.")

# ==========================================
# COMMANDS: SYSTEM, DATA & MAINTENANCE (ADMIN RESTRICTED)
# ==========================================
@bot.command(name="savedata")
@is_admin_or_owner()
async def force_save(ctx):
    await save_data_to_channel(ctx.guild)
    await ctx.send("💾 State snapshot safely committed to `#bot-memory` (Admin authorized).")

@bot.command(name="backups", aliases=["backuplist"])
@is_admin_or_owner()
async def list_available_backups(ctx):
    memory_channel = await get_or_create_memory_channel(ctx.guild)
    if not memory_channel:
        return await ctx.send("❌ Channel `#bot-memory` not found.")

    found_backups = []
    async for msg in memory_channel.history(limit=100):
        for att in msg.attachments:
            if att.filename.lower().endswith(".json"):
                found_backups.append((msg.created_at, att.filename, msg.author.display_name))

    if not found_backups:
        return await ctx.send("ℹ️ No JSON backup files located in `#bot-memory`.")

    embed = discord.Embed(
        title="💾 Available Server Backups (Admin Restricted)",
        description="To restore a specific backup, run `.restoredata <Index>` (e.g., `.restoredata 0`).",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    for idx, (created, fname, author) in enumerate(found_backups[:10]):
        unix = int(created.timestamp())
        embed.add_field(
            name=f"[{idx}] {fname}",
            value=f"📅 <t:{unix}:f> (<t:{unix}:R>)\n👤 Saved by: `{author}`",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name="cleanbackups", aliases=["purgebackups", "clearbackups"])
@is_admin_or_owner()
async def clean_old_backups(ctx, keep_newest: int = 1):
    status = await ctx.send(f"🧹 Scanning `#bot-memory` to purge old backups (keeping newest: {keep_newest})...")
    deleted = await purge_all_backups(ctx.guild, keep_newest=keep_newest)
    await status.edit(content=f"✅ **Cleaned `#bot-memory`**: Deleted **{deleted}** obsolete backup message(s).")

@bot.command(name="restoredata", aliases=["loaddata", "recoverdata"])
@is_admin_or_owner()
async def force_restore_data(ctx, backup_index: Optional[int] = None):
    uploaded_file = ctx.message.attachments[0] if ctx.message.attachments else None

    target_desc = (
        f"attached file **`{uploaded_file.filename}`**" if uploaded_file
        else (f"backup snapshot at index **`[{backup_index}]`**" if backup_index is not None
        else "the latest valid backup containing progression data in `#bot-memory`")
    )

    view = RestoreConfirmView(ctx)
    embed = discord.Embed(
        title="⚠️ Database Recovery Confirmation (Admin Restricted)",
        description=(
            f"Restoring will overwrite current session data from {target_desc}.\n\n"
            "• All XP, levels, warnings, birthdays, and anniversaries will be updated.\n"
            "• Old, duplicate files in `#bot-memory` will be cleaned.\n\n"
            "Do you want to proceed?"
        ),
        color=discord.Color.red()
    )
    prompt_msg = await ctx.send(embed=embed, view=view)

    await view.wait()
    if not view.value:
        return

    restored_count = await restore_data_from_channel(
        ctx.guild,
        target_attachment=uploaded_file,
        target_index=backup_index
    )

    if restored_count > 0:
        await purge_all_backups(ctx.guild, keep_newest=0)
        await save_data_to_channel(ctx.guild, keep_last=1)

        await prompt_msg.edit(
            content=(
                f"♻️ **State Successfully Restored**: Loaded **{restored_count} member profiles** from {target_desc}.\n"
                "🧹 `#bot-memory` has been purged of obsolete snapshots and synced with a fresh baseline."
            ),
            embed=None,
            view=None
        )
    else:
        await prompt_msg.edit(
            content="❌ **Recovery Failed**: Could not parse any valid progression data from the selected source.",
            embed=None,
            view=None
        )

@bot.group(name="maintenance", invoke_without_command=True)
@is_admin_or_owner()
async def maintenance_group(ctx):
    state = "🔴 **ACTIVE (System Locked)**" if MAINTENANCE_MODE else "🟢 **INACTIVE (Normal Operation)**"
    embed = discord.Embed(
        title="🛠️ Maintenance Mode Control Panel",
        description=f"Current Status: {state}\n\n**Subcommands:**\n• `.maintenance on` — Freeze operations, save data & prepare for update.\n• `.maintenance off` — Resume normal bot functions.",
        color=discord.Color.orange() if MAINTENANCE_MODE else discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed)

@maintenance_group.command(name="on", aliases=["start", "enable"])
@is_admin_or_owner()
async def maintenance_activate(ctx):
    global MAINTENANCE_MODE
    if MAINTENANCE_MODE:
        return await ctx.send("⚠️ Maintenance mode is already active.")

    status_msg = await ctx.send("⏳ **Activating Maintenance Mode... Locking systems and securing backup...**")
    MAINTENANCE_MODE = True

    activity = discord.Activity(type=discord.ActivityType.watching, name="🛠️ System Maintenance & Updates")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)

    if periodic_backup_loop.is_running():
        periodic_backup_loop.cancel()
    if check_birthdays_loop.is_running():
        check_birthdays_loop.cancel()
    if check_anniversaries_loop.is_running():
        check_anniversaries_loop.cancel()

    saved_guilds = 0
    for guild in bot.guilds:
        try:
            await save_data_to_channel(guild)
            saved_guilds += 1
        except Exception as e:
            print(f"Failed backup for {guild.id}: {e}")

    embed = discord.Embed(
        title="🔴 Maintenance Mode Activated",
        description=(
            "The bot has been safely locked for maintenance and system updates.\n\n"
            f"✅ **Database Snapshot:** Committed to `#bot-memory` ({saved_guilds} guild[s]).\n"
            "✅ **Activity Paused:** Member XP, AFK resets, bumps & regular commands frozen.\n"
            "✅ **Background Loops:** Safely halted.\n\n"
            "💡 **You can now safely restart or update the bot code without losing any data.**"
        ),
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Locked by {ctx.author.display_name} • Use '.maintenance off' to resume")
    await status_msg.edit(content=None, embed=embed)

@maintenance_group.command(name="off", aliases=["stop", "disable"])
@is_admin_or_owner()
async def maintenance_deactivate(ctx):
    global MAINTENANCE_MODE
    if not MAINTENANCE_MODE:
        return await ctx.send("⚠️ Maintenance mode is already inactive.")

    MAINTENANCE_MODE = False

    if not periodic_backup_loop.is_running():
        periodic_backup_loop.start()
    if not check_birthdays_loop.is_running():
        check_birthdays_loop.start()
    if not check_anniversaries_loop.is_running():
        check_anniversaries_loop.cancel()

    await bot.change_presence(status=discord.Status.online, activity=None)

    embed = discord.Embed(
        title="🟢 Maintenance Mode Deactivated",
        description="The bot is now fully back online and operating normally.\n\n• Member commands & XP tracking resumed.\n• Automated cycles restarted.\n• Status restored to Online.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Restored by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="restart", aliases=["reboot"])
@is_admin_or_owner()
async def restart_bot(ctx):
    status_msg = await ctx.send("💾 **[1/3] Securing state snapshots in `#bot-memory` across all servers...**")

    save_tasks = [save_data_to_channel(guild) for guild in bot.guilds]
    results = await asyncio.gather(*save_tasks, return_exceptions=True)
    successful_saves = sum(1 for r in results if not isinstance(r, Exception))

    await status_msg.edit(
        content=f"✅ **[2/3] Saved {successful_saves}/{len(bot.guilds)} server snapshot(s)!**\n"
                f"♻️ **[3/3] Closing gateway cleanly & rebooting process... Back in ~3-5 seconds!**"
    )

    await asyncio.sleep(1.5)
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.command(name="botcommands", aliases=["helpmanual", "commandslist"])
@is_admin_or_higher()
async def bot_commands(ctx, *, update_note: str = None):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    note = update_note or f"Manual refresh by {ctx.author.display_name}"
    sent_msg = await publish_or_update_botcommands(ctx.guild, update_note=note)

    if sent_msg and ctx.channel.id != sent_msg.channel.id:
        confirm = await ctx.send(f"✅ **Command directory updated in** {sent_msg.channel.mention} (Old post purged).")
        await asyncio.sleep(4)
        try:
            await confirm.delete()
        except discord.Forbidden:
            pass

@bot.command(name="bump")
async def bump(ctx):
    bump_ch = await get_or_create_bump_channel(ctx.guild)
    if bump_ch and ctx.channel.id != bump_ch.id:
        return await ctx.send(f"❌ `.bump` is restricted to {bump_ch.mention}.")

    gid = ctx.guild.id
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
    last_bump = last_bump_times.get(gid, 0.0)
    elapsed = now_ts - last_bump

    if last_bump != 0 and elapsed < BUMP_COOLDOWN_SECONDS:
        diff = int(BUMP_COOLDOWN_SECONDS - elapsed)
        ready_unix = int(now_ts + diff)
        m, s = divmod(diff, 60)
        h, m = divmod(m, 60)
        return await ctx.send(f"❌ **Cooldown Active**: Wait **{h}h {m}m** before bumping (<t:{ready_unix}:R>).")

    last_bump_times[gid] = now_ts
    await add_xp(ctx.author, 200)

    next_bump_unix = int(now_ts + BUMP_COOLDOWN_SECONDS)
    cheer = random.choice(CUTE_BUMP_MESSAGES)

    await ctx.send(
        f"Thank you for bumping, {ctx.author.mention}! (**+200 XP**)\n"
        f"*{cheer}*\n\n"
        f"⏰ **Next Bump Available:** <t:{next_bump_unix}:t> (<t:{next_bump_unix}:R>)"
    )

    if gid in active_bump_tasks:
        active_bump_tasks[gid].cancel()
    active_bump_tasks[gid] = asyncio.create_task(schedule_bump_reminders(ctx.guild, bump_ch))

@bot.command(name="afk")
async def afk(ctx, *, reason: str = None):
    gid = ctx.guild.id
    uid = ctx.author.id

    chosen_reason = reason.strip() if reason else random.choice(AFK_DEFAULT_REASONS)
    afk_users[gid][uid] = chosen_reason
    afk_mentions[gid][uid].clear()

    embed = discord.Embed(
        title="💤 AFK Status Activated",
        description=(
            f"{ctx.author.mention} is now resting away from chat.\n\n"
            f"📌 **Status / Reason:**\n> *\"{chosen_reason}\"*\n\n"
            "💌 *I'll quietly collect any pings you miss while you're away!*"
        ),
        color=discord.Color.from_rgb(255, 182, 193),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text="Send any message in chat when you return to clear this status!")
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def user_info(ctx, member: discord.Member = None):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Please run this command in {cmd_ch.mention}.")

    target = member or ctx.author
    gid = ctx.guild.id
    lvl = user_levels[gid].get(target.id, 1)
    xp = user_xp[gid].get(target.id, 0)
    warns = user_warnings[gid].get(target.id, 0)
    mutes = user_mute_counts[gid].get(target.id, 0)
    tier = get_tier_info_for_level(lvl)["name"]

    embed = discord.Embed(title=f"👤 User Profile - {target.display_name}", color=target.color, timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Account ID", value=target.id, inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Progression", value=f"Level {lvl} ({tier})\n{xp} Total XP", inline=False)
    embed.add_field(name="Moderation Record", value=f"Warnings: {warns}/3\nTotal Timeouts: {mutes}", inline=False)

    roles = [r.mention for r in target.roles if r.name != "@everyone"]
    embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def server_info(ctx):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Please run this command in {cmd_ch.mention}.")

    guild = ctx.guild
    embed = discord.Embed(title=f"🏰 {guild.name} Server Statistics", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Total Members", value=guild.member_count, inline=True)
    embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=True)
    embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=True)
    embed.add_field(name="Roles Count", value=len(guild.roles), inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="about")
async def about_bot(ctx):
    embed = discord.Embed(title="🤖 System Architecture", color=discord.Color.purple())
    embed.add_field(name="Maintainer", value=BOT_CREATOR_USERNAME, inline=True)
    embed.add_field(name="Lead Engineer", value=BOT_CREATOR_REAL_NAME, inline=True)
    embed.add_field(name="Organization", value=BOT_COMPANY_NAME, inline=True)
    await ctx.send(embed=embed)

# ==========================================
# BOT INITIALIZATION
# ==========================================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable is not set.")
        sys.exit(1)
    bot.run(token)
