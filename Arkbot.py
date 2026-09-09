import asyncio
import io
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands, tasks

# ==============================================================================
# 1. SERVER ROLES & PERMISSION MATRIX CONFIGURATION
# ==============================================================================

ADMIN_ROLE_NAME     = "୨୧ Highness ☕⸝⸝﹗"
AUTHORITY_ROLE_NAME = "·.✦Authority✦.·"
HEAD_MOD_ROLE_NAME  = "✦•┈๑⋅⋯Head Moderator⋯⋅๑┈•✦"
MOD_ROLE_NAME       = "⋆. 𐙚˚࿔ 𝒎𝒐𝒅𝒆𝒓𝒂𝒕𝒐𝒓 𝜗𝜚˚⋆"
TRIAL_MOD_ROLE_NAME = "☆⋆｡Trial mod 𖦹°‧★"
TEAM_ROLE_NAME      = "𖦹°‧★ ⏜︵   𝒄𝒉𝒊𝒍𝒍-𝒗𝒆𝒓𝒔𝒆 𝒕𝒆𝒂𝒎    ⏜︵ 𖦹°‧★"

RESTRICTED_ADMIN_ROLES = [
    ADMIN_ROLE_NAME,
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

# ==============================================================================
# 3. DATABASE STATE & MEMORY RETENTION (#bot-memory: 3-file rolling retention)
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
        "announced_birthdays": {},
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
        channel = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(memory_channel_name), guild.text_channels)
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, attach_files=True, read_message_history=True
                )
            }
            try:
                channel = await guild.create_text_channel(name=memory_channel_name, overwrites=overwrites)
            except (discord.Forbidden, discord.HTTPException):
                return

        payload = data or default_server_state()
        raw_json = json.dumps(payload, indent=2)
        file_bytes = io.BytesIO(raw_json.encode('utf-8'))
        filename = f"backup_{guild.id}.json"
        
        try:
            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            await channel.send(
                content=f"💾 **[DATABASE STATE SYNC]** `{timestamp_str}`",
                file=discord.File(file_bytes, filename=filename)
            )

            # Rolling Retention: Keep strictly the 3 newest backup posts
            backup_messages = []
            async for msg in channel.history(limit=35):
                if msg.attachments and any(a.filename.endswith(".json") for a in msg.attachments):
                    backup_messages.append(msg)
                elif "DATABASE STATE SYNC" in msg.content:
                    backup_messages.append(msg)

            if len(backup_messages) > 3:
                for old_msg in backup_messages[3:]:
                    try:
                        await old_msg.delete()
                        await asyncio.sleep(0.3)
                    except Exception:
                        pass
        except (discord.Forbidden, discord.HTTPException):
            pass

async def load_state_from_memory(guild: discord.Guild, memory_channel_name: str = "bot-memory") -> dict:
    channel = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(memory_channel_name), guild.text_channels)
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
    roblox_role = find_role_resilient(guild, ROBLOX_ROLE_NAME)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
            manage_permissions=True, embed_links=True, attach_files=True
        )
    }

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
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(send_messages=True)
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
    elif scheme == "public_voice":
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True, stream=True
        )
    elif scheme == "vip_voice":
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True, stream=True
        )
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                priority_speaker=True, move_members=True, mute_members=True
            )
    elif scheme == "music_voice":
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True, stream=False, use_soundboard=False
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
    return overwrites

# ==============================================================================
# 5. PROGRESSION & MILESTONES ENGINE
# ==============================================================================

xp_cooldowns: Dict[int, float] = {}

async def verify_member_tenure(member: discord.Member, auto_save: bool = True) -> bool:
    if not member.joined_at or member.bot or not member.guild:
        return False
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
                except (discord.Forbidden, discord.HTTPException):
                    pass

            state["last_anniversary"][str(member.id)] = current_year
            if auto_save:
                await save_state_to_memory(guild, data=state)
            return True
    return False

async def sync_member_level_tier(member: discord.Member, new_level: int):
    guild = member.guild
    target_tier_data = None
    for (min_lvl, max_lvl), config in LEVEL_TIER_ROLES.items():
        if min_lvl <= new_level <= max_lvl or (max_lvl == 70 and new_level >= 60):
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
    except (discord.Forbidden, discord.HTTPException):
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

    leveled_up = False
    # Handles multi-level advancements cleanly without skipping thresholds
    while curr_lvl < MAX_LEVEL and curr_xp >= (curr_lvl * 300):
        curr_xp -= (curr_lvl * 300)
        curr_lvl += 1
        leveled_up = True

    state["user_xp"][uid_str] = curr_xp
    state["user_levels"][uid_str] = curr_lvl

    if leveled_up:
        await sync_member_level_tier(member, curr_lvl)

        ann_ch = discord.utils.find(lambda c: "level-announcements" in normalize_text(c.name), guild.text_channels)
        if ann_ch:
            embed = discord.Embed(
                title="⚡ Level Advanced!",
                description=f"Congratulations {member.mention}, you reached **Level {curr_lvl}**! 🎉\nNew role permissions and perks have been unlocked.",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await ann_ch.send(content=f"🎉 {member.mention}", embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

        await save_state_to_memory(guild, data=state)

# ==============================================================================
# 6. INTERACTIVE PANELS, MODALS & VIEWS
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
            await interaction.followup.send("❌ Cannot assign color. Hierarchy conflict.", ephemeral=True)

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
        placeholder="Type your anonymous confession here...",
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
        embed.set_footer(text="Submit yours via the confession form panel!")
        try:
            msg = await target_ch.send(embed=embed)
            await msg.add_reaction("❤️")
            await msg.add_reaction("💔")
            await interaction.followup.send("🤫 Your anonymous confession has been dispatched successfully!", ephemeral=True)
            await save_state_to_memory(guild, data=state)
        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"❌ Failed to dispatch confession: {e}", ephemeral=True)

class ConfessionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Write Confession", style=discord.ButtonStyle.danger, emoji="💌", custom_id="btn_open_confession_modal")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfessionModal())

class TicketControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.closing = False

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.closing:
            return await interaction.response.send_message("⚠️ This ticket is already in the process of closing.", ephemeral=True)
        self.closing = True
        
        await interaction.response.send_message("🔒 **Ticket closing in 5 seconds...**")
        
        guild_id = interaction.guild.id
        state = bot.server_state.setdefault(guild_id, default_server_state())
        state["tickets"].pop(str(interaction.channel.id), None)
        await save_state_to_memory(interaction.guild, data=state)

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Closed by {interaction.user}")
        except (discord.Forbidden, discord.HTTPException):
            pass

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.success, emoji="📩", custom_id="btn_ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild, user = interaction.guild, interaction.user

        guild_id = guild.id
        state = bot.server_state.setdefault(guild_id, default_server_state())

        for ch_id, t_info in list(state.get("tickets", {}).items()):
            if t_info.get("user_id") == user.id:
                existing_ch = guild.get_channel(int(ch_id))
                if existing_ch:
                    return await interaction.followup.send(f"⚠️ You already have an open ticket in {existing_ch.mention}.", ephemeral=True)

        clean_name = re.sub(r"[^\w-]", "", user.name.lower()) or str(user.id)
        ticket_ch_name = f"ticket-{clean_name[:20]}"

        category = discord.utils.find(lambda c: "team" in normalize_text(c.name), guild.categories)
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
            ch = await guild.create_text_channel(name=ticket_ch_name, category=category, overwrites=overwrites, reason="Support ticket open")
            state["tickets"][str(ch.id)] = {"user_id": user.id, "created_at": datetime.now(timezone.utc).isoformat()}
            await save_state_to_memory(guild, data=state)

            embed = discord.Embed(
                title="🎫 Support Portal",
                description=f"Welcome {user.mention}! Staff will assist you shortly.\nClick **Close Ticket** below when finished.",
                color=discord.Color.teal()
            )
            await ch.send(content=f"{user.mention}", embed=embed, view=TicketControlsView())
            await interaction.followup.send(f"✅ Ticket created: {ch.mention}", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send("❌ Could not create ticket channel. Verify permissions.", ephemeral=True)

# ==============================================================================
# 7. BOT CLIENT SETUP & AUTOMATED LOOPS
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
            try:
                state = self.server_state.get(guild.id)
                if state:
                    await save_state_to_memory(guild, data=state)
            except Exception as e:
                print(f"⚠️ Automated backup failed for guild '{guild.name}': {e}")

    @auto_backup_loop.before_loop
    async def before_auto_backup(self):
        await self.wait_until_ready()

    @tasks.loop(hours=1)
    async def daily_birthday_check(self):
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%d-%m")
        current_year = str(now.year)
        
        for guild in self.guilds:
            try:
                state = self.server_state.get(guild.id, {})
                birthdays = state.get("user_birthdays", {})
                announced = state.setdefault("announced_birthdays", {})
                bday_ch = discord.utils.find(lambda c: "birthdays" in normalize_text(c.name), guild.text_channels)
                if not bday_ch:
                    continue

                updated = False
                for uid, bday in birthdays.items():
                    if bday == today_str and announced.get(str(uid)) != current_year:
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
                                announced[str(uid)] = current_year
                                updated = True
                            except (discord.Forbidden, discord.HTTPException):
                                pass
                if updated:
                    await save_state_to_memory(guild, data=state)
            except Exception as e:
                print(f"⚠️ Birthday verification error for guild '{guild.name}': {e}")

    @daily_birthday_check.before_loop
    async def before_bday_check(self):
        await self.wait_until_ready()

bot = ChillVerseBot()

def is_staff_or_admin():
    async def predicate(ctx: commands.Context) -> bool:
        return is_staff_member(ctx.author)
    return commands.check(predicate)

def is_team_channel():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        in_team_cat = ctx.channel.category and "team" in normalize_text(ctx.channel.category.name)
        in_team_ch = "team" in normalize_text(ctx.channel.name) or "bump" in normalize_text(ctx.channel.name)
        if in_team_cat or in_team_ch:
            return True
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await ctx.send("❌ This command can only be used inside **`Team <3`** channels.", delete_after=5)
        return False
    return commands.check(predicate)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"⚠️ Missing required parameter: `{error.param.name}`", delete_after=8)
    if isinstance(error, commands.BadArgument):
        return await ctx.send(f"⚠️ Invalid argument provided: {error}", delete_after=8)
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌ You lack the necessary permissions to execute this command.", delete_after=8)
    if isinstance(error, commands.BotMissingPermissions):
        return await ctx.send(f"❌ The bot lacks required permissions: `{', '.join(error.missing_permissions)}`", delete_after=8)
    
    print(f"❌ Unhandled Command Error [{ctx.command}]: {error}")
    try:
        await ctx.send(f"⚠️ Error executing command: `{error}`", delete_after=10)
    except Exception:
        pass

# ==============================================================================
# 8. BUMP SCHEDULER & LISTENERS
# ==============================================================================

async def schedule_bump_reminder(guild: discord.Guild, channel: Optional[discord.TextChannel] = None):
    if guild.id in active_bump_tasks and not active_bump_tasks[guild.id].done():
        try:
            active_bump_tasks[guild.id].cancel()
        except Exception:
            pass

    async def _runner():
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
                description="The 2-hour cooldown has passed. Run `/bump` to grow the server! 🚀",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            try:
                await bump_ch.send(content=f"🔔 {ping}", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
            except (discord.Forbidden, discord.HTTPException):
                pass

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

        modified = False
        for member in guild.members:
            if not member.bot:
                if await verify_member_tenure(member, auto_save=False):
                    modified = True
        if modified:
            await save_state_to_memory(guild, data=bot.server_state[guild.id])

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    newbie_role = find_role_resilient(member.guild, "୨୧Newbie୨୧") or await ensure_role_exists(member.guild, "୨୧Newbie୨୧", discord.Color.teal())
    if newbie_role and member.guild.me.top_role > newbie_role:
        try:
            await member.add_roles(newbie_role, reason="Auto-assign on onboarding")
        except (discord.Forbidden, discord.HTTPException):
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
        except (discord.Forbidden, discord.HTTPException):
            pass

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if not before.premium_since and after.premium_since:
        booster_role = find_role_resilient(after.guild, BOOSTER_ROLE_NAME)
        if booster_role and booster_role not in after.roles and after.guild.me.top_role > booster_role:
            try:
                await after.add_roles(booster_role, reason="Server boost perk")
            except (discord.Forbidden, discord.HTTPException):
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
            except (discord.Forbidden, discord.HTTPException):
                pass

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        # Intercept automated bump bot success notifications
        if message.author.id == 302050872383242240 or (message.author.bot and "bump" in message.content.lower()):
            success = "bump done" in message.content.lower()
            if not success and message.embeds:
                for emb in message.embeds:
                    desc = emb.description or ""
                    if "bump done" in desc.lower() or "thumbsup" in desc.lower() or "👍" in desc:
                        success = True
                        break
            if success and message.guild:
                state = bot.server_state.setdefault(message.guild.id, default_server_state())
                state["last_bump_time"] = time.time()
                await save_state_to_memory(message.guild, data=state)
                await message.channel.send("🚀 **Bump detected!** Next bump alert scheduled in 2 hours.", delete_after=10)
                await schedule_bump_reminder(message.guild, message.channel)
        return

    guild_id = message.guild.id
    state = bot.server_state.setdefault(guild_id, default_server_state())

    # Maintenance Lock Check
    if state.get("maintenance_mode", False) and not is_staff_member(message.author):
        if message.content.startswith("."):
            await message.channel.send("🚧 **Server is currently in Maintenance Mode.** Commands are restricted to staff.", delete_after=6)
        return

    user_str = str(message.author.id)
    # Check AFK return: do not trigger if user is executing .afk command
    if user_str in state["afk_users"] and not message.content.strip().startswith(f"{bot.command_prefix}afk"):
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

    # When someone mentions an AFK user
    if message.mentions:
        for member in set(message.mentions):
            m_str = str(member.id)
            if m_str in state
