import asyncio
import json
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands

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
    (60, 60): {
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

# ==============================================================================
# 2. SERVER CHANNEL BLUEPRINT & MIGRATION SCHEMES
# ==============================================================================

EXTENDED_SERVER_BLUEPRINT = [
    {
        "category": "Info 🩵",
        "channels": [
            {"name": "📢・level-announcements", "type": "text", "scheme": "public_read"},
            {"name": "🎫・tickets",            "type": "text", "scheme": "public_read"},
            {"name": "🎨・colours",            "type": "text", "scheme": "public_read"}
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

CRITICAL_PROTECTED_CHANNELS = ["bot-memory", "bot_memory", "backup", "audit-log"]

LEGACY_ROLE_MIGRATION = {
    "admin": ADMIN_ROLE_NAME,
    "authority": AUTHORITY_ROLE_NAME,
    "head moderator": HEAD_MOD_ROLE_NAME,
    "moderator": MOD_ROLE_NAME,
    "trial mod": TRIAL_MOD_ROLE_NAME,
    "team": TEAM_ROLE_NAME,
    "og": OG_ROLE_NAME,
    "veteran": VETERAN_ROLE_NAME,
    "1 year veteran": VETERAN_ROLE_NAME,
    "bumppings": BUMP_ROLE_NAME,
    "pollpings": POLL_ROLE_NAME,
    "roblox": ROBLOX_ROLE_NAME,
    "male": "Male ★★",
    "female": "Female ★★",
    "non-binary": "Non-Binary",
    "newbie": "୨୧Newbie୨୧",
    "explorer": "୨ৎ ˖Explorer",
    "elite": "୨ৎ ˖ Elite",
    "champion": "୨ৎ ˖ Champion",
    "legend": "୨ৎ ˖ Legend",
    "sovereign": "୨ৎ ˖ Sovereign"
}

# ==============================================================================
# 3. TEXT NORMALIZATION & RESILIENT HELPERS
# ==============================================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\u200B-\u200D\uFEFF\u200E\u200F]", "", text)
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip().lower()

def clean_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", name)
    return " ".join(cleaned.split()).strip().lower()

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

# ==============================================================================
# 4. MEMORY STORAGE & SAFE BACKUP ENGINE (#bot-memory)
# ==============================================================================

memory_lock = asyncio.Lock()

class MemoryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        return super().default(obj)

def robust_memory_decoder(dct: dict):
    for key, value in dct.items():
        if isinstance(value, dict) and "__datetime__" in value:
            try:
                dct[key] = datetime.fromisoformat(value["__datetime__"])
            except (ValueError, TypeError):
                pass
        elif isinstance(value, str):
            if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
                try:
                    dct[key] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
    return dct

def migrate_legacy_state_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    if "users" in data:
        for user_id, user_info in data["users"].items():
            if "roles" in user_info and isinstance(user_info["roles"], list):
                updated_roles = []
                for rname in user_info["roles"]:
                    cleaned = normalize_text(rname)
                    updated_roles.append(LEGACY_ROLE_MIGRATION.get(cleaned, rname))
                user_info["roles"] = updated_roles
    data.setdefault("users", {})
    data.setdefault("tickets", {})
    data.setdefault("confessions", [])
    data.setdefault("afk", {})
    return data

async def save_state_to_memory(guild: discord.Guild, memory_channel_name: str = "bot-memory", data: dict = None):
    async with memory_lock:
        channel = discord.utils.find(lambda c: c.name == memory_channel_name, guild.text_channels)
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            try:
                channel = await guild.create_text_channel(name=memory_channel_name, overwrites=overwrites)
            except (discord.Forbidden, discord.HTTPException):
                return

        raw_json = json.dumps(data or {}, cls=MemoryEncoder, indent=2)
        chunks = [raw_json[i:i + 1950] for i in range(0, len(raw_json), 1950)]
        try:
            await channel.purge(limit=15)
            for chunk in chunks:
                await channel.send(f"```json\n{chunk}\n```")
        except (discord.Forbidden, discord.HTTPException):
            pass

async def load_state_from_memory(guild: discord.Guild, memory_channel_name: str = "bot-memory") -> dict:
    channel = discord.utils.find(lambda c: c.name == memory_channel_name, guild.text_channels)
    if not channel:
        return {}

    raw_chunks = []
    async for message in channel.history(limit=50, oldest_first=True):
        content = message.content.strip()
        if not content:
            continue
        clean_chunk = re.sub(r"^```(?:json)?\n?", "", content, flags=re.IGNORECASE)
        clean_chunk = re.sub(r"\n?```$", "", clean_chunk)
        raw_chunks.append(clean_chunk)

    if not raw_chunks:
        return {}

    try:
        raw_data = json.loads("".join(raw_chunks), object_hook=robust_memory_decoder)
        return migrate_legacy_state_payload(raw_data)
    except json.JSONDecodeError:
        for chunk in reversed(raw_chunks):
            try:
                raw_data = json.loads(chunk, object_hook=robust_memory_decoder)
                return migrate_legacy_state_payload(raw_data)
            except json.JSONDecodeError:
                continue
    return {}

# ==============================================================================
# 5. PERMISSION OVERWRITE ROUTER
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
# 6. PROGRESSION ENGINE (LEVELS & TENURE)
# ==============================================================================

xp_cooldowns: Dict[int, float] = {}

async def verify_member_tenure(member: discord.Member):
    if not member.joined_at or member.bot:
        return
    now = datetime.now(timezone.utc)
    if (now - member.joined_at).days >= 365:
        og_role = find_role_resilient(member.guild, OG_ROLE_NAME)
        vet_role = find_role_resilient(member.guild, VETERAN_ROLE_NAME)
        
        if not og_role:
            og_role = await ensure_role_exists(member.guild, OG_ROLE_NAME, discord.Color.dark_magenta())
        if not vet_role:
            vet_role = await ensure_role_exists(member.guild, VETERAN_ROLE_NAME, discord.Color.purple())

        roles_to_grant = []
        if og_role and og_role not in member.roles and member.guild.me.top_role > og_role:
            roles_to_grant.append(og_role)
        if vet_role and vet_role not in member.roles and member.guild.me.top_role > vet_role:
            roles_to_grant.append(vet_role)

        if roles_to_grant:
            try:
                await member.add_roles(*roles_to_grant, reason="Tenure: Reached 365-day server milestone")
                await add_xp(member, 1000, bypass_cooldown=True)
            except (discord.Forbidden, discord.HTTPException):
                pass

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
    if guild_id not in bot.server_state:
        bot.server_state[guild_id] = {}
    users_db = bot.server_state[guild_id].setdefault("users", {})
    user_data = users_db.setdefault(str(member.id), {"xp": 0, "level": 1, "total_xp": 0})

    user_data["xp"] += xp_amount
    user_data["total_xp"] = user_data.get("total_xp", 0) + xp_amount
    needed_xp = user_data["level"] * 300

    if user_data["xp"] >= needed_xp:
        user_data["level"] += 1
        user_data["xp"] -= needed_xp
        new_level = user_data["level"]

        await sync_member_level_tier(member, new_level)

        ann_ch = discord.utils.find(lambda c: "level-announcements" in normalize_text(c.name), guild.text_channels)
        if ann_ch:
            embed = discord.Embed(
                title="⚡ Level Advanced!",
                description=f"Congratulations {member.mention}, you reached **Level {new_level}**! 🎉\nNew role permissions and perks have been unlocked.",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ann_ch.send(content=f"🎉 {member.mention}", embed=embed)

        await save_state_to_memory(guild, data=bot.server_state[guild_id])

# ==============================================================================
# 7. INTERACTIVE PERSISTENT UI VIEWS
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

        target_role = find_role_resilient(guild, selected)
        if not target_role:
            target_role = await ensure_role_exists(guild, selected, PRO_HEX_COLORS[selected])

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

        target_role = find_role_resilient(guild, selected)
        if not target_role:
            target_role = await ensure_role_exists(guild, selected, GENDER_ROLES[selected])

        if target_role and guild.me.top_role > target_role:
            await member.add_roles(target_role, reason="Identity role self-assignment")
            await interaction.followup.send(f"✨ Assigned **{selected}**!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error assigning identity role. Hierarchy issue.", ephemeral=True)

class GenderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GenderSelect())

class TicketControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.followup.send("🔒 **Ticket closing in 5 seconds...**")
        
        guild_id = interaction.guild.id
        if guild_id in bot.server_state and "tickets" in bot.server_state[guild_id]:
            bot.server_state[guild_id]["tickets"].pop(str(interaction.channel.id), None)
            await save_state_to_memory(interaction.guild, data=bot.server_state[guild_id])

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

        clean_name = re.sub(r"[^\w-]", "", user.name.lower()) or str(user.id)
        ticket_ch_name = f"ticket-{clean_name[:20]}"
        if discord.utils.find(lambda c: c.name == ticket_ch_name, guild.text_channels):
            return await interaction.followup.send("⚠️ You already have an open support ticket.", ephemeral=True)

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
            
            guild_id = guild.id
            if guild_id not in bot.server_state:
                bot.server_state[guild_id] = {}
            tickets_db = bot.server_state[guild_id].setdefault("tickets", {})
            tickets_db[str(ch.id)] = {"user_id": user.id, "created_at": datetime.now(timezone.utc).isoformat()}
            await save_state_to_memory(guild, data=bot.server_state[guild_id])

            embed = discord.Embed(
                title="🎫 Support Portal",
                description=f"Welcome {user.mention}! Staff will assist you shortly.\nClick **Close Ticket** below when finished.",
                color=discord.Color.teal()
            )
            await ch.send(content=f"{user.mention}", embed=embed, view=TicketControlsView())
            await interaction.followup.send(f"✅ Ticket created: {ch.mention}", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send("❌ Could not create ticket channel.", ephemeral=True)

# ==============================================================================
# 8. BOT CLIENT & PERMISSION HELPERS
# ==============================================================================

class ChillVerseBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents, help_command=None)
        self.server_state: Dict[int, Any] = {}

    async def setup_hook(self):
        self.add_view(CommunityRolesView())
        self.add_view(ColorView())
        self.add_view(GenderView())
        self.add_view(TicketLaunchView())
        self.add_view(TicketControlsView())

bot = ChillVerseBot()

def is_staff_or_admin():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
        user_roles = {normalize_text(r.name) for r in ctx.author.roles}
        allowed = {normalize_text(r) for r in RESTRICTED_ADMIN_ROLES}
        return not user_roles.isdisjoint(allowed)
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

# ==============================================================================
# 9. LISTENERS (AFK, BUMP, BOOSTS, EXP, AUTO-REACTIONS, THREADS)
# ==============================================================================

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    for guild in bot.guilds:
        restored = await load_state_from_memory(guild)
        if restored:
            bot.server_state[guild.id] = restored
            print(f"✅ Backups restored for '{guild.name}'")
        for member in guild.members:
            if not member.bot:
                await verify_member_tenure(member)

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    newbie_role = find_role_resilient(member.guild, "୨୧Newbie୨୧")
    if not newbie_role:
        newbie_role = await ensure_role_exists(member.guild, "୨୧Newbie୨୧", discord.Color.teal())
    if newbie_role and member.guild.me.top_role > newbie_role:
        try:
            await member.add_roles(newbie_role, reason="Auto-assign on onboarding")
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
                color=discord.Color.nitro_pink(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            await ann_ch.send(content=f"🎉 {after.mention}", embed=embed)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        if message.author.id == 302050872383242240 or (message.author.bot and "bump" in message.content.lower()):
            success = "bump done" in message.content.lower()
            if not success and message.embeds:
                for emb in message.embeds:
                    desc = emb.description or ""
                    if "bump done" in desc.lower() or "thumbsup" in desc.lower():
                        success = True
                        break
            if success and message.guild:
                await message.channel.send("🚀 **Bump detected!** Next bump alert in 2 hours.", delete_after=10)
                asyncio.create_task(bump_reminder_task(message.guild, message.channel))
        return

    guild_id = message.guild.id
    afk_data = bot.server_state.get(guild_id, {}).get("afk", {})
    user_str = str(message.author.id)

    if user_str in afk_data:
        del afk_data[user_str]
        await message.channel.send(f"👋 Welcome back {message.author.mention}, I removed your AFK.", delete_after=10)
        await save_state_to_memory(message.guild, data=bot.server_state[guild_id])

    if message.mentions:
        for member in message.mentions:
            m_str = str(member.id)
            if m_str in afk_data and member.id != message.author.id:
                rec = afk_data[m_str]
                mins = int((time.time() - rec["timestamp"]) // 60)
                t_str = f"{mins}m ago" if mins > 0 else "just now"
                await message.channel.send(f"💤 **{member.display_name}** is AFK: {rec['reason']} *({t_str})*", delete_after=10)

    ch_name = normalize_text(message.channel.name)
    if "vouch" in ch_name:
        try:
            await message.add_reaction("⭐")
        except (discord.Forbidden, discord.HTTPException):
            pass
    elif "memes" in ch_name or "selfies" in ch_name or "photography" in ch_name:
        if message.attachments or "http" in message.content:
            try:
                await message.add_reaction("❤️")
                await message.add_reaction("🔥")
            except (discord.Forbidden, discord.HTTPException):
                pass
    elif "discussions" in ch_name and not isinstance(message.channel, discord.Thread):
        if message.type == discord.MessageType.default:
            try:
                thread_title = message.content[:40] if message.content else f"Discussion by {message.author.name}"
                await message.create_thread(name=f"💬・{thread_title}")
            except (discord.Forbidden, discord.HTTPException):
                pass

    await add_xp(message.author, 15)
    await bot.process_commands(message)

# ==============================================================================
# 10. SYSTEM & USER COMMANDS
# ==============================================================================

async def bump_reminder_task(guild: discord.Guild, channel: discord.TextChannel):
    await asyncio.sleep(7200)
    role = find_role_resilient(guild, BUMP_ROLE_NAME)
    ping = role.mention if role else "@here"
    embed = discord.Embed(
        title="⏰ Time to Bump!",
        description="The 2-hour cooldown has passed. Run `/bump` to grow the server! 🚀",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    await channel.send(content=f"🔔 {ping}", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))

@bot.command(name="afk")
async def cmd_afk(ctx: commands.Context, *, reason: str = "AFK"):
    try:
        await ctx.message.delete(delay=10)
    except (discord.Forbidden, discord.HTTPException):
        pass

    guild_id = ctx.guild.id
    if guild_id not in bot.server_state:
        bot.server_state[guild_id] = {}
    afk_data = bot.server_state[guild_id].setdefault("afk", {})
    afk_data[str(ctx.author.id)] = {"reason": reason, "timestamp": time.time()}

    await ctx.send(f"💤 {ctx.author.mention}, I set your AFK: **{reason}**", delete_after=10)
    await save_state_to_memory(ctx.guild, data=bot.server_state[guild_id])

@bot.command(name="bump")
async def cmd_bump(ctx: commands.Context):
    try:
        await ctx.message.delete(delay=10)
    except (discord.Forbidden, discord.HTTPException):
        pass

    await ctx.send(f"👊 {ctx.author.mention}, bump logged! I'll ping **{BUMP_ROLE_NAME}** in 2 hours.", delete_after=10)
    await add_xp(ctx.author, 250, bypass_cooldown=True)
    asyncio.create_task(bump_reminder_task(ctx.guild, ctx.channel))

@bot.command(name="confess")
async def cmd_confess(ctx: commands.Context, *, confession_text: str):
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    target_ch = discord.utils.find(lambda c: "confession" in normalize_text(c.name), ctx.guild.text_channels)
    if not target_ch:
        return await ctx.send("❌ Confession channel not found.", delete_after=10)

    guild_id = ctx.guild.id
    if guild_id not in bot.server_state:
        bot.server_state[guild_id] = {}
    confs = bot.server_state[guild_id].setdefault("confessions", [])
    cid = len(confs) + 1
    confs.append({"id": cid, "content": confession_text, "timestamp": datetime.now(timezone.utc).isoformat()})

    embed = discord.Embed(
        title=f"💌 Anonymous Confession #{cid}",
        description=f"*{confession_text}*",
        color=discord.Color.from_rgb(230, 70, 80),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text="Send yours via .confess <message>")
    msg = await target_ch.send(embed=embed)
    await msg.add_reaction("❤️")
    await msg.add_reaction("💔")

    await ctx.send(f"🤫 {ctx.author.mention}, your confession was dispatched!", delete_after=10)
    await save_state_to_memory(ctx.guild, data=bot.server_state[guild_id])

@bot.command(name="rank", aliases=["level", "xp"])
async def cmd_rank(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    guild_id = ctx.guild.id
    users_db = bot.server_state.get(guild_id, {}).get("users", {})
    user_data = users_db.get(str(target.id), {"xp": 0, "level": 1, "total_xp": 0})

    lvl = user_data["level"]
    current_xp = user_data["xp"]
    needed_xp = lvl * 300
    progress = min(int((current_xp / max(needed_xp, 1)) * 10), 10)
    bar = "▰" * progress + "▱" * (10 - progress)

    embed = discord.Embed(title=f"📊 Rank Card — {target.display_name}", color=discord.Color.teal())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Level", value=f"**{lvl}**", inline=True)
    embed.add_field(name="Tier Progress", value=f"{current_xp} / {needed_xp} XP", inline=True)
    embed.add_field(name="Progress Bar", value=f"`[{bar}]`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def cmd_leaderboard(ctx: commands.Context):
    guild_id = ctx.guild.id
    users_db = bot.server_state.get(guild_id, {}).get("users", {})
    if not users_db:
        return await ctx.send("ℹ️ No XP records found yet.")

    sorted_users = sorted(users_db.items(), key=lambda item: item[1].get("total_xp", 0), reverse=True)[:10]
    lines = []
    for rank, (uid, data) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        lines.append(f"**#{rank}** {name} — Level **{data.get('level', 1)}** ({data.get('total_xp', 0):,} total XP)")

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
    except (discord.Forbidden, discord.HTTPException):
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
    except (discord.Forbidden, discord.HTTPException):
        pass

    embed = discord.Embed(
        title="🤖 Chill-Verse Complete Command Matrix",
        description="Comprehensive catalog of all administrative, staff, and public user commands:",
        color=discord.Color.teal(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="🏗️ Setup & Infrastructure",
        value=(
            "• `.setup_channels` — Deploys stylized architecture & purges legacy channels\n"
            "• `.syncperms` — Enforces staff and tier permission matrices\n"
            "• `.autorole_setup` — Provisions all server roles and cosmetic tiers"
        ),
        inline=False
    )
    embed.add_field(
        name="🎨 Panels & UI Management",
        value=(
            "• `.communitypanel` — Spawns PollPings and Roblox role picker\n"
            "• `.postcolors` — Spawns the chat color selection dropdown\n"
            "• `.postgender` — Spawns the identity role dropdown\n"
            "• `.posttickets` — Spawns the support ticket launcher"
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Moderation Suite",
        value=(
            "• `.kick <member>` — Kicks a user from the server\n"
            "• `.ban <member>` — Bans a user from the server\n"
            "• `.timeout <member> <mins>` — Mutes a user temporarily\n"
            "• `.purge <amount>` — Clears up to 100 messages"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Public & Community Features",
        value=(
            "• `.rank` — Displays user level, XP progress, and card\n"
            "• `.leaderboard` — Shows top 10 most active members by XP\n"
            "• `.afk <reason>` — Sets AFK status with auto-removal and alerts\n"
            "• `.bump` — Logs manual server bump and 2-hour reminder timer\n"
            "• `.confess <msg>` — Posts secure anonymous confession\n"
            "• `.poll <question>` — Dispatches an official server poll"
        ),
        inline=False
    )
    embed.add_field(
        name="📦 System & Backup",
        value=(
            "• `.backup` — Commits server state snapshot to `#bot-memory`\n"
            "• `.restorebackup` — Synchronizes state from `#bot-memory`\n"
            "• `.removeadminrole` — Migrates legacy Admin holders to Highness"
        ),
        inline=False
    )
    embed.set_footer(text="Restricted exclusively to Team <3 channels.")
    await ctx.send(embed=embed)

# ==============================================================================
# 11. MODERATION SUITE
# ==============================================================================

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
        await ctx.send(f"⏳ Timed out **{member.display_name}** for {minutes} minute(s) | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Failed to timeout. Check bot permissions and role order.")

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def cmd_purge(ctx: commands.Context, amount: int):
    if amount < 1 or amount > 100:
        return await ctx.send("⚠️ Specify an amount between 1 and 100 messages.", delete_after=5)
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Purged **{len(deleted)}** message(s).", delete_after=5)

# ==============================================================================
# 12. DEPLOYMENT, PERMISSION SYNC & MIGRATION
# ==============================================================================

@bot.command(name="syncperms")
@commands.has_permissions(administrator=True)
async def cmd_syncperms(ctx: commands.Context):
    status = await ctx.send("⏳ **Enforcing server permission hierarchy...**")
    guild = ctx.guild
    updated, failed = [], []

    for rname, cfg in ROLE_PERMISSIONS_CONFIG.items():
        role = find_role_resilient(guild, rname)
        if not role:
            role = await ensure_role_exists(guild, rname, cfg["color"], cfg["permissions"], cfg["hoist"])
            updated.append(f"✨ Created staff role `{rname}`")
            await asyncio.sleep(0.35)
            continue

        if guild.me.top_role > role:
            if role.permissions != cfg["permissions"] or role.hoist != cfg["hoist"]:
                try:
                    await role.edit(permissions=cfg["permissions"], hoist=cfg["hoist"], reason="Staff matrix sync")
                    updated.append(f"🛡️ Updated staff `{role.name}`")
                    await asyncio.sleep(0.35)
                except Exception as e:
                    failed.append(f"❌ `{role.name}`: {e}")
        else:
            failed.append(f"⚠️ `{role.name}` is positioned above the bot")

    for (low, high), cfg in LEVEL_TIER_ROLES.items():
        role = find_role_resilient(guild, cfg["name"])
        if not role:
            role = await ensure_role_exists(guild, cfg["name"], cfg["color"], cfg["permissions"], cfg["hoist"])
            updated.append(f"✨ Created tier `{cfg['name']}`")
            await asyncio.sleep(0.35)
            continue

        if guild.me.top_role > role:
            if role.permissions != cfg["permissions"] or role.hoist != cfg["hoist"]:
                try:
                    await role.edit(permissions=cfg["permissions"], hoist=cfg["hoist"], reason="Tier matrix sync")
                    updated.append(f"⚡ Level {low}-{high} updated `{role.name}`")
                    await asyncio.sleep(0.35)
                except Exception as e:
                    failed.append(f"❌ `{role.name}`: {e}")
        else:
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
    await ensure_role_exists(guild, BOOSTER_ROLE_NAME, discord.Color.nitro_pink())
    await ensure_role_exists(guild, VANITY_ROLE_NAME, discord.Color.from_rgb(120, 100, 180))
    await ensure_role_exists(guild, BUMP_ROLE_NAME, discord.Color.gold(), mentionable=True)
    await ensure_role_exists(guild, POLL_ROLE_NAME, discord.Color.red(), mentionable=True)
    await ensure_role_exists(guild, ROBLOX_ROLE_NAME, discord.Color.blue())

    await msg.edit(content="✅ **All server roles, staff permissions, and cosmetics successfully initialized!**")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def cmd_setup_channels(ctx: commands.Context):
    guild = ctx.guild
    status = await ctx.send("⏳ **Step 1/3: Deploying new stylized architecture & channel locks...**")

    preserved_channels = set()
    preserved_categories = set()
    created, synced, purged = 0, 0, 0

    for cat_data in EXTENDED_SERVER_BLUEPRINT:
        cat_name = cat_data["category"]
        category = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(cat_name), guild.categories)
        if not category:
            category = await guild.create_category(name=cat_name, reason="Blueprint Category Init")
            await asyncio.sleep(0.35)
        preserved_categories.add(category.id)

        for ch in cat_data["channels"]:
            ch_name, ch_type, scheme = ch["name"], ch["type"], ch["scheme"]
            user_lim = ch.get("user_limit", 0)
            overwrites = generate_channel_overwrites(guild, scheme)

            target_list = guild.text_channels if ch_type == "text" else guild.voice_channels
            channel = discord.utils.find(lambda c: c.name == ch_name and c.category_id == category.id, target_list)

            if not channel:
                if ch_type == "text":
                    channel = await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites)
                else:
                    channel = await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim, overwrites=overwrites)
                created += 1
                await asyncio.sleep(0.35)
            else:
                for target, ow in overwrites.items():
                    await channel.set_permissions(target, overwrite=ow)
                if ch_type == "voice" and channel.user_limit != user_lim:
                    await channel.edit(user_limit=user_lim)
                synced += 1
                await asyncio.sleep(0.35)

            if channel:
                preserved_channels.add(channel.id)

    await status.edit(content="⏳ **Step 2/3: Purging legacy and duplicate channels...**")
    blueprint_slugs = {clean_slug(ch["name"]) for cat in EXTENDED_SERVER_BLUEPRINT for ch in cat["channels"]}
    for ch in list(guild.text_channels) + list(guild.voice_channels):
        if ch.id in preserved_channels:
            continue
        if any(p in ch.name.lower() for p in CRITICAL_PROTECTED_CHANNELS) or ch.name.lower().startswith("ticket-"):
            continue

        if clean_slug(ch.name) in blueprint_slugs or (ch.category and ch.category.id in preserved_categories):
            try:
                await ch.delete(reason="Purged legacy channel replaced by blueprint")
                purged += 1
                await asyncio.sleep(0.5)
            except (discord.Forbidden, discord.HTTPException):
                pass

    await status.edit(content="⏳ **Step 3/3: Cleaning up empty categories...**")
    for cat in guild.categories:
        if cat.id not in preserved_categories and len(cat.channels) == 0:
            try:
                await cat.delete(reason="Purged empty category")
                await asyncio.sleep(0.35)
            except (discord.Forbidden, discord.HTTPException):
                pass

    embed = discord.Embed(
        title="🧹 Channel Replacement Complete",
        description=f"• **New Channels Deployed:** `{created}`\n• **Permissions Synchronized:** `{synced}`\n• **Legacy Channels Purged:** `{purged}`",
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
    except (discord.Forbidden, discord.HTTPException):
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
    except (discord.Forbidden, discord.HTTPException):
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
    except (discord.Forbidden, discord.HTTPException):
        pass

@bot.command(name="posttickets")
@commands.has_permissions(administrator=True)
async def cmd_posttickets(ctx: commands.Context):
    ch = discord.utils.find(lambda c: "tickets" in normalize_text(c.name), ctx.guild.text_channels) or ctx.channel
    embed = discord.Embed(
        title="🎫 Server Support & Assistance",
        description="Need assistance or have a server inquiry?\nClick the button below to open a private ticket with staff.",
        color=discord.Color.teal()
    )
    await ch.send(embed=embed, view=TicketLaunchView())
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def cmd_backup(ctx: commands.Context):
    status = await ctx.send("⏳ **Saving snapshot to `#bot-memory`...**")
    guild_id = ctx.guild.id
    if guild_id in bot.server_state:
        await save_state_to_memory(ctx.guild, data=bot.server_state[guild_id])
        await status.edit(content="✅ **Server state backup committed successfully.**")
    else:
        await status.edit(content="ℹ️ No local state found to back up.")

@bot.command(name="restorebackup")
@commands.has_permissions(administrator=True)
async def cmd_restorebackup(ctx: commands.Context):
    status = await ctx.send("⏳ **Restoring state from `#bot-memory`...**")
    data = await load_state_from_memory(ctx.guild)
    if not data:
        return await status.edit(content="❌ No valid backup found in `#bot-memory`.")

    bot.server_state[ctx.guild.id] = data
    embed = discord.Embed(
        title="📦 Memory Backup Synchronized",
        description=f"• **User Records:** `{len(data.get('users', {}))}`\n• **Active Tickets:** `{len(data.get('tickets', {}))}`\n• **Logged Confessions:** `{len(data.get('confessions', []))}`\n• **Active AFK Records:** `{len(data.get('afk', {}))}`",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await status.edit(content=None, embed=embed)

# ==============================================================================
# 13. APPLICATION ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    bot.run(TOKEN)
