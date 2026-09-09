import asyncio
import io
import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import discord
from discord.ext import commands, tasks

# ==============================================================================
# 1. SERVER ROLES & PERMISSION MATRIX CONFIGURATION (ORIGINAL – UNCHANGED)
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
VANITY_ROLE_NAME    = "🗡 ׄ ݊ ݂ Always-in-nasheֹ  ۪ ֹ ᮫"   # (unused in code but kept)
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
# 2. TEXT NORMALIZATION & RESILIENT HELPERS (UNCHANGED)
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

class StateManager:
    """Manages server state with automatic backup to a dedicated text channel."""
    VERSION = 2

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._dirty = False

    @classmethod
    def default_state(cls) -> Dict[str, Any]:
        return {
            "version": cls.VERSION,
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
            "tickets": {},
        }

    async def load(self) -> None:
        channel = self._get_memory_channel()
        if not channel:
            channel = await self._create_memory_channel()
            if not channel:
                self.data = self.default_state()
                return

        async for msg in channel.history(limit=30):
            if msg.attachments:
                for att in msg.attachments:
                    if att.filename.endswith(".json"):
                        try:
                            raw = await att.read()
                            data = json.loads(raw.decode("utf-8"))
                            self.data = self._migrate(data)
                            return
                        except Exception:
                            continue
            content = msg.content.strip()
            if content.startswith("```") and content.endswith("```"):
                try:
                    json_str = re.sub(r"^```(?:json)?\n?", "", content)
                    json_str = re.sub(r"\n?```$", "", json_str)
                    data = json.loads(json_str)
                    self.data = self._migrate(data)
                    return
                except Exception:
                    continue

        self.data = self.default_state()

    async def save(self) -> None:
        async with self._lock:
            if not self._dirty:
                return
            channel = self._get_memory_channel()
            if not channel:
                channel = await self._create_memory_channel()
                if not channel:
                    return

            self.data["version"] = self.VERSION
            raw = json.dumps(self.data, indent=2, default=str)
            file = discord.File(io.BytesIO(raw.encode("utf-8")), filename=f"backup_{self.guild.id}.json")
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            try:
                await channel.send(
                    content=f"💾 **DATABASE STATE SYNC** `{timestamp}`",
                    file=file
                )
                self._dirty = False
                # Rolling retention: keep newest 3
                backups = []
                async for msg in channel.history(limit=35):
                    if msg.attachments and any(a.filename.endswith(".json") for a in msg.attachments):
                        backups.append(msg)
                    elif "DATABASE STATE SYNC" in msg.content:
                        backups.append(msg)
                if len(backups) > 3:
                    for old in backups[3:]:
                        try:
                            await old.delete()
                            await asyncio.sleep(0.3)
                        except Exception:
                            pass
            except Exception:
                pass

    def mark_dirty(self) -> None:
        self._dirty = True

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.mark_dirty()

    def update(self, key: str, value: Any) -> None:
        self.data.update({key: value})
        self.mark_dirty()

    def _get_memory_channel(self) -> Optional[discord.TextChannel]:
        return discord.utils.find(
            lambda c: normalize_text(c.name) == normalize_text("bot-memory"),
            self.guild.text_channels
        )

    async def _create_memory_channel(self) -> Optional[discord.TextChannel]:
        if not self.guild.me.guild_permissions.manage_channels:
            return None
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, attach_files=True, read_message_history=True
            )
        }
        try:
            return await self.guild.create_text_channel(
                name="bot-memory",
                overwrites=overwrites
            )
        except Exception:
            return None

    def _migrate(self, data: dict) -> dict:
        default = self.default_state()
        result = default.copy()
        for key in default:
            if key in data:
                result[key] = data[key]
        if "users" in data and isinstance(data["users"], dict):
            for uid, udata in data["users"].items():
                if isinstance(udata, dict):
                    result.setdefault("user_xp", {})[str(uid)] = udata.get("xp", 0)
                    result.setdefault("user_levels", {})[str(uid)] = udata.get("level", 1)
        result["version"] = self.VERSION
        return result

# ==============================================================================
# 4. PERMISSION OVERWRITES (ORIGINAL – UNCHANGED)
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
# 5. BOT CLASS & CORE LOGIC
# ==============================================================================

class ChillVerseBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix=".", intents=intents, help_command=None)
        self.state_managers: Dict[int, StateManager] = {}
        self.xp_cooldowns: Dict[int, float] = {}
        self.bump_tasks: Dict[int, asyncio.Task] = {}
        self._prune_cooldowns.start()

    async def setup_hook(self):
        # Add persistent views
        self.add_view(CommunityRolesView())
        self.add_view(ColorView())
        self.add_view(GenderView())
        self.add_view(TicketLaunchView())
        self.add_view(TicketControlsView())
        self.add_view(ConfessionPanelView())
        # Start background tasks
        self.daily_birthday_check.start()
        self.auto_backup_loop.start()
        self.tenure_check_loop.start()

    # --------------------------------------------------------------------------
    # BACKGROUND TASKS
    # --------------------------------------------------------------------------

    @tasks.loop(minutes=10)
    async def auto_backup_loop(self):
        for manager in self.state_managers.values():
            if manager._dirty:
                await manager.save()

    @tasks.loop(hours=1)
    async def daily_birthday_check(self):
        now = datetime.now(timezone.utc)
        today = now.strftime("%d-%m")
        year = str(now.year)
        for manager in self.state_managers.values():
            guild = manager.guild
            birthdays = manager.get("user_birthdays", {})
            announced = manager.get("announced_birthdays", {})
            channel = discord.utils.find(
                lambda c: "birthdays" in normalize_text(c.name),
                guild.text_channels
            )
            if not channel:
                continue
            updated = False
            for uid, bday in birthdays.items():
                if bday == today and announced.get(uid) != year:
                    member = guild.get_member(int(uid))
                    if member:
                        embed = discord.Embed(
                            title="🎂 Happy Birthday! 🎉",
                            description=f"Wishing a wonderful Birthday to {member.mention}! 🥳✨",
                            color=discord.Color.gold()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        try:
                            await channel.send(content=f"🎉 {member.mention}", embed=embed)
                            announced[uid] = year
                            updated = True
                        except Exception:
                            pass
            if updated:
                manager.mark_dirty()

    @tasks.loop(hours=1)
    async def tenure_check_loop(self):
        for manager in self.state_managers.values():
            guild = manager.guild
            now = datetime.now(timezone.utc)
            current_year = str(now.year)
            for member in guild.members:
                if member.bot or not member.joined_at:
                    continue
                if (now - member.joined_at).days < 365:
                    continue
                uid = str(member.id)
                if manager.get("last_anniversary", {}).get(uid) == current_year:
                    continue
                og_role = await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
                vet_role = await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())
                roles_to_add = [r for r in (og_role, vet_role) if r and r not in member.roles and guild.me.top_role > r]
                if roles_to_add:
                    try:
                        await member.add_roles(*roles_to_add, reason="1‑year tenure")
                        await self._add_xp(member, 1000, bypass=True)
                    except Exception:
                        pass
                manager.set("last_anniversary", {**manager.get("last_anniversary", {}), uid: current_year})
                manager.mark_dirty()
                if len(manager.get("last_anniversary", {})) % 10 == 0:
                    await manager.save()

    @tasks.loop(minutes=30)
    async def _prune_cooldowns(self):
        now = time.time()
        to_remove = [uid for uid, ts in self.xp_cooldowns.items() if now - ts > 3600]
        for uid in to_remove:
            del self.xp_cooldowns[uid]

    # --------------------------------------------------------------------------
    # XP SYSTEM (identical to original, but uses StateManager)
    # --------------------------------------------------------------------------

    async def _add_xp(self, member: discord.Member, amount: int, bypass: bool = False) -> None:
        if member.bot or not member.guild:
            return
        now = time.time()
        if not bypass:
            last = self.xp_cooldowns.get(member.id, 0)
            if now - last < 45:  # original cooldown 45 seconds
                return
            self.xp_cooldowns[member.id] = now

        manager = self.state_managers.get(member.guild.id)
        if not manager:
            return
        uid = str(member.id)
        xp = manager.get("user_xp", {}).get(uid, 0) + amount
        level = manager.get("user_levels", {}).get(uid, 1)
        leveled = False
        base_xp = 300
        while level < MAX_LEVEL and xp >= level * base_xp:
            xp -= level * base_xp
            level += 1
            leveled = True

        manager.set("user_xp", {**manager.get("user_xp", {}), uid: xp})
        manager.set("user_levels", {**manager.get("user_levels", {}), uid: level})
        manager.mark_dirty()

        if leveled:
            await self._sync_level_tier(member, level)
            ann_ch = discord.utils.find(
                lambda c: "level-announcements" in normalize_text(c.name),
                member.guild.text_channels
            )
            if ann_ch:
                embed = discord.Embed(
                    title="⚡ Level Advanced!",
                    description=f"Congratulations {member.mention}, you reached **Level {level}**! 🎉",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await ann_ch.send(content=f"🎉 {member.mention}", embed=embed)
                except Exception:
                    pass
            await manager.save()

    async def _sync_level_tier(self, member: discord.Member, level: int) -> None:
        guild = member.guild
        target_config = None
        for (min_lvl, max_lvl), cfg in LEVEL_TIER_ROLES.items():
            if min_lvl <= level <= max_lvl or (max_lvl == 70 and level >= 60):
                target_config = cfg
                break
        if not target_config:
            return

        target_role = await ensure_role_exists(
            guild, target_config["name"], target_config["color"],
            permissions=target_config["permissions"], hoist=target_config["hoist"]
        )
        if not target_role or guild.me.top_role <= target_role:
            return

        all_tier_names = {normalize_text(cfg["name"]) for cfg in LEVEL_TIER_ROLES.values()}
        to_remove = [
            r for r in member.roles
            if normalize_text(r.name) in all_tier_names and r != target_role and guild.me.top_role > r
        ]
        try:
            if to_remove:
                await member.remove_roles(*to_remove, reason="Level tier update")
            if target_role not in member.roles:
                await member.add_roles(target_role, reason="Level tier advancement")
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # BUMP SCHEDULER
    # --------------------------------------------------------------------------

    async def _schedule_bump(self, guild: discord.Guild, channel: Optional[discord.TextChannel] = None) -> None:
        if guild.id in self.bump_tasks and not self.bump_tasks[guild.id].done():
            try:
                self.bump_tasks[guild.id].cancel()
            except Exception:
                pass

        async def bump_reminder():
            manager = self.state_managers.get(guild.id)
            if not manager:
                return
            last = manager.get("last_bump_time", 0.0)
            now = time.time()
            remaining = max(0, int(7200 - (now - last)))
            if remaining > 0:
                await asyncio.sleep(remaining)

            bump_ch = channel or discord.utils.find(
                lambda c: "bump" in normalize_text(c.name),
                guild.text_channels
            )
            if bump_ch:
                role = find_role_resilient(guild, BUMP_ROLE_NAME)
                ping = role.mention if role else "@here"
                embed = discord.Embed(
                    title="⏰ Time to Bump!",
                    description="The 2‑hour cooldown has passed. Run `/bump` to grow the server! 🚀",
                    color=discord.Color.gold()
                )
                try:
                    await bump_ch.send(content=f"🔔 {ping}", embed=embed)
                except Exception:
                    pass

        task = asyncio.create_task(bump_reminder())
        self.bump_tasks[guild.id] = task

    # --------------------------------------------------------------------------
    # EVENT HANDLERS
    # --------------------------------------------------------------------------

    async def on_ready(self):
        print(f"Bot connected as {self.user} (ID: {self.user.id})")
        for guild in self.guilds:
            manager = StateManager(self, guild)
            await manager.load()
            self.state_managers[guild.id] = manager
            print(f"✅ State loaded for '{guild.name}' ({len(manager.get('user_xp', {}))} users)")

            if manager.get("last_bump_time", 0.0) > 0:
                await self._schedule_bump(guild)

    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        newbie_role = await ensure_role_exists(member.guild, "୨୧Newbie୨୧", discord.Color.teal())
        if newbie_role and member.guild.me.top_role > newbie_role:
            try:
                await member.add_roles(newbie_role, reason="Auto‑assign on join")
            except Exception:
                pass

        welcome_ch = discord.utils.find(
            lambda c: "welcome" in normalize_text(c.name),
            member.guild.text_channels
        )
        if welcome_ch:
            embed = discord.Embed(
                title="✨ Welcome to Chill‑Verse! 🌴",
                description=f"Hey {member.mention}! We're thrilled to have you here. 🎉\n\n• Grab your identity roles in <#colours>\n• Open a support ticket in <#tickets> if you need assistance!",
                color=discord.Color.from_rgb(255, 105, 180)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{len(member.guild.members)}")
            try:
                await welcome_ch.send(content=f"Welcome {member.mention}!", embed=embed)
            except Exception:
                pass

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not before.premium_since and after.premium_since:
            booster_role = await ensure_role_exists(after.guild, BOOSTER_ROLE_NAME, discord.Color.from_rgb(255, 105, 180))
            if booster_role and booster_role not in after.roles and after.guild.me.top_role > booster_role:
                try:
                    await after.add_roles(booster_role, reason="Server boost")
                except Exception:
                    pass
            await self._add_xp(after, 1500, bypass=True)
            ann_ch = discord.utils.find(
                lambda c: "level-announcements" in normalize_text(c.name),
                after.guild.text_channels
            )
            if ann_ch:
                embed = discord.Embed(
                    title="✨ Server Boost Received! 🚀",
                    description=f"Thank you {after.mention} for boosting **{after.guild.name}**!\n• Equipped `{BOOSTER_ROLE_NAME}`\n• Received **+1,500 XP**",
                    color=discord.Color.from_rgb(255, 105, 180)
                )
                embed.set_thumbnail(url=after.display_avatar.url)
                try:
                    await ann_ch.send(content=f"🎉 {after.mention}", embed=embed)
                except Exception:
                    pass

    async def on_message(self, message: discord.Message):
        # --- BUMP DETECTION (Improved) ---
        if message.author.id == 302050872383242240:   # Disboard bot
            success = False
            bumper = None
            # Check content
            if "bump done" in message.content.lower():
                success = True
                # Extract bumper from content: "Bump done by @user"
                match = re.search(r"Bump done by <@!?(\d+)>", message.content)
                if match:
                    bumper_id = int(match.group(1))
                    bumper = message.guild.get_member(bumper_id)
            if not success and message.embeds:
                for emb in message.embeds:
                    desc = emb.description or ""
                    if "bump done" in desc.lower() or "👍" in desc:
                        success = True
                        # Try to get bumper from embed author
                        if emb.author:
                            # Embeds may have author name or icon_url; we can try to match by name
                            # Disboard usually sets author name to the bumper's display name.
                            # We'll attempt to find by name (case-insensitive)
                            author_name = emb.author.name
                            if author_name:
                                for member in message.guild.members:
                                    if normalize_text(member.display_name) == normalize_text(author_name):
                                        bumper = member
                                        break
                        break

            if success and message.guild:
                manager = self.state_managers.get(message.guild.id)
                if manager:
                    manager.set("last_bump_time", time.time())
                    await manager.save()
                    # Award XP to bumper if found
                    if bumper:
                        await self._add_xp(bumper, 150, bypass=True)   # 150 XP per bump
                        bump_ch = message.channel
                        try:
                            await bump_ch.send(f"🚀 **{bumper.mention}** bumped the server! Next reminder in 2 hours.")
                        except Exception:
                            pass
                    else:
                        # Could not find bumper, just send generic
                        try:
                            await message.channel.send("🚀 **Bump detected!** Next reminder in 2 hours.", delete_after=10)
                        except Exception:
                            pass
                    # Schedule reminder
                    await self._schedule_bump(message.guild, message.channel)
            # Do not process further (avoid command processing on Disboard messages)
            return

        if message.author.bot:
            return

        if not message.guild:
            return

        manager = self.state_managers.get(message.guild.id)
        if not manager:
            return

        # Maintenance mode check
        if manager.get("maintenance_mode", False) and not is_staff_member(message.author):
            if message.content.startswith(self.command_prefix):
                await message.channel.send("🚧 **Server is currently in Maintenance Mode.** Commands are restricted to staff.", delete_after=6)
            return

        # AFK handling
        uid = str(message.author.id)
        afk_users = manager.get("afk_users", {})
        if uid in afk_users and not message.content.startswith(f"{self.command_prefix}afk"):
            entry = afk_users.pop(uid)
            manager.set("afk_users", afk_users)
            manager.mark_dirty()
            spent = int((time.time() - entry.get("timestamp", time.time())) // 60)
            spent_str = f"{spent} minute(s)" if spent > 0 else "a few seconds"
            mood = entry.get("mood", "neutral")
            if mood == "sad":
                greet = f"🤍 Welcome back {message.author.mention}! Hope your day is brighter. (AFK for {spent_str})"
            elif mood == "happy":
                greet = f"🎉 Welcome back {message.author.mention}! (AFK for {spent_str}) 😊"
            else:
                greet = f"👋 Welcome back {message.author.mention}! (AFK for {spent_str})"
            await message.channel.send(greet, delete_after=10)
            await manager.save()

        # Mention AFK users
        if message.mentions:
            for member in set(message.mentions):
                m_uid = str(member.id)
                if m_uid in manager.get("afk_users", {}):
                    entry = manager.get("afk_users", {}).get(m_uid, {})
                    reason = entry.get("reason", "AFK")
                    await message.channel.send(f"💤 {member.mention} is AFK: {reason}", delete_after=10)

        # XP for non‑command messages
        if not message.content.startswith(self.command_prefix):
            await self._add_xp(message.author, 15)   # Original XP per message

        await self.process_commands(message)

# ==============================================================================
# 6. INTERACTIVE VIEWS (ORIGINAL – UNCHANGED)
# ==============================================================================

class CommunityRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _toggle_role(self, interaction: discord.Interaction, role_name: str, color: discord.Color, mentionable: bool):
        await interaction.response.defer(ephemeral=True)
        guild, member = interaction.guild, interaction.user
        role = await ensure_role_exists(guild, role_name, color, mentionable=mentionable)
        if not role or guild.me.top_role <= role:
            return await interaction.followup.send("⚠️ Cannot manage role due to hierarchy.", ephemeral=True)
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
        manager = interaction.client.state_managers.get(guild.id)
        if not manager:
            return await interaction.followup.send("❌ State not ready.", ephemeral=True)

        target_ch = discord.utils.find(
            lambda c: "confession" in normalize_text(c.name) and "panel" not in normalize_text(c.name),
            guild.text_channels
        )
        if not target_ch:
            return await interaction.followup.send("❌ Confession feed channel not found.", ephemeral=True)

        counter = manager.get("confession_counter", 0) + 1
        manager.set("confession_counter", counter)
        text = self.confession_text.value

        embed = discord.Embed(
            title=f"💌 Anonymous Confession #{counter}",
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
            await manager.save()
        except Exception as e:
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

        manager = interaction.client.state_managers.get(interaction.guild.id)
        if manager:
            tickets = manager.get("tickets", {})
            tickets.pop(str(interaction.channel.id), None)
            manager.set("tickets", tickets)
            await manager.save()

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Closed by {interaction.user}")
        except Exception:
            pass

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.success, emoji="📩", custom_id="btn_ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild, user = interaction.guild, interaction.user
        manager = interaction.client.state_managers.get(guild.id)
        if not manager:
            return await interaction.followup.send("❌ State not ready.", ephemeral=True)

        # Check for existing open ticket
        for ch_id, info in manager.get("tickets", {}).items():
            if info.get("user_id") == user.id:
                ch = guild.get_channel(int(ch_id))
                if ch:
                    return await interaction.followup.send(f"⚠️ You already have an open ticket in {ch.mention}.", ephemeral=True)

        clean_name = re.sub(r"[^\w-]", "", user.name.lower()) or str(user.id)
        ticket_ch_name = f"ticket-{clean_name[:20]}"

        category = discord.utils.find(
            lambda c: "team" in normalize_text(c.name),
            guild.categories
        )
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
                reason="Support ticket open"
            )
            manager.set("tickets", {**manager.get("tickets", {}), str(ch.id): {"user_id": user.id, "created_at": datetime.now(timezone.utc).isoformat()}})
            await manager.save()

            embed = discord.Embed(
                title="🎫 Support Portal",
                description=f"Welcome {user.mention}! Staff will assist you shortly.\nClick **Close Ticket** below when finished.",
                color=discord.Color.teal()
            )
            await ch.send(content=f"{user.mention}", embed=embed, view=TicketControlsView())
            await interaction.followup.send(f"✅ Ticket created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not create ticket channel: {e}", ephemeral=True)

# ==============================================================================
# 7. COMMANDS COG
# ==============================================================================

class AdminCommands(commands.Cog):
    def __init__(self, bot: ChillVerseBot):
        self.bot = bot

    # ----- Help -----
    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(title="📚 Chill‑Verse Bot Commands", color=discord.Color.blurple())
        embed.add_field(
            name="General",
            value="`.level` `.leaderboard` `.setbirthday DD-MM` `.removebirthday` `.afk [reason]`",
            inline=False
        )
        embed.add_field(
            name="Staff",
            value="`.warn @user [reason]` `.mute @user [minutes]` `.unmute @user` `.kick @user [reason]` `.ban @user [reason]` `.nick @user new_nick` `.clear [count]` `.maintenance`",
            inline=False
        )
        embed.add_field(
            name="Setup",
            value="`.setup` – creates all roles and channels (admin only)",
            inline=False
        )
        embed.set_footer(text=f"Prefix: {self.bot.command_prefix}")
        await ctx.send(embed=embed)

    # ----- Setup (creates all roles & channels) -----
    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_server(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild.me.guild_permissions.manage_roles or not guild.me.guild_permissions.manage_channels:
            return await ctx.send("❌ Bot lacks Manage Roles and Manage Channels permissions.")

        # Create all roles from the configuration
        for role_name in RESTRICTED_ADMIN_ROLES:
            perms_cfg = ROLE_PERMISSIONS_CONFIG.get(role_name)
            if perms_cfg:
                await ensure_role_exists(
                    guild, role_name,
                    color=perms_cfg["color"],
                    permissions=perms_cfg["permissions"],
                    hoist=perms_cfg["hoist"]
                )
        # Other roles
        await ensure_role_exists(guild, BOOSTER_ROLE_NAME, discord.Color.from_rgb(255, 105, 180))
        await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
        await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())
        await ensure_role_exists(guild, BUMP_ROLE_NAME, discord.Color.gold())
        await ensure_role_exists(guild, POLL_ROLE_NAME, discord.Color.red())
        await ensure_role_exists(guild, ROBLOX_ROLE_NAME, discord.Color.blue())
        for name, color in GENDER_ROLES.items():
            await ensure_role_exists(guild, name, color)
        for name, color in PRO_HEX_COLORS.items():
            await ensure_role_exists(guild, name, color)
        for (min_lvl, max_lvl), cfg in LEVEL_TIER_ROLES.items():
            await ensure_role_exists(
                guild, cfg["name"], cfg["color"],
                permissions=cfg["permissions"], hoist=cfg["hoist"]
            )

        # Create categories and channels from blueprint
        for category_data in EXTENDED_SERVER_BLUEPRINT:
            cat_name = category_data["category"]
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                try:
                    category = await guild.create_category(cat_name)
                except Exception as e:
                    await ctx.send(f"⚠️ Could not create category {cat_name}: {e}")
                    continue
            for ch_data in category_data["channels"]:
                existing = discord.utils.get(category.channels, name=ch_data["name"])
                if existing:
                    continue
                overwrites = generate_channel_overwrites(guild, ch_data["scheme"])
                try:
                    if ch_data["type"] == "text":
                        await guild.create_text_channel(
                            name=ch_data["name"],
                            category=category,
                            overwrites=overwrites,
                            reason="Setup"
                        )
                    elif ch_data["type"] == "voice":
                        await guild.create_voice_channel(
                            name=ch_data["name"],
                            category=category,
                            overwrites=overwrites,
                            user_limit=ch_data.get("user_limit", 0),
                            reason="Setup"
                        )
                except Exception as e:
                    await ctx.send(f"⚠️ Could not create channel {ch_data['name']}: {e}")

        # Create bot-memory channel
        manager = self.bot.state_managers.get(guild.id)
        if manager:
            await manager._create_memory_channel()

        # Post interactive panels in relevant channels
        colour_ch = discord.utils.get(guild.text_channels, name="🎨・colours")
        if colour_ch:
            await colour_ch.send("**Choose your chat color**", view=ColorView())
            await colour_ch.send("**Choose your identity role**", view=GenderView())
            await colour_ch.send("**Community roles**", view=CommunityRolesView())

        ticket_ch = discord.utils.get(guild.text_channels, name="🎫・tickets")
        if ticket_ch:
            await ticket_ch.send("**Support Tickets** – click to open a ticket.", view=TicketLaunchView())

        conf_ch = discord.utils.get(guild.text_channels, name="🚦confession-🖇")
        if conf_ch:
            await conf_ch.send("**Confession Panel** – click below to confess anonymously.", view=ConfessionPanelView())

        await ctx.send("✅ Server setup complete! Check the channels for interactive panels.")

    # ----- Maintenance -----
    @commands.command(name="maintenance")
    @commands.has_permissions(administrator=True)
    async def toggle_maintenance(self, ctx: commands.Context):
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State not loaded.")
        current = manager.get("maintenance_mode", False)
        manager.set("maintenance_mode", not current)
        await manager.save()
        await ctx.send(f"🛠️ Maintenance mode is now **{'ON' if not current else 'OFF'}**.")

    # ----- Level & Leaderboard -----
    @commands.command(name="level")
    async def show_level(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State not ready.")
        uid = str(target.id)
        xp = manager.get("user_xp", {}).get(uid, 0)
        level = manager.get("user_levels", {}).get(uid, 1)
        embed = discord.Embed(title=f"📊 Level for {target.display_name}", color=target.color)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=f"{xp} / {level * 300}", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context, count: int = 10):
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State not ready.")
        xp_data = manager.get("user_xp", {})
        sorted_users = sorted(xp_data.items(), key=lambda x: x[1], reverse=True)[:count]
        if not sorted_users:
            return await ctx.send("No XP data yet.")
        embed = discord.Embed(title="🏆 XP Leaderboard", color=discord.Color.gold())
        for idx, (uid, xp) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"Unknown ({uid})"
            level = manager.get("user_levels", {}).get(uid, 1)
            embed.add_field(name=f"#{idx} {name}", value=f"Level {level} – {xp} XP", inline=False)
        await ctx.send(embed=embed)

    # ----- Birthday -----
    @commands.command(name="setbirthday")
    async def set_birthday(self, ctx: commands.Context, date: str):
        try:
            datetime.strptime(date, "%d-%m")
        except ValueError:
            return await ctx.send("❌ Invalid format. Use `DD-MM` (e.g. `25-12`).")
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State error.")
        uid = str(ctx.author.id)
        birthdays = manager.get("user_birthdays", {})
        birthdays[uid] = date
        manager.set("user_birthdays", birthdays)
        await manager.save()
        await ctx.send(f"✅ Birthday set to **{date}**!")

    @commands.command(name="removebirthday")
    async def remove_birthday(self, ctx: commands.Context):
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State error.")
        uid = str(ctx.author.id)
        birthdays = manager.get("user_birthdays", {})
        if uid in birthdays:
            del birthdays[uid]
            manager.set("user_birthdays", birthdays)
            await manager.save()
            await ctx.send("🗑️ Birthday removed.")
        else:
            await ctx.send("You don't have a birthday set.")

    # ----- AFK -----
    @commands.command(name="afk")
    async def set_afk(self, ctx: commands.Context, *, reason: str = "AFK"):
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State error.")
        uid = str(ctx.author.id)
        afk = manager.get("afk_users", {})
        afk[uid] = {"reason": reason, "timestamp": time.time()}
        manager.set("afk_users", afk)
        await manager.save()
        await ctx.send(f"💤 {ctx.author.mention} is now AFK: {reason}")

    # ----- Moderation -----
    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if is_staff_member(member):
            return await ctx.send("❌ Cannot warn a staff member.")
        manager = self.bot.state_managers.get(ctx.guild.id)
        if not manager:
            return await ctx.send("❌ State error.")
        uid = str(member.id)
        warnings = manager.get("user_warnings", {})
        warnings[uid] = warnings.get(uid, 0) + 1
        manager.set("user_warnings", warnings)
        await manager.save()
        await ctx.send(f"⚠️ {member.mention} has been warned. Total warnings: {warnings[uid]}")

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, minutes: int = 60, *, reason: str = "No reason"):
        if is_staff_member(member):
            return await ctx.send("❌ Cannot mute a staff member.")
        duration = timedelta(minutes=minutes)
        try:
            await member.timeout(duration, reason=reason)
            await ctx.send(f"🔇 Muted {member.mention} for {minutes} minutes.")
        except Exception as e:
            await ctx.send(f"❌ Failed to mute: {e}")

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        try:
            await member.timeout(None, reason="Unmuted by staff")
            await ctx.send(f"🔊 Unmuted {member.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to unmute: {e}")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if is_staff_member(member):
            return await ctx.send("❌ Cannot kick staff.")
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 Kicked {member.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed: {e}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if is_staff_member(member):
            return await ctx.send("❌ Cannot ban staff.")
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 Banned {member.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed: {e}")

    @commands.command(name="nick")
    @commands.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx: commands.Context, member: discord.Member, *, new_nick: str):
        if is_staff_member(member):
            return await ctx.send("❌ Cannot change staff nickname.")
        try:
            await member.edit(nick=new_nick, reason="Staff command")
            await ctx.send(f"✏️ Changed nickname of {member.mention} to **{new_nick}**.")
        except Exception as e:
            await ctx.send(f"❌ Failed: {e}")

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 10):
        if amount < 1:
            return await ctx.send("Amount must be at least 1.")
        if amount > 100:
            amount = 100
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages.", delete_after=5)
        except Exception as e:
            await ctx.send(f"❌ Failed: {e}")

# ==============================================================================
# 8. RUN THE BOT
# ==============================================================================

bot = ChillVerseBot()

async def main():
    async with bot:
        await bot.add_cog(AdminCommands(bot))
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("No DISCORD_TOKEN found in environment variables.")
            return
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
