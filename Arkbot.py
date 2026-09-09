import asyncio
import io
import json
import os
import re
import time
import traceback
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands, tasks

# ==============================================================================
# 1. SERVER ROLES & PERMISSION MATRIX CONFIGURATION
# ==============================================================================

ADMIN_ROLE_NAME          = "୨୧ Highness ☕⸝⸝﹗"
SUPREME_LEADER_ROLE_NAME = "୨ৎ ˖ 𝑺𝒖𝒑𝒓𝒆𝒎𝒆 𝑳𝒆𝒂𝒅𝒆𝒓"
SUPREME_LEADER_COLOR     = discord.Color.from_rgb(1, 1, 1) # Near-black
AUTHORITY_ROLE_NAME      = "·.✦Authority✦.·"
HEAD_MOD_ROLE_NAME       = "✦•┈๑⋅⋯Head Moderator⋯⋅๑┈•✦"
MOD_ROLE_NAME            = "⋆. 𐙚˚࿔ 𝒎𝒐𝒅𝒆𝒓𝒂𝒕𝒐𝒓 𝜗𝜚˚⋆"
TRIAL_MOD_ROLE_NAME      = "☆⋆｡Trial mod 𖦹°‧★"
TEAM_ROLE_NAME           = "𖦹°‧★ ⏜︵   𝒄𝒉𝒊𝒍𝒍-𝒗𝒆𝒓𝒔𝒆 𝒕𝒆𝒂𝒎    ⏜︵ 𖦹°‧★"

RESTRICTED_ADMIN_ROLES = [
    ADMIN_ROLE_NAME,
    SUPREME_LEADER_ROLE_NAME,
    AUTHORITY_ROLE_NAME,
    HEAD_MOD_ROLE_NAME,
    MOD_ROLE_NAME,
    TRIAL_MOD_ROLE_NAME,
    TEAM_ROLE_NAME
]

OG_ROLE_NAME        = "★.  𝓸𝓰  .★  ˚  ✦  .  ⑅  ."
VETERAN_ROLE_NAME   = "୨ৎ ˖ Veteran"
BOOSTER_ROLE_NAME   = "꒰ . 𖦹 𝖘𝖊𝖗𝖛𝖊𝖗 𝖇𝖔𝖔𝖘𝖙𝖊𝖗 .ᐟ 𖦹 . ꒱"
VANITY_ROLE_NAME    = "🗡 ׄ ݊ ݂ Always-in-nasheֹ  ۪ ֹ ᮫"
BUMP_ROLE_NAME      = "✟ BumpPings"
POLL_ROLE_NAME      = "✟ PollPings"
ROBLOX_ROLE_NAME    = "Roblox Members"

GENDER_ROLES = {
    "Male ★★": discord.Color.blue(),
    "Female ★★": discord.Color.magenta(),
    "Non-Binary": discord.Color.purple()
}

PRO_HEX_COLORS = {
    "Pro Hex Yellow": discord.Color.gold(),
    "Pro Hex Red":    discord.Color.red(),
    "Pro Hex Pink":   discord.Color.from_rgb(255, 105, 180),
    "Pro Hex Orange": discord.Color.orange(),
    "Pro Hex Blue":   discord.Color.blue(),
    "Pro Hex Green":  discord.Color.green()
}

MAX_LEVEL = 70

LEVEL_TIER_ROLES = {
    (1, 9): {
        "name": "୨୧Newbie୨୧",
        "color": discord.Color.teal(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True
        )
    },
    (10, 19): {
        "name": "୨ৎ ˖Explorer",
        "color": discord.Color.green(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True
        )
    },
    (20, 29): {
        "name": "Vanguard",
        "color": discord.Color.blue(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True
        )
    },
    (30, 39): {
        "name": "୨ৎ ˖ Elite",
        "color": discord.Color.purple(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True
        )
    },
    (40, 49): {
        "name": "୨ৎ ˖ Champion",
        "color": discord.Color.gold(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True,
            use_soundboard=True, use_external_sounds=True
        )
    },
    (50, 59): {
        "name": "୨ৎ ˖ Legend",
        "color": discord.Color.orange(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True,
            use_soundboard=True, use_external_sounds=True,
            priority_speaker=True, create_private_threads=True
        )
    },
    (60, 70): {
        "name": "୨ৎ ˖ Sovereign",
        "color": discord.Color.dark_red(),
        "hoist": True,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True,
            use_soundboard=True, use_external_sounds=True,
            priority_speaker=True, create_private_threads=True
        )
    }
}

ROLE_PERMISSIONS_CONFIG = {
    SUPREME_LEADER_ROLE_NAME: {
        "hoist": True,
        "color": SUPREME_LEADER_COLOR,
        "permissions": discord.Permissions(administrator=True)
    },
    ADMIN_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(255, 105, 180),
        "permissions": discord.Permissions(administrator=True)
    },
    AUTHORITY_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(150, 100, 255),
        "permissions": discord.Permissions(
            view_audit_log=True, manage_guild=True, manage_channels=True,
            manage_roles=True, kick_members=True, ban_members=True,
            manage_messages=True, moderate_members=True, manage_nicknames=True,
            mute_members=True, deafen_members=True, move_members=True
        )
    },
    HEAD_MOD_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(230, 70, 80),
        "permissions": discord.Permissions(
            view_audit_log=True, kick_members=True, ban_members=True,
            manage_messages=True, moderate_members=True, mute_members=True,
            deafen_members=True, move_members=True, manage_threads=True
        )
    },
    MOD_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(240, 190, 60),
        "permissions": discord.Permissions(
            kick_members=True, manage_messages=True, moderate_members=True,
            mute_members=True, deafen_members=True, move_members=True
        )
    },
    TRIAL_MOD_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(80, 170, 250),
        "permissions": discord.Permissions(manage_messages=True, moderate_members=True)
    },
    TEAM_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.teal(),
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True
        )
    }
}

EXTENDED_SERVER_BLUEPRINT = [
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "🤖・bot-commands", "type": "text", "scheme": "supreme_admin_only"},
            {"name": "🛡️・bot-errors",   "type": "text", "scheme": "supreme_admin_only"}
        ]
    },
    {
        "category": "Info 🩵",
        "channels": [
            {"name": "📢・level-announcements", "type": "text", "scheme": "public_read"},
            {"name": "🎫・tickets",            "type": "text", "scheme": "public_read"},
            {"name": "🎨・colours",            "type": "text", "scheme": "public_read"},
            {"name": "👋・welcome",            "type": "text", "scheme": "public_read"}
        ]
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "🛡️・team-rules", "type": "text", "scheme": "staff_rules"},
            {"name": "💬・team-chat",  "type": "text", "scheme": "staff_chat"},
            {"name": "⏰・bump",       "type": "text", "scheme": "staff_chat"},
            {"name": "📰・team-news",  "type": "text", "scheme": "staff_news"}
        ]
    },
    {
        "category": "Events <3",
        "channels": [
            {"name": "🎉・gwys",  "type": "text", "scheme": "public_read"},
            {"name": "⭐・vouch", "type": "text", "scheme": "public_chat"}
        ]
    },
    {
        "category": "Chill Area <3",
        "channels": [
            {"name": "☁️・chat",        "type": "text", "scheme": "public_chat"},
            {"name": "🍸・chat-ai",     "type": "text", "scheme": "public_chat"},
            {"name": "🪄・chat-en",     "type": "text", "scheme": "public_chat"},
            {"name": "🐥・discussions", "type": "text", "scheme": "public_chat"}
        ]
    },
    {
        "category": "Media <3",
        "channels": [
            {"name": "media-share🦅", "type": "text", "scheme": "public_media"},
            {"name": "pfp-share🛼",   "type": "text", "scheme": "public_media"},
            {"name": "selfies🐳",     "type": "text", "scheme": "public_media"}
        ]
    },
    {
        "category": "Fun Area <3",
        "channels": [
            {"name": "playground-🤼",    "type": "text", "scheme": "public_chat"},
            {"name": "🚦confession-🖇",  "type": "text", "scheme": "confession_feed"},
            {"name": "birthdays",       "type": "text", "scheme": "public_chat"},
            {"name": "memes🤪",          "type": "text", "scheme": "public_media"},
            {"name": "🖇-daily-polls",   "type": "text", "scheme": "polls_feed"},
            {"name": "🖇-roblox-elites", "type": "text", "scheme": "roblox_exclusive"}
        ]
    },
    {
        "category": "Hobbies <3",
        "channels": [
            {"name": "shayari-and-poetry💗", "type": "text", "scheme": "public_chat"},
            {"name": "photography📷",       "type": "text", "scheme": "public_media"},
            {"name": "arts-and-crafts🎨",    "type": "text", "scheme": "public_media"},
            {"name": "🎤drop-your-songs",   "type": "text", "scheme": "public_media"}
        ]
    },
    {
        "category": "Voice Chat <3",
        "channels": [
            {"name": "🍕 | chit-chat", "type": "voice", "user_limit": 12, "scheme": "public_voice"},
            {"name": "🥞 | Duo",       "type": "voice", "user_limit": 2,  "scheme": "public_voice"},
            {"name": "🍞 | Trio",      "type": "voice", "user_limit": 3,  "scheme": "public_voice"},
            {"name": "🧀 | squad",     "type": "voice", "user_limit": 4,  "scheme": "public_voice"},
            {"name": "💽 | Vip",       "type": "voice", "user_limit": 50, "scheme": "vip_voice"}
        ]
    },
    {
        "category": "Music <3",
        "channels": [
            {"name": "🎷-Atom Music", "type": "voice", "user_limit": 0, "scheme": "music_voice"},
            {"name": "🎵 Hade Music", "type": "voice", "user_limit": 0, "scheme": "music_voice"}
        ]
    }
]

# ==============================================================================
# 2. TEXT NORMALIZATION & RESILIENT HELPERS
# ==============================================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\u200B-\u200D\uFEFF\u200E\u200F]", "", text)
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip().lower()

def find_role_resilient(guild: discord.Guild, target_name: str) -> Optional[discord.Role]:
    clean_target = normalize_text(target_name)
    for role in guild.roles:
        if normalize_text(role.name) == clean_target:
            return role
    return None

async def ensure_role_exists(
    guild: discord.Guild,
    name: str,
    color: discord.Color = discord.Color.default(),
    permissions: discord.Permissions = discord.Permissions.none(),
    hoist: bool = False,
    mentionable: bool = False
) -> Optional[discord.Role]:
    role = find_role_resilient(guild, name)
    if not role:
        if not guild.me.guild_permissions.manage_roles:
            return None
        try:
            role = await guild.create_role(
                name=name, color=color, permissions=permissions,
                hoist=hoist, mentionable=mentionable,
                reason="System auto-role setup"
            )
        except (discord.Forbidden, discord.HTTPException):
            return None
    return role

def is_staff_member(member: discord.Member) -> bool:
    if not member or not getattr(member, "guild", None):
        return False
    if member.id == member.guild.owner_id or member.guild_permissions.administrator:
        return True
    user_roles = {normalize_text(r.name) for r in member.roles}
    allowed = {normalize_text(r) for r in RESTRICTED_ADMIN_ROLES}
    return not user_roles.isdisjoint(allowed)

async def log_bot_error(guild: discord.Guild, error_title: str, error_detail: str):
    error_ch = discord.utils.find(lambda c: "bot-errors" in normalize_text(c.name), guild.text_channels)
    if not error_ch:
        return
    embed = discord.Embed(
        title=f"🚨 Bot Exception — {error_title}",
        description=f"```py\n{error_detail[:1800]}\n```",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    try:
        await error_ch.send(embed=embed)
    except Exception:
        pass

# ==============================================================================
# 3. DATABASE STATE & MEMORY RETENTION
# ==============================================================================

memory_lock = asyncio.Lock()
active_bump_tasks: Dict[int, asyncio.Task] = {}

def default_server_state() -> Dict[str, Any]:
    return {
        "user_xp": {},
        "user_levels": {},
        "user_warnings": {},
        "user_mute_counts": {},
        "afk_users": {},
        "user_birthdays": {},
        "last_anniversary": {},
        "confession_counter": 0,
        "last_bump_time": 0.0,
        "maintenance_mode": False,
        "tickets": {}
    }

def migrate_state_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        return default_server_state()
    
    base = default_server_state()
    for key in base:
        if key in data:
            base[key] = data[key]
    
    if "users" in data and isinstance(data["users"], dict):
        for uid, udata in data["users"].items():
            if isinstance(udata, dict):
                base["user_xp"].setdefault(str(uid), udata.get("xp", 0))
                base["user_levels"].setdefault(str(uid), udata.get("level", 1))
    if "afk" in data and isinstance(data["afk"], dict):
        base["afk_users"].update(data["afk"])
    if "confessions" in data and isinstance(data["confessions"], list):
        base["confession_counter"] = max(base["confession_counter"], len(data["confessions"]))

    return base

async def save_state_to_memory(guild: discord.Guild, memory_channel_name: str = "bot-memory", data: dict = None):
    async with memory_lock:
        channel = discord.utils.find(lambda c: c.name == memory_channel_name, guild.text_channels)
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            admin_role = find_role_resilient(guild, ADMIN_ROLE_NAME)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=False)
            try:
                channel = await guild.create_text_channel(name=memory_channel_name, overwrites=overwrites)
            except (discord.Forbidden, discord.HTTPException):
                return

        payload = data or bot.server_state.get(guild.id, default_server_state())
        raw_json = json.dumps(payload, indent=2)
        file_bytes = io.BytesIO(raw_json.encode('utf-8'))
        filename = f"backup_{guild.id}.json"
        
        try:
            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            await channel.send(
                content=f"💾 **[DATABASE STATE SYNC]** `{timestamp_str}`",
                file=discord.File(file_bytes, filename=filename)
            )

            backup_messages = []
            async for msg in channel.history(limit=30):
                if msg.attachments and any(a.filename.endswith(".json") for a in msg.attachments):
                    backup_messages.append(msg)
                elif "DATABASE STATE SYNC" in msg.content:
                    backup_messages.append(msg)

            if len(backup_messages) > 3:
                for old_msg in backup_messages[3:]:
                    try:
                        await old_msg.delete()
                        await asyncio.sleep(0.35)
                    except Exception:
                        pass
        except (discord.Forbidden, discord.HTTPException) as e:
            await log_bot_error(guild, "SaveStateToMemory", str(e))

async def load_state_from_memory(guild: discord.Guild, memory_channel_name: str = "bot-memory") -> dict:
    channel = discord.utils.find(lambda c: c.name == memory_channel_name, guild.text_channels)
    if not channel:
        return default_server_state()

    async for message in channel.history(limit=25):
        if message.attachments:
            for att in message.attachments:
                if att.filename.endswith(".json"):
                    try:
                        file_bytes = await att.read()
                        raw_data = json.loads(file_bytes.decode('utf-8'))
                        return migrate_state_payload(raw_data)
                    except Exception:
                        continue
        
        content = message.content.strip()
        if content.startswith("```"):
            clean_chunk = re.sub(r"^```(?:json)?\n?", "", content, flags=re.IGNORECASE)
            clean_chunk = re.sub(r"\n?```$", "", clean_chunk)
            try:
                raw_data = json.loads(clean_chunk)
                return migrate_state_payload(raw_data)
            except json.JSONDecodeError:
                continue

    return default_server_state()

# ==============================================================================
# 4. PERMISSION OVERWRITES
# ==============================================================================

def generate_channel_overwrites(guild: discord.Guild, scheme: str) -> Dict[Any, discord.PermissionOverwrite]:
    staff_roles = [find_role_resilient(guild, r) for r in RESTRICTED_ADMIN_ROLES]
    active_staff = [r for r in staff_roles if r]
    admin_role = find_role_resilient(guild, ADMIN_ROLE_NAME)
    supreme_role = find_role_resilient(guild, SUPREME_LEADER_ROLE_NAME)
    roblox_role = find_role_resilient(guild, ROBLOX_ROLE_NAME)
    tier_roles = [find_role_resilient(guild, cfg["name"]) for cfg in LEVEL_TIER_ROLES.values()]
    active_tiers = [r for r in tier_roles if r]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
            manage_permissions=True, embed_links=True, attach_files=True
        )
    }

    public_schemes = ["public_chat", "public_media", "public_read", "polls_feed", "confession_feed", "public_voice", "vip_voice", "music_voice"]
    if scheme in public_schemes:
        if scheme == "public_chat":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, add_reactions=True
            )
        elif scheme == "public_media":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True, add_reactions=True
            )
        elif scheme in ["public_read", "polls_feed", "confession_feed"]:
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True, add_reactions=True
            )
        elif scheme in ["public_voice", "vip_voice"]:
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True, stream=True
            )
        elif scheme == "music_voice":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True, stream=False, use_soundboard=False
            )
            
        for role in active_staff + active_tiers:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    elif scheme == "roblox_exclusive":
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        if roblox_role:
            overwrites[roblox_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True
            )
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

    elif scheme == "staff_chat":
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True
            )

    elif scheme in ["staff_rules", "staff_news"]:
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True, add_reactions=True
            )
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_messages=True
            )

    elif scheme == "supreme_admin_only":
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for role in [admin_role, supreme_role]:
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    attach_files=True, embed_links=True
                )
            
    return overwrites

# ==============================================================================
# 5. AUTO-MODERATION ENGINE
# ==============================================================================

FORBIDDEN_WORDS = ["badword1", "badword2", "spamphrase"]
SPAM_LINK_REGEX = re.compile(r"https?://(?:www\.)?(?:discord\.(?:gg|io|me|li|com/invite)|t\.me|bit\.ly)/\S+", re.IGNORECASE)
BYPASS_ROLES = RESTRICTED_ADMIN_ROLES + [BOOSTER_ROLE_NAME]

async def run_automod_check(message: discord.Message) -> bool:
    if message.author.bot or not message.guild or is_staff_member(message.author):
        return False

    user_role_names = {normalize_text(r.name) for r in message.author.roles}
    allowed_bypass = {normalize_text(r) for r in BYPASS_ROLES}
    if not user_role_names.isdisjoint(allowed_bypass):
        return False

    content_clean = normalize_text(message.content)
    
    if SPAM_LINK_REGEX.search(message.content):
        try:
            await message.delete()
        except Exception:
            pass
        await message.channel.send(f"⚠️ {message.author.mention}, external invite or spam links are not permitted here.", delete_after=6)
        return True

    for word in FORBIDDEN_WORDS:
        if word in content_clean:
            try:
                await message.delete()
            except Exception:
                pass
            
            state = bot.server_state.setdefault(message.guild.id, default_server_state())
            uid_str = str(message.author.id)
            state["user_warnings"][uid_str] = state["user_warnings"].get(uid_str, 0) + 1
            await save_state_to_memory(message.guild, data=state)
            
            await message.channel.send(f"⚠️ {message.author.mention}, your message contained prohibited language and was removed. Warning recorded.", delete_after=6)
            return True

    return False

# ==============================================================================
# 6. PROGRESSION & MILESTONES ENGINE
# ==============================================================================

xp_cooldowns: Dict[int, float] = {}

async def verify_member_tenure(member: discord.Member):
    if not member.joined_at or member.bot:
        return
    now = datetime.now(timezone.utc)
    if (now - member.joined_at).days >= 365:
        guild = member.guild
        guild_id = guild.id
        current_year = str(now.year)

        state = bot.server_state.setdefault(guild_id, default_server_state())
        last_anniv = state["last_anniversary"].get(str(member.id))

        if last_anniv != current_year:
            og_role = find_role_resilient(guild, OG_ROLE_NAME) or await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
            vet_role = find_role_resilient(guild, VETERAN_ROLE_NAME) or await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())

            roles_to_grant = [r for r in [og_role, vet_role] if r and r not in member.roles and guild.me.top_role > r]
            if roles_to_grant:
                try:
                    await member.add_roles(*roles_to_grant, reason="Tenure: 1+ Year Milestone reached")
                    await add_xp(member, 1000, bypass_cooldown=True)
                except Exception:
                    pass

            state["last_anniversary"][str(member.id)] = current_year
            await save_state_to_memory(guild, data=state)

async def sync_member_level_tier(member: discord.Member, new_level: int):
    guild = member.guild
    target_tier_data = None
    for (min_lvl, max_lvl), config in LEVEL_TIER_ROLES.items():
        if min_lvl <= new_level <= max_lvl:
            target_tier_data = config
            break

    if not target_tier_data:
        return

    all_tier_names = {normalize_text(cfg["name"]) for cfg in LEVEL_TIER_ROLES.values()}
    target_clean = normalize_text(target_tier_data["name"])

    to_remove = [
        r for r in member.roles
        if normalize_text(r.name) in all_tier_names
        and normalize_text(r.name) != target_clean
        and guild.me.top_role > r
    ]

    target_role = find_role_resilient(guild, target_tier_data["name"])
    if not target_role:
        target_role = await ensure_role_exists(
            guild, target_tier_data["name"], target_tier_data["color"],
            permissions=target_tier_data["permissions"], hoist=target_tier_data["hoist"]
        )

    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Level tier advancement")
        if target_role and target_role not in member.roles and guild.me.top_role > target_role:
            await member.add_roles(target_role, reason="Level tier advancement")
    except Exception:
        pass

async def add_xp(member: discord.Member, xp_amount: int, bypass_cooldown: bool = False):
    if member.bot or not member.guild:
        return

    now = time.time()
    if not bypass_cooldown:
        last_xp = xp_cooldowns.get(member.id, 0)
        if now - last_xp < 45:
            return
        xp_cooldowns[member.id] = now

    guild = member.guild
    guild_id = guild.id
    state = bot.server_state.setdefault(guild_id, default_server_state())
    uid_str = str(member.id)

    curr_xp = state["user_xp"].get(uid_str, 0) + xp_amount
    curr_lvl = state["user_levels"].get(uid_str, 1)

    initial_lvl = curr_lvl
    while curr_lvl < MAX_LEVEL:
        needed_xp = curr_lvl * 300
        if curr_xp >= needed_xp:
            curr_xp -= needed_xp
            curr_lvl += 1
        else:
            break

    state["user_levels"][uid_str] = curr_lvl
    state["user_xp"][uid_str] = curr_xp

    if curr_lvl > initial_lvl:
        await sync_member_level_tier(member, curr_lvl)
        
        current_tier_name = "Standard Member"
        tier_perks = "Standard Chat & Voice Access"
        for (min_l, max_l), cfg in LEVEL_TIER_ROLES.items():
            if min_l <= curr_lvl <= max_l:
                current_tier_name = cfg["name"]
                p = cfg["permissions"]
                perk_list = []
                if p.embed_links: perk_list.append("Embed Links")
                if p.attach_files: perk_list.append("Attach Files")
                if p.use_external_emojis: perk_list.append("External Emojis")
                if p.stream: perk_list.append("Video Streaming")
                if p.use_soundboard: perk_list.append("Soundboard Access")
                if p.priority_speaker: perk_list.append("Priority Speaker")
                tier_perks = " • ".join(perk_list) if perk_list else "Advanced Tier Perks"
                break

        next_goal_xp = curr_lvl * 300
        ann_ch = discord.utils.find(lambda c: "level-announcements" in normalize_text(c.name), guild.text_channels)
        
        if ann_ch:
            embed = discord.Embed(
                title="⚡ Level Advanced — Milestone Unlocked!",
                description=(
                    f"Congratulations {member.mention}! You've leveled up to **Level {curr_lvl}**! 🎉\n\n"
                    f"• **Unlocked Role:** `{current_tier_name}`\n"
                    f"• **New Tier Perks:** `{tier_perks}`\n"
                    f"• **Next Goal:** `{curr_xp:,} / {next_goal_xp:,} XP`"
                ),
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Keep participating to rank higher on the leaderboard!")
            try:
                await ann_ch.send(content=f"🎉 Great milestone, {member.mention}!", embed=embed)
            except Exception:
                pass

        await save_state_to_memory(guild, data=state)

# ==============================================================================
# 7. INTERACTIVE PANELS, MODALS & VIEWS
# ==============================================================================

class CommunityRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _toggle_role(self, interaction: discord.Interaction, role_name: str, color: discord.Color, mentionable: bool):
        await interaction.response.defer(ephemeral=True)
        guild, member = interaction.guild, interaction.user
        role = await ensure_role_exists(guild, role_name, color, mentionable=mentionable)
        if not role or guild.me.top_role <= role:
            return await interaction.followup.send("⚠️ Cannot manage role due to hierarchy position.", ephemeral=True)

        if role in member.roles:
            await member.remove_roles(role, reason="Self-role toggle off")
            await interaction.followup.send(f"🔕 Removed **{role.name}**.", ephemeral=True)
        else:
            await member.add_roles(role, reason="Self-role toggle on")
            await interaction.followup.send(f"🔔 Equipped **{role.name}**!", ephemeral=True)

    @discord.ui.button(label="Poll Pings", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="btn_toggle_pollpings")
    async def toggle_poll_pings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, POLL_ROLE_NAME, discord.Color.red(), True)

    @discord.ui.button(label="Roblox Members", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="btn_toggle_roblox")
    async def toggle_roblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, ROBLOX_ROLE_NAME, discord.Color.blue(), False)

class ColorSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, emoji="🎨", description=f"Switch display color to {name}")
            for name in PRO_HEX_COLORS
        ]
        options.append(discord.SelectOption(label="Reset Color", emoji="⚪", description="Remove custom color role"))
        super().__init__(placeholder="Choose your display chat color...", min_values=1, max_values=1, custom_id="sel_hex_colors", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild, member = interaction.guild, interaction.user
        selected = self.values[0]

        to_remove = [r for r in member.roles if r.name in PRO_HEX_COLORS and guild.me.top_role > r]
        if to_remove:
            await member.remove_roles(*to_remove, reason="Color role swap")

        if selected == "Reset Color":
            return await interaction.followup.send("⚪ Removed your cosmetic chat color.", ephemeral=True)

        target_role = find_role_resilient(guild, selected) or await ensure_role_exists(guild, selected, PRO_HEX_COLORS[selected])

        if target_role and guild.me.top_role > target_role:
            await member.add_roles(target_role, reason="Self-assigned chat color")
            await interaction.followup.send(f"✨ Equipped **{selected}**!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Cannot assign color. Role hierarchy conflict.", ephemeral=True)

class ColorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColorSelect())

class GenderSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Male ★★", emoji="👦", description="Select Male identity role"),
            discord.SelectOption(label="Female ★★", emoji="👧", description="Select Female identity role"),
            discord.SelectOption(label="Non-Binary", emoji="✨", description="Select Non-Binary identity role"),
            discord.SelectOption(label="Remove Gender Role", emoji="⚪", description="Clear identity roles")
        ]
        super().__init__(placeholder="Choose your identity role...", min_values=1, max_values=1, custom_id="sel_gender_roles", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild, member = interaction.guild, interaction.user
        selected = self.values[0]

        to_remove = [r for r in member.roles if r.name in GENDER_ROLES and guild.me.top_role > r]
        if to_remove:
            await member.remove_roles(*to_remove, reason="Gender role update")

        if selected == "Remove Gender Role":
            return await interaction.followup.send("⚪ Removed your identity role.", ephemeral=True)

        target_role = find_role_resilient(guild, selected) or await ensure_role_exists(guild, selected, GENDER_ROLES[selected])

        if target_role and guild.me.top_role > target_role:
            await member.add_roles(target_role, reason="Identity role self-assignment")
            await interaction.followup.send(f"✨ Assigned **{selected}**!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error assigning identity role. Hierarchy issue.", ephemeral=True)

class GenderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GenderSelect())

class ConfessionModal(discord.ui.Modal, title="Anonymous Confession Portal"):
    confession_text = discord.ui.TextInput(
        label="Your Confession",
        style=discord.TextStyle.paragraph,
        placeholder="Type your 100% anonymous confession here...",
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        guild_id = guild.id
        state = bot.server_state.setdefault(guild_id, default_server_state())

        target_ch = discord.utils.find(lambda c: "confession" in normalize_text(c.name) and "panel" not in normalize_text(c.name), guild.text_channels)
        if not target_ch:
            return await interaction.followup.send("❌ Confession feed channel not found.", ephemeral=True)

        state["confession_counter"] = state.get("confession_counter", 0) + 1
        cid = state["confession_counter"]
        text = self.confession_text.value

        embed = discord.Embed(
            title=f"💌 Anonymous Confession #{cid}",
            description=f"*{text}*",
            color=discord.Color.from_rgb(230, 70, 80),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="100% Anonymous • Submit yours via the confession panel!")
        
        msg = await target_ch.send(embed=embed)
        await msg.add_reaction("❤️")
        await msg.add_reaction("💔")

        await interaction.followup.send("🤫 Your confession has been sent anonymously. Your identity was never recorded!", ephemeral=True)
        await save_state_to_memory(guild, data=state)

class ConfessionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Confess Anonymously", style=discord.ButtonStyle.danger, emoji="💌", custom_id="btn_open_confession_modal")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfessionModal())

class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"Support Portal — {ticket_type}")
        self.ticket_type = ticket_type
        
        self.reason_input = discord.ui.TextInput(
            label="Describe your request / details",
            style=discord.TextStyle.paragraph,
            placeholder="Provide context, application details, or how staff can assist you...",
            required=True,
            max_length=1500
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild, user = interaction.guild, interaction.user

        clean_name = re.sub(r"[^\w-]", "", user.name.lower()) or str(user.id)
        ticket_ch_name = f"ticket-{self.ticket_type.lower()[:5]}-{clean_name[:15]}"
        
        if discord.utils.find(lambda c: c.name == ticket_ch_name, guild.text_channels):
            return await interaction.followup.send("⚠️ You already have an open ticket of this type.", ephemeral=True)

        category = discord.utils.find(lambda c: "team" in normalize_text(c.name), guild.categories)
        if not category:
            category = await guild.create_category(name="Team <3", reason="Auto-created missing Team category")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        for rname in RESTRICTED_ADMIN_ROLES:
            st_role = find_role_resilient(guild, rname)
            if st_role:
                overwrites[st_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True)

        try:
            ch = await guild.create_text_channel(
                name=ticket_ch_name, 
                category=category, 
                overwrites=overwrites, 
                reason=f"Ticket opened: {self.ticket_type}"
            )
            
            guild_id = guild.id
            state = bot.server_state.setdefault(guild_id, default_server_state())
            state["tickets"][str(ch.id)] = {
                "user_id": user.id, 
                "type": self.ticket_type,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await save_state_to_memory(guild, data=state)

            embed = discord.Embed(
                title=f"🎫 Support Ticket — {self.ticket_type}",
                description=(
                    f"Welcome {user.mention}!\n"
                    f"• **Inquiry Type:** `{self.ticket_type}`\n"
                    f"• **Details:** *{self.reason_input.value}*\n\n"
                    "Staff have been notified and will assist you shortly.\n"
                    "Click **Close Ticket** below when finished."
                ),
                color=discord.Color.teal(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await ch.send(content=f"{user.mention}", embed=embed, view=TicketControlsView())
            await interaction.followup.send(f"✅ Ticket created successfully: {ch.mention}", ephemeral=True)
        except Exception as e:
            await log_bot_error(guild, "TicketModalSubmit", str(e))
            await interaction.followup.send(f"❌ Could not create ticket channel: `{e}`", ephemeral=True)

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Team Apply", emoji="🛡️", description="Apply to join the Chill-Verse staff team"),
            discord.SelectOption(label="Create Ticket", emoji="📩", description="Open a general support ticket"),
            discord.SelectOption(label="Need Help", emoji="🆘", description="Report an issue or request immediate assistance")
        ]
        super().__init__(placeholder="Select an inquiry type to open a ticket...", min_values=1, max_values=1, custom_id="sel_ticket_options", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.followup.send("🔒 **Ticket closing in 5 seconds...**")
        
        guild_id = interaction.guild.id
        state = bot.server_state.setdefault(guild_id, default_server_state())
        state["tickets"].pop(str(interaction.channel.id), None)
        await save_state_to_memory(interaction.guild, data=state)

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Closed by {interaction.user}")
        except Exception:
            pass

# ==============================================================================
# 8. BOT CLIENT SETUP & SYSTEM HEALTH AUDIT
# ==============================================================================

class ChillVerseBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents, help_command=None)
        self.server_state: Dict[int, Dict[str, Any]] = {}

    async def setup_hook(self):
        self.add_view(CommunityRolesView())
        self.add_view(ColorView())
        self.add_view(GenderView())
        self.add_view(TicketLaunchView())
        self.add_view(TicketControlsView())
        self.add_view(ConfessionPanelView())
        self.daily_birthday_check.start()
        self.auto_backup_loop.start()

    @tasks.loop(minutes=10)
    async def auto_backup_loop(self):
        for guild in self.guilds:
            state = self.server_state.get(guild.id)
            if state:
                await save_state_to_memory(guild, data=state)

    @auto_backup_loop.before_loop
    async def before_auto_backup(self):
        await self.wait_until_ready()

    @tasks.loop(hours=24)
    async def daily_birthday_check(self):
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%d-%m")
        for guild in self.guilds:
            state = self.server_state.get(guild.id, {})
            birthdays = state.get("user_birthdays", {})
            bday_ch = discord.utils.find(lambda c: "birthdays" in normalize_text(c.name), guild.text_channels)
            if not bday_ch:
                continue

            for uid, bday in birthdays.items():
                if bday == today_str:
                    member = guild.get_member(int(uid))
                    if member:
                        embed = discord.Embed(
                            title="🎂 Happy Birthday! 🎉",
                            description=f"Wishing a wonderful Birthday to {member.mention}! 🥳✨\nHave an amazing day celebrating in Chill-Verse!",
                            color=discord.Color.gold()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        try:
                            await bday_ch.send(content=f"🎉 {member.mention}", embed=embed)
                        except Exception:
                            pass

    @daily_birthday_check.before_loop
    async def before_bday_check(self):
        await self.wait_until_ready()

bot = ChillVerseBot()

async def run_system_health_audit(guild: discord.Guild):
    missing_roles = []
    for rname in list(ROLE_PERMISSIONS_CONFIG.keys()):
        if not find_role_resilient(guild, rname):
            missing_roles.append(rname)

    missing_channels = []
    for cat in EXTENDED_SERVER_BLUEPRINT:
        for ch in cat["channels"]:
            if not discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(ch["name"]), guild.text_channels + guild.voice_channels):
                missing_channels.append(ch["name"])

    error_ch = discord.utils.find(lambda c: "bot-errors" in normalize_text(c.name), guild.text_channels)
    if error_ch:
        embed = discord.Embed(
            title="🔍 System Boot Audit Completed",
            description=(
                f"✅ Bot initialized successfully on **{guild.name}**.\n"
                f"• **Database Records Loaded:** `{len(bot.server_state.get(guild.id, {}).get('user_xp', {}))}` user profiles\n"
                f"• **Missing Roles Detected:** `{len(missing_roles)}` `(Run .autorole_setup if needed)`\n"
                f"• **Missing Channels Detected:** `{len(missing_channels)}` `(Run .setup_channels if needed)`"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        try:
            await error_ch.send(embed=embed)
        except Exception:
            pass

def is_staff_or_admin():
    async def predicate(ctx: commands.Context) -> bool:
        return is_staff_member(ctx.author)
    return commands.check(predicate)

def is_team_channel():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        in_team_cat = ctx.channel.category and "team" in normalize_text(ctx.channel.category.name)
        in_team_ch = "team" in normalize_text(ctx.channel.name) or "bump" in normalize_text(ctx.channel.name) or "bot-commands" in normalize_text(ctx.channel.name)
        if in_team_cat or in_team_ch:
            return True
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send("❌ This command can only be used inside **`Team <3`** or **`Admin Area`** channels.", delete_after=5)
        return False
    return commands.check(predicate)

def is_bump_channel():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        if "bump" in normalize_text(ctx.channel.name):
            return True
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send("❌ This command can only be used inside a **`bump`** channel.", delete_after=5)
        return False
    return commands.check(predicate)

def is_ticket_channel():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        if "ticket" in normalize_text(ctx.channel.name):
            return True
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send("❌ This command can only be used inside a **`tickets`** channel.", delete_after=5)
        return False
    return commands.check(predicate)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    print(f"❌ Command Error [{ctx.command}]: {error}")
    await log_bot_error(ctx.guild, f"Command: {ctx.command}", tb)
    try:
        await ctx.send(f"⚠️ Error executing command: `{error}`", delete_after=10)
    except Exception:
        pass

# ==============================================================================
# 9. BUMP SCHEDULER & LISTENERS
# ==============================================================================

async def schedule_bump_reminder(guild: discord.Guild, channel: Optional[discord.TextChannel] = None):
    if guild.id in active_bump_tasks and not active_bump_tasks[guild.id].done():
        try:
            active_bump_tasks[guild.id].cancel()
        except Exception:
            pass

    async def _runner():
        try:
            state = bot.server_state.setdefault(guild.id, default_server_state())
            last_bump = state.get("last_bump_time", 0.0)
            now = time.time()
            remaining = max(0, int(7200 - (now - last_bump)))

            if remaining > 0:
                await asyncio.sleep(remaining)

            bump_ch = channel or discord.utils.find(lambda c: "bump" in normalize_text(c.name), guild.text_channels)
            if bump_ch:
                role = find_role_resilient(guild, BUMP_ROLE_NAME)
                ping = role.mention if role else "@here"
                embed = discord.Embed(
                    title="⏰ Time to Bump!",
                    description="The 2-hour cooldown has passed. Run `.bump` to grow the server! 🚀",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                await bump_ch.send(content=f"🔔 {ping}", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
        finally:
            active_bump_tasks.pop(guild.id, None)

    task = asyncio.create_task(_runner())
    active_bump_tasks[guild.id] = task

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    for guild in bot.guilds:
        restored = await load_state_from_memory(guild)
        bot.server_state[guild.id] = restored
        print(f"✅ State loaded for '{guild.name}' ({len(restored.get('user_xp', {}))} users in database)")

        if restored.get("last_bump_time", 0.0) > 0:
            await schedule_bump_reminder(guild)

        for member in guild.members:
            if not member.bot:
                await verify_member_tenure(member)

        await run_system_health_audit(guild)

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    newbie_role = find_role_resilient(member.guild, "୨୧Newbie୨୧") or await ensure_role_exists(member.guild, "୨୧Newbie୨୧", discord.Color.teal())
    if newbie_role and member.guild.me.top_role > newbie_role:
        try:
            await member.add_roles(newbie_role, reason="Auto-assign on onboarding")
        except Exception:
            pass

    welcome_ch = discord.utils.find(lambda c: "welcome" in normalize_text(c.name), member.guild.text_channels)
    if welcome_ch:
        embed = discord.Embed(
            title="✨ Welcome to Chill-Verse! 🌴",
            description=f"Hey {member.mention}! We are thrilled to have you here. 🎉\n\n• Grab your identity roles in <#colours>\n• Open a support ticket in <#tickets> if you need assistance!",
            color=discord.Color.from_rgb(255, 105, 180),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{len(member.guild.members)}")
        try:
            await welcome_ch.send(content=f"Welcome {member.mention}!", embed=embed)
        except Exception:
            pass

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if not before.premium_since and after.premium_since:
        booster_role = find_role_resilient(after.guild, BOOSTER_ROLE_NAME)
        if booster_role and booster_role not in after.roles and after.guild.me.top_role > booster_role:
            try:
                await after.add_roles(booster_role, reason="Server boost perk")
            except Exception:
                pass

        await add_xp(after, 1500, bypass_cooldown=True)
        ann_ch = discord.utils.find(lambda c: "level-announcements" in normalize_text(c.name), after.guild.text_channels)
        if ann_ch:
            embed = discord.Embed(
                title="✨ Server Boost Received! 🚀",
                description=f"Thank you {after.mention} for boosting **{after.guild.name}**!\n• Equipped `{BOOSTER_ROLE_NAME}`\n• Received **+1,500 XP**",
                color=discord.Color.from_rgb(255, 105, 180),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            try:
                await ann_ch.send(content=f"🎉 {after.mention}", embed=embed)
            except Exception:
                pass

@bot.event
async def on_message(message: discord.Message):
    try:
        if message.author.bot or not message.guild:
            if message.guild and (message.author.id == 302050872383242240 or (message.author.bot and "bump" in message.content.lower())):
                success = "bump done" in message.content.lower()
                if not success and message.embeds:
                    for emb in message.embeds:
                        desc = emb.description or ""
                        if "bump done" in desc.lower() or "thumbsup" in desc.lower():
                            success = True
                            break
                if success:
                    state = bot.server_state.setdefault(message.guild.id, default_server_state())
                    state["last_bump_time"] = time.time()
                    await save_state_to_memory(message.guild, data=state)
                    try:
                        await message.channel.send("🚀 **Bump detected!** Next bump alert scheduled in 2 hours.", delete_after=10)
                    except Exception:
                        pass
                    await schedule_bump_reminder(message.guild, message.channel)
            return

        if await run_automod_check(message):
            return

        guild_id = message.guild.id
        state = bot.server_state.setdefault(guild_id, default_server_state())

        if state.get("maintenance_mode", False) and not is_staff_member(message.author):
            if message.content.startswith("."):
                await message.channel.send("🚧 **Server is currently in Maintenance Mode.** Commands are restricted to staff.", delete_after=6)
            return

        user_str = str(message.author.id)
        if user_str in state["afk_users"]:
            afk_entry = state["afk_users"].pop(user_str, {})
            spent_time = int((time.time() - afk_entry.get("timestamp", time.time())) // 60)
            spent_str = f"{spent_time} minute(s)" if spent_time > 0 else "a few seconds"
            mood = afk_entry.get("mood", "neutral")

            if mood == "sad":
                greet = f"🤍 Welcome back {message.author.mention}! We hope your day is getting brighter. I've cleared your AFK. *(Away for {spent_str})*"
            elif mood == "happy":
                greet = f"🎉 Welcome back {message.author.mention}! Hope you had a fantastic time! I've cleared your AFK. *(Away for {spent_str})* 😊"
            else:
                greet = f"👋 Welcome back {message.author.mention}! I've removed your AFK. *(Away for {spent_str})*"

            await message.channel.send(greet, delete_after=10)
            await save_state_to_memory(message.guild, data=state)

        if message.mentions:
            for member in message.mentions:
                m_str = str(member.id)
                if m_str in state["afk_users"] and member.id != message.author.id:
                    rec = state["afk_users"][m_str]
                    mins = int((time.time() - rec["timestamp"]) // 60)
                    t_str = f"{mins}m ago" if mins > 0 else "just now"
                    m_mood = rec.get("mood", "neutral")

                    if m_mood == "sad":
                        note = f"🥺 **{member.display_name}** is AFK feeling down: *{rec['reason']}* `({t_str})` 💔"
                    elif m_mood == "happy":
                        note = f"✨ **{member.display_name}** is AFK vibing: *{rec['reason']}* `({t_str})` 😊"
                    else:
                        note = f"💤 **{member.display_name}** is AFK: *{rec['reason']}* `({t_str})`"

                    await message.channel.send(note, delete_after=10)

        ch_name = normalize_text(message.channel.name)
        if "vouch" in ch_name:
            try:
                await message.add_reaction("⭐")
            except Exception:
                pass
        elif "memes" in ch_name or "selfies" in ch_name or "photography" in ch_name:
            if message.attachments or "http" in message.content:
                try:
                    await message.add_reaction("❤️")
                    await message.add_reaction("🔥")
                except Exception:
                    pass
        elif "discussions" in ch_name and not isinstance(message.channel, discord.Thread):
            if message.type == discord.MessageType.default:
                try:
                    thread_title = message.content[:40] if message.content else f"Discussion by {message.author.name}"
                    await message.create_thread(name=f"💬・{thread_title}")
                except Exception:
                    pass

        await add_xp(message.author, 15)
        await bot.process_commands(message)
    except Exception as e:
        await log_bot_error(message.guild, "OnMessageEvent", str(e))

# ==============================================================================
# 10. USER, LEVEL & COMMUNITY COMMANDS
# ==============================================================================

@bot.command(name="afk")
async def cmd_afk(ctx: commands.Context, *, reason: str = "AFK"):
    try:
        await ctx.message.delete(delay=10)
    except Exception:
        pass

    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())

    mood = "neutral"
    lower_r = reason.lower()
    sad_words = ["sad", "depressed", "cry", "crying", "unhappy", "down", "hurt", "tired", "heartbroken", "gloomy", "lonely"]
    happy_words = ["happy", "glad", "joy", "excited", "vibing", "celebrate", "chilling", "good", "fun", "blessed"]

    if any(w in lower_r for w in sad_words):
        mood = "sad"
        status_header = "🥺 Gone AFK (Feeling Down)"
        color = discord.Color.from_rgb(130, 140, 200)
        subtext = "Hope you feel better soon! Take care of yourself 🤍"
    elif any(w in lower_r for w in happy_words):
        mood = "happy"
        status_header = "✨ Gone AFK (Feeling Great!)"
        color = discord.Color.gold()
        subtext = "Enjoy your time and keep smiling! ✨"
    else:
        status_header = "💤 Gone AFK"
        color = discord.Color.teal()
        subtext = "I'll let everyone know you're away."

    state["afk_users"][str(ctx.author.id)] = {
        "reason": reason,
        "timestamp": time.time(),
        "mood": mood
    }
    await save_state_to_memory(ctx.guild, data=state)

    embed = discord.Embed(
        title=status_header,
        description=f"{ctx.author.mention} is now AFK: **{reason}**\n*{subtext}*",
        color=color
    )
    embed.set_footer(text="Notice clears in 10s. AFK remains saved until you speak again!")
    await ctx.send(embed=embed, delete_after=10)

@bot.command(name="bump")
@is_bump_channel()
async def cmd_bump(ctx: commands.Context):
    try:
        await ctx.message.delete(delay=10)
    except Exception:
        pass

    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    last_bump = state.get("last_bump_time", 0.0)
    elapsed = time.time() - last_bump
    remaining = int(7200 - elapsed)

    if remaining > 0 and not is_staff_member(ctx.author):
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
        return await ctx.send(f"⏳ {ctx.author.mention}, the server cannot be bumped yet! Please wait **{time_str}** until the 2-hour timer completes.", delete_after=8)

    state["last_bump_time"] = time.time()
    await add_xp(ctx.author, 250, bypass_cooldown=True)
    await save_state_to_memory(ctx.guild, data=state)

    await ctx.send(f"👊 {ctx.author.mention}, bump logged! I'll ping **{BUMP_ROLE_NAME}** in 2 hours.", delete_after=10)
    await schedule_bump_reminder(ctx.guild, ctx.channel)

@bot.command(name="bumptimer", aliases=["nextbump", "bumpcheck", "bp"])
async def cmd_bumptimer(ctx: commands.Context):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    last_bump = state.get("last_bump_time", 0.0)
    elapsed = time.time() - last_bump
    remaining = int(7200 - elapsed)

    if remaining > 0:
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
        progress = min(int((elapsed / 7200) * 10), 10)
        bar = "▰" * progress + "▱" * (10 - progress)

        embed = discord.Embed(
            title="⏰ Server Bump Countdown",
            description=f"Next bump will be ready in **{time_str}**!\n\n`[{bar}]`",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🚀 Bump Ready!",
            description="The server is ready to be bumped right now! Run `.bump` to grow the server.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.command(name="confess")
async def cmd_confess(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    class ConfessTriggerView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)

        @discord.ui.button(label="Open Confession Form", style=discord.ButtonStyle.danger, emoji="💌")
        async def trigger_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(ConfessionModal())

    try:
        await ctx.author.send(
            "💌 Click the button below to open your **100% Anonymous** Confession Form:",
            view=ConfessTriggerView()
        )
        await ctx.send(f"💌 {ctx.author.mention}, I've sent you a DM with your 100% anonymous confession link!", delete_after=6)
    except Exception:
        await ctx.send(f"❌ {ctx.author.mention}, I couldn't send you a DM. Please enable DMs to use `.confess`!", delete_after=6)

@bot.command(name="setbirthday", aliases=["setbday"])
async def cmd_setbirthday(ctx: commands.Context, date_str: str):
    if not re.match(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])$", date_str):
        return await ctx.send("⚠️ Invalid format! Use `DD-MM` (e.g. `.setbirthday 15-06`).", delete_after=10)

    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    state["user_birthdays"][str(ctx.author.id)] = date_str
    await save_state_to_memory(ctx.guild, data=state)
    await ctx.send(f"🎂 {ctx.author.mention}, your birthday was saved as **{date_str}**!", delete_after=10)

@bot.command(name="birthday", aliases=["bday"])
async def cmd_birthday(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    bday = state["user_birthdays"].get(str(target.id))
    if bday:
        await ctx.send(f"🎂 **{target.display_name}**'s birthday is **{bday}** (DD-MM).")
    else:
        await ctx.send(f"ℹ️ No birthday saved for **{target.display_name}**.")

@bot.command(name="rank", aliases=["level", "xp"])
async def cmd_rank(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    uid_str = str(target.id)

    lvl = state["user_levels"].get(uid_str, 1)
    current_xp = state["user_xp"].get(uid_str, 0)
    needed_xp = lvl * 300

    if lvl >= MAX_LEVEL:
        lvl_display = f"{lvl} (MAX)"
        progress_text = f"{current_xp:,} XP (Maximum Level Reached)"
        bar = "▰" * 10
    else:
        lvl_display = str(lvl)
        progress = min(int((current_xp / max(needed_xp, 1)) * 10), 10)
        bar = "▰" * progress + "▱" * (10 - progress)
        progress_text = f"{current_xp:,} / {needed_xp:,} XP"

    embed = discord.Embed(title=f"📊 Rank Card — {target.display_name}", color=discord.Color.teal())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Level", value=f"**{lvl_display}**", inline=True)
    embed.add_field(name="Tier Progress", value=progress_text, inline=True)
    embed.add_field(name="Progress Bar", value=f"`[{bar}]`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def cmd_leaderboard(ctx: commands.Context):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    users_xp = state["user_xp"]
    if not users_xp:
        return await ctx.send("ℹ️ No XP records found in the database yet.")

    sorted_users = sorted(users_xp.items(), key=lambda item: item[1], reverse=True)[:10]
    lines = []
    for rank, (uid, xp_val) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        lvl = state["user_levels"].get(uid, 1)
        lvl_str = f"**{lvl} (MAX)**" if lvl >= MAX_LEVEL else f"**{lvl}**"
        lines.append(f"**#{rank}** {name} — Level {lvl_str} ({xp_val:,} XP)")

    embed = discord.Embed(
        title="🏆 Server XP Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed)

@bot.command(name="poll")
@is_staff_or_admin()
async def cmd_poll(ctx: commands.Context, *, question: str):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    poll_ch = discord.utils.find(lambda c: "daily-polls" in normalize_text(c.name), ctx.guild.text_channels) or ctx.channel
    role = find_role_resilient(ctx.guild, POLL_ROLE_NAME)
    ping = role.mention if role else "@here"

    embed = discord.Embed(
        title="📊 Official Server Poll",
        description=f"**{question}**\n\nReact below to vote!",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Poll by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    msg = await poll_ch.send(content=f"🔔 {ping}", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command(name="botlist", aliases=["botcommands"])
@is_team_channel()
async def cmd_botlist(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🤖 Chill-Verse Complete Command Matrix",
        description="Catalog of all administrative, staff, and public user commands:",
        color=discord.Color.teal(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="🏗️ Setup & Infrastructure",
        value=(
            "• `.setup_channels` — Deploys missing channels & auto-posts panels safely\n"
            "• `.syncperms` — Enforces staff and tier permission matrices\n"
            "• `.autorole_setup` — Provisions all server roles and cosmetic tiers\n"
            "• `.resetroles` — Wipes and re-provisions all managed server roles\n"
            "• `.maintenance [on/off]` — Toggles server maintenance lock"
        ),
        inline=False
    )
    embed.add_field(
        name="🎨 Panels & UI Management",
        value=(
            "• `.communitypanel` — Spawns PollPings and Roblox role picker\n"
            "• `.postcolors` — Spawns the chat color selection dropdown\n"
            "• `.postgender` — Spawns the identity role dropdown\n"
            "• `.posttickets` — Spawns the support ticket launcher\n"
            "• `.confesspanel` — Spawns the 100% anonymous confession form panel"
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Moderation Suite",
        value=(
            "• `.kick <member>` — Kicks a user from the server\n"
            "• `.ban <member>` — Bans a user from the server\n"
            "• `.timeout <member> <mins>` — Mutes user & updates mute count\n"
            "• `.warn <member> [reason]` — Issues official staff warning\n"
            "• `.warnings <member>` — Views warning and mute record\n"
            "• `.clearwarns <member>` — Clears warnings for a member\n"
            "• `.purge <amount>` — Clears up to 100 messages (Owner, Highness, Authority)"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Public & Community Features",
        value=(
            "• `.rank` — Displays user level (capped at 70), total XP, and detailed card\n"
            "• `.leaderboard` — Shows top 10 most active members by XP\n"
            "• `.confess` — Triggers 100% anonymous confession modal via DMs\n"
            "• `.afk [reason]` — Sets AFK status with 10s auto-delete\n"
            "• `.bumptimer` — Checks exact countdown until next bump\n"
            "• `.bump` — Logs manual server bump (Strict 2-hour lockout enforced)\n"
            "• `.setbirthday <DD-MM>` — Registers birthday for daily announcements\n"
            "• `.birthday [member]` — Checks registered birthday\n"
            "• `.poll <question>` — Dispatches an official server poll"
        ),
        inline=False
    )
    embed.add_field(
        name="📦 System & Backup",
        value=(
            "• `.backup` — Commits snapshot to `#bot-memory` (keeps 3 backups with bump state)\n"
            "• `.restorebackup` — Synchronizes state from `#bot-memory`\n"
            "• `.removeadminrole` — Migrates legacy Admin holders to Highness"
        ),
        inline=False
    )
    embed.set_footer(text="Restricted exclusively to Team <3 / Admin channels.")
    await ctx.send(embed=embed)

# ==============================================================================
# 11. MODERATION & MAINTENANCE COMMANDS
# ==============================================================================

@bot.command(name="maintenance")
@commands.has_permissions(administrator=True)
async def cmd_maintenance(ctx: commands.Context, state_arg: Optional[str] = None):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    
    if state_arg is None:
        state["maintenance_mode"] = not state.get("maintenance_mode", False)
    else:
        state["maintenance_mode"] = state_arg.lower() in ["on", "enable", "true", "yes"]

    status = state["maintenance_mode"]
    await save_state_to_memory(ctx.guild, data=state)

    embed = discord.Embed(
        title="🚧 Maintenance Mode Updated",
        description=f"Server Maintenance Mode is now **{'ACTIVATED 🔴' if status else 'DEACTIVATED 🟢'}**.\n\n"
                    f"{'⚠️ Regular commands and non-staff message executions are restricted.' if status else '✅ All public functions and member commands are operational.'}",
        color=discord.Color.red() if status else discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed)

@bot.command(name="warn")
@is_staff_or_admin()
async def cmd_warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if ctx.author.top_role <= member.top_role or member.id == ctx.guild.owner_id:
        return await ctx.send("❌ You cannot warn a member with equal or higher authority.")

    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    uid_str = str(member.id)
    state["user_warnings"][uid_str] = state["user_warnings"].get(uid_str, 0) + 1
    total = state["user_warnings"][uid_str]
    await save_state_to_memory(ctx.guild, data=state)

    embed = discord.Embed(
        title="⚠️ Member Warned",
        description=f"**User:** {member.mention} ({member.id})\n**Staff:** {ctx.author.mention}\n**Reason:** {reason}\n**Total Warnings:** `{total}`",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed)

@bot.command(name="warnings", aliases=["warns"])
@is_staff_or_admin()
async def cmd_warnings(ctx: commands.Context, member: discord.Member):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    uid_str = str(member.id)
    warns = state["user_warnings"].get(uid_str, 0)
    mutes = state["user_mute_counts"].get(uid_str, 0)

    embed = discord.Embed(
        title=f"📋 Infraction History — {member.display_name}",
        description=f"• **Warnings:** `{warns}`\n• **Mutes / Timeouts:** `{mutes}`",
        color=discord.Color.teal()
    )
    await ctx.send(embed=embed)

@bot.command(name="clearwarns", aliases=["clearwarnings"])
@is_staff_or_admin()
async def cmd_clearwarns(ctx: commands.Context, member: discord.Member):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    state["user_warnings"][str(member.id)] = 0
    await save_state_to_memory(ctx.guild, data=state)
    await ctx.send(f"✅ Cleared all warnings for **{member.display_name}**.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def cmd_kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if ctx.author.top_role <= member.top_role or member.id == ctx.guild.owner_id:
        return await ctx.send("❌ You cannot kick a member with equal or higher authority.")
    if ctx.guild.me.top_role <= member.top_role:
        return await ctx.send("❌ Cannot kick. Bot role is below member's highest role.")
    try:
        await member.kick(reason=f"{reason} (By {ctx.author})")
        await ctx.send(f"👢 Kicked **{member.display_name}** | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Failed to kick. Check bot permissions and role order.")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def cmd_ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if ctx.author.top_role <= member.top_role or member.id == ctx.guild.owner_id:
        return await ctx.send("❌ You cannot ban a member with equal or higher authority.")
    if ctx.guild.me.top_role <= member.top_role:
        return await ctx.send("❌ Cannot ban. Bot role is below member's highest role.")
    try:
        await member.ban(reason=f"{reason} (By {ctx.author})")
        await ctx.send(f"🔨 Banned **{member.display_name}** | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Failed to ban. Check bot permissions and role order.")

@bot.command(name="timeout", aliases=["mute"])
@commands.has_permissions(moderate_members=True)
async def cmd_timeout(ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
    if ctx.author.top_role <= member.top_role or member.id == ctx.guild.owner_id:
        return await ctx.send("❌ You cannot moderate a member with equal or higher authority.")
    if ctx.guild.me.top_role <= member.top_role:
        return await ctx.send("❌ Cannot timeout. Bot role is below member's highest role.")
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{reason} (By {ctx.author})")

        state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
        uid_str = str(member.id)
        state["user_mute_counts"][uid_str] = state["user_mute_counts"].get(uid_str, 0) + 1
        await save_state_to_memory(ctx.guild, data=state)

        await ctx.send(f"⏳ Timed out **{member.display_name}** for {minutes} min(s) | Total Mutes: `{state['user_mute_counts'][uid_str]}`")
    except discord.Forbidden:
        await ctx.send("❌ Failed to timeout. Check bot permissions and role order.")

@bot.command(name="purge", aliases=["clear"])
async def cmd_purge(ctx: commands.Context, amount: int):
    is_owner = ctx.author.id == ctx.guild.owner_id
    allowed_roles = {normalize_text(ADMIN_ROLE_NAME), normalize_text(AUTHORITY_ROLE_NAME)}
    user_roles = {normalize_text(r.name) for r in ctx.author.roles}
    
    if not (is_owner or ctx.author.guild_permissions.administrator or not user_roles.isdisjoint(allowed_roles)):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        return await ctx.send("❌ This command is restricted to the **Server Owner**, **Admins**, and **Authorities** only.", delete_after=6)

    if amount < 1 or amount > 100:
        return await ctx.send("⚠️ Specify an amount between 1 and 100 messages.", delete_after=5)
        
    try:
        await ctx.message.delete()
    except Exception:
        pass
        
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Purged **{len(deleted)}** message(s).", delete_after=5)

# ==============================================================================
# 12. DEPLOYMENT, SAFE CHANNELS & ROLE MANAGEMENT
# ==============================================================================

@bot.command(name="syncperms")
@commands.has_permissions(administrator=True)
async def cmd_syncperms(ctx: commands.Context):
    status = await ctx.send("⏳ **Enforcing server permission hierarchy...**")
    guild = ctx.guild
    updated, failed = [], []

    for rname, cfg in ROLE_PERMISSIONS_CONFIG.items():
        role = find_role_resilient(guild, rname) or await ensure_role_exists(guild, rname, cfg["color"], cfg["permissions"], cfg["hoist"])
        if role and guild.me.top_role > role:
            if role.permissions != cfg["permissions"] or role.hoist != cfg["hoist"]:
                try:
                    await role.edit(permissions=cfg["permissions"], hoist=cfg["hoist"], reason="Staff matrix sync")
                    updated.append(f"🛡️ Updated staff `{role.name}`")
                    await asyncio.sleep(0.35)
                except Exception as e:
                    failed.append(f"❌ `{role.name}`: {e}")
        elif role:
            failed.append(f"⚠️ `{role.name}` is positioned above the bot")

    for (low, high), cfg in LEVEL_TIER_ROLES.items():
        role = find_role_resilient(guild, cfg["name"]) or await ensure_role_exists(guild, cfg["name"], cfg["color"], cfg["permissions"], cfg["hoist"])
        if role and guild.me.top_role > role:
            if role.permissions != cfg["permissions"] or role.hoist != cfg["hoist"]:
                try:
                    await role.edit(permissions=cfg["permissions"], hoist=cfg["hoist"], reason="Tier matrix sync")
                    updated.append(f"⚡ Level {low}-{high} updated `{role.name}`")
                    await asyncio.sleep(0.35)
                except Exception as e:
                    failed.append(f"❌ `{role.name}`: {e}")
        elif role:
            failed.append(f"⚠️ `{role.name}` is positioned above the bot")

    embed = discord.Embed(
        title="🛡️ Permission Audit Results",
        description="\n".join(updated) if updated else "All role permissions are fully up to date.",
        color=discord.Color.green() if not failed else discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    if failed:
        embed.add_field(name="Hierarchy Conflicts", value="\n".join(failed), inline=False)
    await status.edit(content=None, embed=embed)

@bot.command(name="autorole_setup")
@commands.has_permissions(administrator=True)
async def cmd_autorole_setup(ctx: commands.Context):
    guild = ctx.guild
    msg = await ctx.send("⏳ **Auditing and provisioning all server roles...**")

    for rname, cfg in ROLE_PERMISSIONS_CONFIG.items():
        await ensure_role_exists(guild, rname, cfg["color"], cfg["permissions"], cfg["hoist"])

    for (low, high), cfg in LEVEL_TIER_ROLES.items():
        await ensure_role_exists(guild, cfg["name"], cfg["color"], cfg["permissions"], cfg["hoist"])

    for c_name, c_color in PRO_HEX_COLORS.items():
        await ensure_role_exists(guild, c_name, c_color)
    for g_name, g_color in GENDER_ROLES.items():
        await ensure_role_exists(guild, g_name, g_color)

    await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
    await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())
    await ensure_role_exists(guild, BOOSTER_ROLE_NAME, discord.Color.from_rgb(255, 105, 180))
    await ensure_role_exists(guild, VANITY_ROLE_NAME, discord.Color.from_rgb(120, 100, 180))
    await ensure_role_exists(guild, BUMP_ROLE_NAME, discord.Color.gold(), mentionable=True)
    await ensure_role_exists(guild, POLL_ROLE_NAME, discord.Color.red(), mentionable=True)
    await ensure_role_exists(guild, ROBLOX_ROLE_NAME, discord.Color.blue())

    await msg.edit(content="✅ **All server roles, staff permissions, and cosmetics successfully initialized!**")

@bot.command(name="resetroles")
@commands.has_permissions(administrator=True)
async def cmd_resetroles(ctx: commands.Context):
    guild = ctx.guild
    msg = await ctx.send("⏳ **Wiping all bot-managed roles and re-adding them...**")

    managed_names = set()
    for rname in ROLE_PERMISSIONS_CONFIG:
        managed_names.add(normalize_text(rname))
    for cfg in LEVEL_TIER_ROLES.values():
        managed_names.add(normalize_text(cfg["name"]))
    for c_name in PRO_HEX_COLORS:
        managed_names.add(normalize_text(c_name))
    for g_name in GENDER_ROLES:
        managed_names.add(normalize_text(g_name))
    for m_name in [OG_ROLE_NAME, VETERAN_ROLE_NAME, BOOSTER_ROLE_NAME, VANITY_ROLE_NAME, BUMP_ROLE_NAME, POLL_ROLE_NAME, ROBLOX_ROLE_NAME, "୨୧Newbie୨୧"]:
        managed_names.add(normalize_text(m_name))

    deleted_count = 0
    for role in guild.roles:
        if normalize_text(role.name) in managed_names and guild.me.top_role > role and role != guild.default_role:
            try:
                await role.delete(reason="Role reset command executed")
                deleted_count += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass

    for rname, cfg in ROLE_PERMISSIONS_CONFIG.items():
        await ensure_role_exists(guild, rname, cfg["color"], cfg["permissions"], cfg["hoist"])
    for (low, high), cfg in LEVEL_TIER_ROLES.items():
        await ensure_role_exists(guild, cfg["name"], cfg["color"], cfg["permissions"], cfg["hoist"])
    for c_name, c_color in PRO_HEX_COLORS.items():
        await ensure_role_exists(guild, c_name, c_color)
    for g_name, g_color in GENDER_ROLES.items():
        await ensure_role_exists(guild, g_name, g_color)

    await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
    await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())
    await ensure_role_exists(guild, BOOSTER_ROLE_NAME, discord.Color.from_rgb(255, 105, 180))
    await ensure_role_exists(guild, VANITY_ROLE_NAME, discord.Color.from_rgb(120, 100, 180))
    await ensure_role_exists(guild, BUMP_ROLE_NAME, discord.Color.gold(), mentionable=True)
    await ensure_role_exists(guild, POLL_ROLE_NAME, discord.Color.red(), mentionable=True)
    await ensure_role_exists(guild, ROBLOX_ROLE_NAME, discord.Color.blue())

    await msg.edit(content=f"✅ **Reset complete! Deleted `{deleted_count}` old roles and re-added all server roles fresh.**")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def cmd_setup_channels(ctx: commands.Context):
    guild = ctx.guild
    status = await ctx.send("⏳ **Checking blueprint and adding missing channels safely (existing channels are untouched)...**")

    created = 0
    for cat_data in EXTENDED_SERVER_BLUEPRINT:
        cat_name = cat_data["category"]
        category = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(cat_name), guild.categories)
        if not category:
            category = await guild.create_category(name=cat_name, reason="Blueprint Category Init")
            await asyncio.sleep(0.35)

        for ch in cat_data["channels"]:
            ch_name, ch_type, scheme = ch["name"], ch["type"], ch["scheme"]
            user_lim = ch.get("user_limit", 0)
            overwrites = generate_channel_overwrites(guild, scheme)

            target_list = guild.text_channels if ch_type == "text" else guild.voice_channels
            channel = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(ch_name) and c.category_id == category.id, target_list)

            if not channel:
                if ch_type == "text":
                    channel = await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites, reason="Adding missing blueprint channel")
                else:
                    channel = await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim, overwrites=overwrites, reason="Adding missing blueprint channel")
                created += 1
                await asyncio.sleep(0.35)

    embed = discord.Embed(
        title="✨ Channel Setup Complete",
        description=f"• **New Missing Channels Added:** `{created}`\n• **Existing Working Channels:** Left completely untouched ✅",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await status.edit(content=None, embed=embed)

@bot.command(name="removeadminrole")
@commands.has_permissions(administrator=True)
async def cmd_removeadminrole(ctx: commands.Context):
    old_role = discord.utils.find(lambda r: normalize_text(r.name) == "admin", ctx.guild.roles)
    highness = find_role_resilient(ctx.guild, ADMIN_ROLE_NAME)
    if not old_role:
        return await ctx.send("ℹ️ No plain `Admin` role exists.")

    if ctx.guild.me.top_role <= old_role:
        return await ctx.send("❌ Cannot modify `Admin`. Bot role must be higher.")

    status = await ctx.send("⏳ **Migrating legacy Admin role...**")
    migrated = 0
    if highness and ctx.guild.me.top_role > highness:
        for m in old_role.members:
            if highness not in m.roles:
                try:
                    await m.add_roles(highness, reason="Admin migration to Highness")
                    migrated += 1
                    await asyncio.sleep(0.35)
                except Exception:
                    pass

    try:
        await old_role.delete(reason="Legacy Admin purged")
        await status.edit(content=f"✅ Deleted **Admin** and transferred {migrated} member(s) to **{ADMIN_ROLE_NAME}**.")
    except Exception as e:
        await status.edit(content=f"❌ Failed to delete role: {e}")

@bot.command(name="communitypanel")
@commands.has_permissions(administrator=True)
async def cmd_communitypanel(ctx: commands.Context):
    embed = discord.Embed(
        title="✨ Self-Assignable Roles",
        description="Click below to toggle optional notification and community roles:\n\n📊 **Poll Pings** — Server poll alerts\n🎮 **Roblox Members** — Access to Roblox community chat\n\n*Click again to toggle off.*",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=CommunityRolesView())
    try:
        await ctx.message.delete()
    except Exception:
        pass

@bot.command(name="postcolors")
@commands.has_permissions(administrator=True)
async def cmd_postcolors(ctx: commands.Context):
    ch = discord.utils.find(lambda c: "colours" in normalize_text(c.name), ctx.guild.text_channels) or ctx.channel
    embed = discord.Embed(
        title="🎨 Customize Your Name Color",
        description="Select a color from the dropdown below to tint your username in chat.\n\n*Selecting 'Reset Color' removes your custom cosmetic role.*",
        color=discord.Color.from_rgb(255, 105, 180)
    )
    await ch.send(embed=embed, view=ColorView())
    try:
        await ctx.message.delete()
    except Exception:
        pass

@bot.command(name="postgender")
@commands.has_permissions(administrator=True)
async def cmd_postgender(ctx: commands.Context):
    embed = discord.Embed(
        title="✨ Identity Roles",
        description="Select your gender identity from the dropdown below to update your profile role.",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, view=GenderView())
    try:
        await ctx.message.delete()
    except Exception:
        pass

@bot.command(name="posttickets")
@commands.has_permissions(administrator=True)
@is_ticket_channel()
async def cmd_posttickets(ctx: commands.Context):
    embed = discord.Embed(
        title="🎫 Chill-Verse Support & Application Portal",
        description=(
            "Need assistance, want to report an issue, or looking to join the staff team?\n\n"
            "Select an option from the dropdown menu below to open your private ticket:\n\n"
            "🛡️ **Team Apply** — Submit a staff application\n"
            "📩 **Create Ticket** — General inquiries & support\n"
            "🆘 **Need Help** — Urgent assistance or reports"
        ),
        color=discord.Color.teal()
    )
    embed.set_footer(text="Confidential • Only staff and you can view your tickets.")
    await ctx.send(embed=embed, view=TicketLaunchView())
    try:
        await ctx.message.delete()
    except Exception:
        pass

@bot.command(name="confesspanel", aliases=["postconfession"])
@commands.has_permissions(administrator=True)
async def cmd_confesspanel(ctx: commands.Context):
    ch = discord.utils.find(lambda c: "confession" in normalize_text(c.name) and "panel" not in normalize_text(c.name), ctx.guild.text_channels) or ctx.channel
    embed = discord.Embed(
        title="💌 Anonymous Confession Portal",
        description="Click the button below or type `.confess` to open your 100% anonymous confession form.\n\n*Your identity, username, and ID are never logged, tracked, or shown anywhere.*",
        color=discord.Color.from_rgb(230, 70, 80)
    )
    embed.set_footer(text="100% Anonymous & Secure")
    await ch.send(embed=embed, view=ConfessionPanelView())
    try:
        await ctx.message.delete()
    except Exception:
        pass

@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def cmd_backup(ctx: commands.Context):
    status = await ctx.send("⏳ **Saving snapshot to `#bot-memory`...**")
    guild_id = ctx.guild.id
    state = bot.server_state.setdefault(guild_id, default_server_state())
    await save_state_to_memory(ctx.guild, data=state)
    
    bump_ts = state.get("last_bump_time", 0.0)
    bump_status = f"<t:{int(bump_ts)}:R>" if bump_ts > 0 else "No bumps recorded yet"
    
    embed = discord.Embed(
        title="📦 Backup Committed",
        description=f"✅ Server state backed up successfully.\n• **Last Bump Tracked:** {bump_status}",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await status.edit(content=None, embed=embed)

@bot.command(name="restorebackup")
@commands.has_permissions(administrator=True)
async def cmd_restorebackup(ctx: commands.Context):
    status = await ctx.send("⏳ **Restoring state from `#bot-memory`...**")
    data = await load_state_from_memory(ctx.guild)

    bot.server_state[ctx.guild.id] = data
    
    if data.get("last_bump_time", 0.0) > 0:
        await schedule_bump_reminder(ctx.guild)

    bump_ts = data.get("last_bump_time", 0.0)
    bump_status = f"<t:{int(bump_ts)}:R>" if bump_ts > 0 else "None"

    embed = discord.Embed(
        title="📦 Memory Backup Synchronized",
        description=(
            f"• **User XP Records:** `{len(data.get('user_xp', {}))}`\n"
            f"• **Tracked Levels:** `{len(data.get('user_levels', {}))}`\n"
            f"• **Total Confessions Logged:** `#{data.get('confession_counter', 0)}`\n"
            f"• **Active Warnings Logged:** `{len(data.get('user_warnings', {}))}`\n"
            f"• **Tracked Mutes:** `{len(data.get('user_mute_counts', {}))}`\n"
            f"• **Registered Birthdays:** `{len(data.get('user_birthdays', {}))}`\n"
            f"• **Last Recorded Bump:** {bump_status}\n"
            f"• **Maintenance Mode:** `{'Active 🔴' if data.get('maintenance_mode', False) else 'Inactive 🟢'}`\n"
            f"• **Active Tickets:** `{len(data.get('tickets', {}))}`"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await status.edit(content=None, embed=embed)

# ==============================================================================
# 13. APPLICATION ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ CRITICAL: DISCORD_TOKEN environment variable is not set!")
    else:
        bot.run(TOKEN)
        
