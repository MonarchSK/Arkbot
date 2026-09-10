import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
from typing import Union, Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
import datetime
import json
import io
import asyncio
import os
import re
import random
import sys

# ==============================================================================
# BOT SETUP & INTENTS
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

UPDATE_NOTIFIED = False
MAINTENANCE_MODE = False

STATE_FILE = "bot_runtime_state.json"
XP_DATABASE_FILE = "user_xp.json"
BIRTHDAYS_FILE = "birthdays.json"
WARNINGS_FILE = "user_warnings.json"
MUTES_FILE = "user_mutes.json"
AUTO_BOOT_BACKUP_FILE = "auto_boot_backup.json"

# In-memory caches & state
AFK_USERS: Dict[int, Dict[str, Any]] = {}
LAST_BUMP_TIME: Optional[datetime.datetime] = None
BUMP_TIMER_TASK: Optional[asyncio.Task] = None
BUMP_COOLDOWN_SECONDS = 7200  # 2 Hours
ANNOUNCED_BIRTHDAYS_TODAY: List[int] = []

# Super Drop tracking
CHANNEL_CHAT_ACTIVITY: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
SUPER_DROP_COOLDOWNS: Dict[int, float] = {}
SUPER_DROP_COOLDOWN_SECONDS = 3600  # 1 hour cooldown per channel

# Message rate tracking
USER_MESSAGE_TIMESTAMPS: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))
USER_CHAT_XP_COOLDOWN: Dict[int, float] = {}
INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9_-]+",
    re.IGNORECASE
)

# Level Role Tier Hierarchy (Minimum Level, Role Name)
LEVEL_TIERS: List[Tuple[int, str]] = [
    (60, "Sovereign (Levels 60-70)"),
    (50, "Legend (Levels 50-59)"),
    (40, "Champion (Levels 40-49)"),
    (30, "Elite (Levels 30-39)"),
    (20, "Vanguard (Levels 20-29)"),
    (10, "Explorer (Levels 10-19)"),
    (1, "Newbie (Levels 1-9)")
]

AFK_PRESET_MESSAGES = [
    "💔 Slipping away into the quiet shadows... see you when the world feels softer.",
    "🌧️ Wandering through quiet echoes and lonely thoughts. Leaving sweet love behind while I'm away.",
    "🥀 Drifting away to let a tired heart rest. Please keep my memories warm until I return.",
    "🌙 Disappearing into the silent twilight... sending tender hugs across the distance.",
    "🍂 Drifting into solitude for a little while. Missing you all already.",
    "🖤 Floating where the silence feels gentler. Be back soon, don't forget me.",
    "✨ Tucking away in my quiet sanctuary with fond thoughts of you all.",
    "🥺 Stepping into the quiet mist to breathe alone for a bit. Catch you later, lovely souls.",
    "🕊️ Seeking peace in quiet solitude. Leaving warm whispers of affection behind.",
    "🌧️ Drifting into silent solitude to heal and recharge. Keep a warm thought for me."
]

AFK_WELCOME_MESSAGES = [
    "☀️ You're back! The entire room just lit up. Welcome back, {user}!",
    "💖 Welcome back, {user}! The server felt far too quiet without your energy!",
    "🎉 Look who returned! We missed you so much, {user}!",
    "🥳 You're finally back! Everything feels complete again. Welcome home, {user}!",
    "✨ Warmest welcome back, {user}! So genuinely happy to see you chatting again!"
]

BUMP_PRESET_MESSAGES = [
    "🚀 **Server Bumped!** Chill-Verse has been blasted into the cosmos! Thank you for supporting the community.",
    "🌟 **Boom!** Your bump sent shockwaves across Discord! Our sanctuary continues to flourish.",
    "💖 **Bump Successful!** Spreading the warmth of Chill-Verse far and wide. You're an absolute legend!",
    "🔥 **Rising Higher!** Thanks to your bump, Chill-Verse is shining brighter than ever on the server boards.",
    "🎉 **Bump Power Activated!** You just put Chill-Verse back at the top. The entire team appreciates you!",
    "✨ **Pure Magic!** Chill-Verse was boosted through the clouds! Keep the amazing vibes rolling.",
    "🛡️ **Honor to the Realm!** Your dedication keeps our gates open and thriving. Outstanding bump!",
    "🎈 **Soaring Upward!** Another bump, another milestone reached. You made our community proud today!",
    "⚡ **Volt of Energy!** Chill-Verse just received an electrifying boost across Discord.",
    "🌙 **Twilight Ascendance!** Our voices echo louder thanks to your bump. Thank you for showing love!"
]

BUMP_15M_MESSAGES = [
    "⏳ **15-Minute Alert!** The 2-hour cooldown is almost over. Stretch those fingers!",
    "🚀 **Pre-Launch Sequence!** Chill-Verse can be launched into the stars in just 15 minutes!",
    "🛡️ **Heads up Guardians!** 15 minutes left until we can boost our sanctuary back to the summit.",
    "✨ **Magic Gathering!** Only 15 minutes remain before the next bump cycle opens!",
    "⚡ **Charging Energy!** 15 minutes until our next bump pulse goes live. Be ready to claim that +250 XP!",
    "🔔 **Almost Time!** The cooldown timer is ticking down—15 minutes until the gates open!",
    "💫 **Cosmic Alignment:** In 15 minutes, Chill-Verse will be eligible to bump again!",
    "🔥 **Stoking the Fire!** 15 minutes left on the clock. Who is taking the XP crown this round?",
    "🌟 **Starlight Alert!** Only 15 minutes to go before our next server boost is unlocked.",
    "🎈 **Prepare for Liftoff!** 15 minutes on the countdown. Get your `.bump` command primed!"
]

BUMP_READY_MESSAGES = [
    "🔔 **TIME TO BUMP!** The 2-hour cooldown is officially over! First to bump takes the **+250 XP**!",
    "🚀 **BUMP GATES OPEN!** Chill-Verse is ready for another boost! Run `.bump` right now!",
    "⚡ **READY FOR ACTION!** The server needs your bump power! Claim your reward today!",
    "🎉 **COOLDOWN FINISHED!** Boost our world to the top of Discord with `.bump`!",
    "🌟 **THE STAGE IS YOURS!** It's time to bump! Show our community some love and grab that XP!",
    "🛡️ **DEFENDERS ASSEMBLE!** The bump timer has cleared! Type `.bump` to push us higher!",
    "🔥 **CHILL-VERSE IS READY!** Fire up your `.bump` command and claim the top booster spot!",
    "🎈 **BUMP UNLOCKED!** Don't let the server wait—boost us up and take home your XP!",
    "✨ **FRESH CYCLE STARTED!** The clock hit zero! Step up and drop a `.bump` in the chat!",
    "💫 **BOOST WINDOW LIVE!** Let's make Chill-Verse shine across Discord again. Hit `.bump` now!"
]

SERVER_BLUEPRINT: List[Dict[str, Any]] = [
    {
        "category": "Welcome",
        "channels": [
            {"name": "📢・announcements", "type": "text", "restricted": False, "read_only": True},
            {"name": "server-rules", "type": "text", "restricted": False, "read_only": True},
            {"name": "👋・welcome", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "team-news", "type": "text", "restricted": True},
            {"name": "🛡️・team-rules", "type": "text", "restricted": True},
            {"name": "💬・team-chat", "type": "text", "restricted": True},
            {"name": "⏰・bump", "type": "text", "restricted": False},
            {"name": "team-news-forum", "type": "forum", "restricted": True}
        ]
    },
    {
        "category": "Events <3",
        "channels": [
            {"name": "🎉・gwys", "type": "text", "restricted": False},
            {"name": "⭐・vouch", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Chill Area <3",
        "channels": [
            {"name": "discussions-🐣", "type": "forum", "restricted": False},
            {"name": "☁️・chat", "type": "text", "restricted": False},
            {"name": "🍸・chat-ai", "type": "text", "restricted": False},
            {"name": "🪄・chat-en", "type": "text", "restricted": False},
            {"name": "🐥・discussions", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Media <3",
        "channels": [
            {"name": "pfp-share🛼", "type": "text", "restricted": False},
            {"name": "media-share🪹", "type": "text", "restricted": False},
            {"name": "selfies🫂", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Fun Area <3",
        "channels": [
            {"name": "playground-🥊", "type": "text", "restricted": False},
            {"name": "birthdays", "type": "text", "restricted": False},
            {"name": "🚦confession-🖇️", "type": "text", "restricted": False},
            {"name": "memes🤪", "type": "text", "restricted": False},
            {"name": "🖇️-daily-polls", "type": "text", "restricted": False},
            {"name": "🖇️-roblox-elites", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Hobbies <3",
        "channels": [
            {"name": "shayari-and-poetry💗-forum", "type": "forum", "restricted": False},
            {"name": "photography📷", "type": "text", "restricted": False},
            {"name": "arts-and-crafts🎨", "type": "text", "restricted": False},
            {"name": "🎤drop-your-songs", "type": "text", "restricted": False},
            {"name": "shayari-and-poetry💗", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Voice Chat <3",
        "channels": [
            {"name": "🍕 | chit-chat", "type": "voice", "restricted": False, "user_limit": 12},
            {"name": "🍔 | Duo", "type": "voice", "restricted": False, "user_limit": 2},
            {"name": "🍞 | Trio", "type": "voice", "restricted": False, "user_limit": 3},
            {"name": "🧀 | squad", "type": "voice", "restricted": False, "user_limit": 4},
            {"name": "🍺 | Vip", "type": "voice", "restricted": False, "user_limit": 50}
        ]
    },
    {
        "category": "Music <3",
        "channels": [
            {"name": "🎵 Hade Music", "type": "voice", "restricted": False},
            {"name": "🎸 -Atom Music", "type": "voice", "restricted": False}
        ]
    },
    {
        "category": "Info 🩵",
        "channels": [
            {"name": "📢・level-announcements", "type": "text", "restricted": False, "read_only": True},
            {"name": "🎫・tickets", "type": "text", "restricted": False},
            {"name": "🎨・colours", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "💼・bot-commands", "type": "text", "restricted": True},
            {"name": "📜・audit-logs", "type": "text", "restricted": True},
            {"name": "🩸・bot-errors", "type": "text", "restricted": True}
        ]
    }
]

# ==============================================================================
# ASYNC THREAD-SAFE STORAGE ENGINE
# ==============================================================================
FILE_LOCKS: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

def _read_file_sync(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_file_sync(path: str, data: Any) -> None:
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, path)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        print(f"[Storage Engine] Failed writing {path}: {e}")

async def safe_read_json(path: str, default: Any) -> Any:
    async with FILE_LOCKS[path]:
        return await asyncio.to_thread(_read_file_sync, path, default)

async def safe_write_json(path: str, data: Any) -> None:
    async with FILE_LOCKS[path]:
        await asyncio.to_thread(_write_file_sync, path, data)

async def load_xp_database() -> Dict[str, int]:
    return await safe_read_json(XP_DATABASE_FILE, {})

async def save_xp_database(data: Dict[str, int]) -> None:
    await safe_write_json(XP_DATABASE_FILE, data)

async def get_user_xp(user_id: int) -> int:
    xp_db = await load_xp_database()
    return xp_db.get(str(user_id), 0)

async def add_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    async with FILE_LOCKS[XP_DATABASE_FILE]:
        xp_db = await asyncio.to_thread(_read_file_sync, XP_DATABASE_FILE, {})
        uid = str(user_id)
        prev_xp = xp_db.get(uid, 0)
        new_xp = prev_xp + amount
        xp_db[uid] = new_xp
        await asyncio.to_thread(_write_file_sync, XP_DATABASE_FILE, xp_db)
        return prev_xp, new_xp

async def remove_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    async with FILE_LOCKS[XP_DATABASE_FILE]:
        xp_db = await asyncio.to_thread(_read_file_sync, XP_DATABASE_FILE, {})
        uid = str(user_id)
        prev_xp = xp_db.get(uid, 0)
        new_xp = max(0, prev_xp - amount)
        xp_db[uid] = new_xp
        await asyncio.to_thread(_write_file_sync, XP_DATABASE_FILE, xp_db)
        return prev_xp, new_xp

def calculate_level(xp: int) -> int:
    if xp <= 0:
        return 0
    return int((xp / 75) ** 0.5)

def xp_for_level(level: int) -> int:
    return int(75 * (level ** 2))

async def load_birthdays() -> Dict[str, str]:
    return await safe_read_json(BIRTHDAYS_FILE, {})

async def save_birthdays(data: Dict[str, str]) -> None:
    await safe_write_json(BIRTHDAYS_FILE, data)

async def persist_runtime_state():
    state = {
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
        "afk_users": {
            str(uid): {
                "reason": info["reason"],
                "time": info["time"].isoformat()
            }
            for uid, info in AFK_USERS.items()
        },
        "announced_birthdays_today": ANNOUNCED_BIRTHDAYS_TODAY
    }
    await safe_write_json(STATE_FILE, state)

async def restore_runtime_state():
    global LAST_BUMP_TIME, AFK_USERS, ANNOUNCED_BIRTHDAYS_TODAY
    state = await safe_read_json(STATE_FILE, {})
    if not state:
        return

    raw_ts = state.get("last_bump_time")
    if raw_ts:
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_ts, datetime.timezone.utc)

    raw_afk = state.get("afk_users", {})
    AFK_USERS.clear()
    for uid_str, data in raw_afk.items():
        try:
            AFK_USERS[int(uid_str)] = {
                "reason": data.get("reason", "AFK"),
                "time": datetime.datetime.fromisoformat(data["time"])
            }
        except Exception:
            continue

    ANNOUNCED_BIRTHDAYS_TODAY = state.get("announced_birthdays_today", [])

async def sync_member_level_roles(member: discord.Member, new_xp: int) -> Optional[discord.Role]:
    guild = member.guild
    current_lvl = calculate_level(new_xp)

    target_tier_name = None
    for min_lvl, r_name in LEVEL_TIERS:
        if current_lvl >= min_lvl:
            target_tier_name = r_name
            break

    target_role = discord.utils.get(guild.roles, name=target_tier_name) if target_tier_name else None
    tier_role_names = {r_name for _, r_name in LEVEL_TIERS}

    to_remove = [
        r for r in member.roles
        if r.name in tier_role_names and r != target_role and r < guild.me.top_role
    ]

    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Level Tier Recalibration")
        if target_role and target_role not in member.roles and target_role < guild.me.top_role:
            await member.add_roles(target_role, reason=f"Level Tier Sync (Level {current_lvl})")
    except (discord.Forbidden, discord.HTTPException):
        pass

    return target_role

async def handle_level_up(member: discord.Member, prev_xp: int, new_xp: int, fallback_ch: Optional[discord.TextChannel] = None):
    old_lvl = calculate_level(prev_xp)
    new_lvl = calculate_level(new_xp)

    if new_lvl <= old_lvl:
        return

    unlocked_role = await sync_member_level_roles(member, new_xp)

    lvl_channel = discord.utils.get(member.guild.text_channels, name="📢・level-announcements") or fallback_ch
    if lvl_channel and isinstance(lvl_channel, discord.TextChannel):
        embed = discord.Embed(
            title="🎊 LEVEL UP! 🎊",
            description=f"Congratulations {member.mention}! You leveled up from **Level {old_lvl}** to **Level {new_lvl}**!",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Total XP", value=f"**{new_xp:,} XP**", inline=True)
        embed.add_field(name="Current Level", value=f"**Level {new_lvl}**", inline=True)

        if unlocked_role:
            embed.add_field(name="⭐ New Rank Unlocked", value=f"**{unlocked_role.mention}**", inline=False)

        next_lvl_xp = xp_for_level(new_lvl + 1)
        embed.add_field(name="Next Level At", value=f"`{next_lvl_xp:,} XP`", inline=False)
        embed.set_footer(text="Keep chatting and bumping to unlock higher tier perks!")

        try:
            await lvl_channel.send(content=f"🎉 {member.mention} just hit **Level {new_lvl}**!", embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            pass

# ==============================================================================
# AUTHORITY CHECKS & HELPERS
# ==============================================================================
def is_authority_holder():
    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        if getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        authority_roles = {"supreme leader", "highness", "authority"}
        user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
        if bool(authority_roles.intersection(user_roles)):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Administrators and Authority holders can execute this command.")
    return commands.check(predicate)

def is_team_member(member: Union[discord.Member, discord.User]) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if getattr(member.guild_permissions, "administrator", False):
        return True
    team_roles = {
        "supreme leader", "highness", "authority",
        "head moderator", "moderator", "trial mod", "chill-verse team"
    }
    user_roles = {r.name.lower().strip() for r in getattr(member, "roles", [])}
    return bool(team_roles.intersection(user_roles))

def resolve_guild_context(interaction: discord.Interaction) -> Optional[discord.Guild]:
    if interaction.guild:
        return interaction.guild
    matched = [g for g in interaction.client.guilds if g.get_member(interaction.user.id)]
    return matched[0] if len(matched) == 1 else None

def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

async def get_or_create_audit_channel(guild: discord.Guild) -> discord.TextChannel:
    target_name = "📜・audit-logs"
    ch = discord.utils.get(guild.text_channels, name=target_name) or discord.utils.get(guild.text_channels, name="audit-logs")
    if ch:
        return ch

    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    admin_roles = ["Supreme Leader", "Highness", "Authority"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            manage_channels=True
        )
    }

    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(
        name=target_name,
        category=admin_cat,
        overwrites=overwrites,
        reason="Private Edit/Delete Audit Channel"
    )

async def get_or_create_memory_channel(guild: discord.Guild) -> discord.TextChannel:
    memory_ch = discord.utils.get(guild.text_channels, name="bot-memory")
    if memory_ch:
        return memory_ch

    admin_roles = ["Supreme Leader", "Highness", "Authority"]
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(name="bot-memory", overwrites=overwrites, reason="Arkbot State Engine")

async def prune_old_backups(channel: discord.TextChannel, keep_count: int = 3):
    try:
        backup_messages = []
        async for msg in channel.history(limit=100):
            if msg.author == channel.guild.me:
                has_backup_file = any(att.filename.endswith(".json") for att in msg.attachments)
                has_backup_text = "backup" in msg.content.lower()
                if has_backup_file or has_backup_text:
                    backup_messages.append(msg)

        if len(backup_messages) > keep_count:
            for old_msg in backup_messages[keep_count:]:
                try:
                    await old_msg.delete()
                    await asyncio.sleep(0.35)
                except (discord.NotFound, discord.HTTPException):
                    pass
    except Exception as e:
        print(f"Failed pruning backups: {e}")

# ==============================================================================
# UNIFIED BACKUP & SAFE RESTORATION
# ==============================================================================
async def generate_unified_backup_payload(guild: discord.Guild) -> Dict[str, Any]:
    categories_data = []
    for cat in guild.categories:
        cat_overwrites = {}
        for target, overwrite in cat.overwrites.items():
            allow, deny = overwrite.pair()
            cat_overwrites[str(target.id)] = {
                "name": target.name,
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": allow.value,
                "deny": deny.value
            }

        cat_entry = {
            "name": cat.name,
            "position": cat.position,
            "overwrites": cat_overwrites,
            "channels": []
        }

        for ch in cat.channels:
            ch_overwrites = {}
            for target, overwrite in ch.overwrites.items():
                allow, deny = overwrite.pair()
                ch_overwrites[str(target.id)] = {
                    "name": target.name,
                    "type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": allow.value,
                    "deny": deny.value
                }

            cat_entry["channels"].append({
                "name": ch.name,
                "type": str(ch.type),
                "position": ch.position,
                "user_limit": getattr(ch, "user_limit", 0),
                "overwrites": ch_overwrites
            })
        categories_data.append(cat_entry)

    current_blueprint = []
    for cat in guild.categories:
        cat_blueprint = {"category": cat.name, "channels": []}
        for ch in cat.channels:
            if ch.name in ["bot-memory", "📜・audit-logs"]:
                continue
            ch_type = "text"
            if isinstance(ch, discord.VoiceChannel):
                ch_type = "voice"
            elif isinstance(ch, getattr(discord, "ForumChannel", ())):
                ch_type = "forum"

            default_ow = ch.overwrites.get(guild.default_role)
            is_restricted = False
            is_read_only = False
            if default_ow:
                if default_ow.view_channel is False:
                    is_restricted = True
                if default_ow.send_messages is False:
                    is_read_only = True
            elif cat.name in ["Team <3", "Admin Area 🔒"]:
                is_restricted = True

            ch_item = {
                "name": ch.name,
                "type": ch_type,
                "restricted": is_restricted,
                "read_only": is_read_only
            }
            if ch_type == "voice" and getattr(ch, "user_limit", 0) > 0:
                ch_item["user_limit"] = ch.user_limit
            cat_blueprint["channels"].append(ch_item)

        if cat_blueprint["channels"]:
            current_blueprint.append(cat_blueprint)

    return {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "categories": categories_data,
        "blueprint": current_blueprint,
        "roles": [
            {
                "name": r.name,
                "permissions": r.permissions.value,
                "color": r.color.value,
                "hoist": r.hoist
            }
            for r in guild.roles if not r.is_default() and not r.managed
        ],
        "user_xp": await load_xp_database(),
        "user_birthdays": await load_birthdays(),
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None
    }

async def apply_unified_restore(guild: discord.Guild, data: Dict[str, Any]) -> Dict[str, int]:
    global SERVER_BLUEPRINT, LAST_BUMP_TIME

    stats = {
        "channels_created": 0,
        "perms_applied": 0,
        "perms_skipped": 0,
        "xp_users": 0
    }

    saved_blueprint = data.get("blueprint")
    if saved_blueprint and isinstance(saved_blueprint, list):
        SERVER_BLUEPRINT = saved_blueprint

    raw_xp = data.get("user_xp") or {}
    if raw_xp:
        curr_xp = await load_xp_database()
        for uid, xp_val in raw_xp.items():
            curr_xp[str(uid)] = max(curr_xp.get(str(uid), 0), int(xp_val))
        await save_xp_database(curr_xp)
        stats["xp_users"] = len(raw_xp)

    raw_bdays = data.get("user_birthdays") or {}
    if raw_bdays:
        curr_bdays = await load_birthdays()
        curr_bdays.update(raw_bdays)
        await save_birthdays(curr_bdays)

    raw_bump = data.get("last_bump_time")
    if raw_bump:
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_bump, datetime.timezone.utc)
        await persist_runtime_state()

    existing_cats = {normalize_name(c.name): c for c in guild.categories}

    for cat_data in data.get("categories", []):
        cat_name = cat_data["name"]
        norm_cat = normalize_name(cat_name)

        if norm_cat in existing_cats:
            category = existing_cats[norm_cat]
        else:
            category = await guild.create_category(name=cat_name)
            existing_cats[norm_cat] = category
            await asyncio.sleep(0.3)

        for target_id, ow_info in cat_data.get("overwrites", {}).items():
            target = guild.get_role(int(target_id)) if ow_info["type"] == "role" else guild.get_member(int(target_id))
            if not target and ow_info["type"] == "role":
                target = discord.utils.get(guild.roles, name=ow_info.get("name"))

            if target:
                if target in category.overwrites:
                    stats["perms_skipped"] += 1
                    continue

                allow = discord.Permissions(ow_info["allow"])
                deny = discord.Permissions(ow_info["deny"])
                try:
                    await category.set_permissions(target, overwrite=discord.PermissionOverwrite.from_pair(allow, deny))
                    stats["perms_applied"] += 1
                except Exception:
                    pass

        existing_chs = {normalize_name(ch.name): ch for ch in category.channels}

        for ch_data in cat_data.get("channels", []):
            ch_name = ch_data["name"]
            norm_ch = normalize_name(ch_name)
            ch_type_str = ch_data.get("type", "text")

            if norm_ch in existing_chs:
                channel = existing_chs[norm_ch]
            else:
                user_lim = ch_data.get("user_limit", 0)
                if "voice" in ch_type_str:
                    channel = await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim)
                elif "forum" in ch_type_str:
                    try:
                        channel = await guild.create_forum_channel(name=ch_name, category=category)
                    except Exception:
                        channel = await guild.create_text_channel(name=ch_name, category=category)
                else:
                    channel = await guild.create_text_channel(name=ch_name, category=category)

                existing_chs[norm_ch] = channel
                stats["channels_created"] += 1
                await asyncio.sleep(0.3)

            for target_id, ow_info in ch_data.get("overwrites", {}).items():
                target = guild.get_role(int(target_id)) if ow_info["type"] == "role" else guild.get_member(int(target_id))
                if not target and ow_info["type"] == "role":
                    target = discord.utils.get(guild.roles, name=ow_info.get("name"))

                if target:
                    if target in channel.overwrites:
                        stats["perms_skipped"] += 1
                        continue

                    allow = discord.Permissions(ow_info["allow"])
                    deny = discord.Permissions(ow_info["deny"])
                    try:
                        await channel.set_permissions(target, overwrite=discord.PermissionOverwrite.from_pair(allow, deny))
                        stats["perms_applied"] += 1
                    except Exception:
                        pass

    return stats

# ==============================================================================
# BUMP NOTIFICATION ENGINE
# ==============================================================================
def get_bump_role_mentions(guild: discord.Guild) -> str:
    bump_role = discord.utils.find(
        lambda r: r.name.lower().strip() in ["bump pings", "bump ping", "bumping"],
        guild.roles
    )
    return bump_role.mention if bump_role else "@here"

async def schedule_bump_timers(guild: discord.Guild, origin_channel: discord.TextChannel):
    target_channel = (
        discord.utils.get(guild.text_channels, name="⏰・bump")
        or discord.utils.get(guild.text_channels, name="bump")
    )

    if not target_channel:
        print(f"[Bump Watch] Dedicated bump channel not found in {guild.name}. Reminders suppressed.")
        return

    try:
        await asyncio.sleep(6300)
        pings = get_bump_role_mentions(guild)
        msg_15m = random.choice(BUMP_15M_MESSAGES)

        reminder_embed = discord.Embed(
            title="⏰ Bump Reminder — 15 Minutes Remaining!",
            description=(
                f"{msg_15m}\n\n"
                f"**Chill-Verse** can be bumped again in exactly **15 minutes**.\n"
                f"🎁 The first member to type `.bump` earns **+250 XP**!"
            ),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        reminder_embed.set_footer(text="Chill-Verse Bump Watch • 15 Minute Notice")
        await target_channel.send(content=pings, embed=reminder_embed)

        await asyncio.sleep(900)
        pings = get_bump_role_mentions(guild)
        msg_ready = random.choice(BUMP_READY_MESSAGES)

        ready_embed = discord.Embed(
            title="🔔 Chill-Verse is Ready to Bump!",
            description=(
                f"{msg_ready}\n\n"
                f"Type **`.bump`** right now to boost the server and claim your **+250 XP** reward!"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        ready_embed.set_footer(text="Cooldown Ended • Bump Unlocked")
        await target_channel.send(content=pings, embed=ready_embed)

    except asyncio.CancelledError:
        pass

# ==============================================================================
# UI COMPONENTS
# ==============================================================================
class ClaimXPDropView(View):
    def __init__(self, xp_amount: int):
        super().__init__(timeout=300.0)
        self.xp_amount = xp_amount
        self.claimed = False
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="🎁 Claim XP", style=discord.ButtonStyle.green, custom_id="claim_xp_drop")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        if self.claimed:
            return await interaction.response.send_message("❌ This XP drop has already been claimed!", ephemeral=True)

        self.claimed = True
        button.disabled = True
        button.label = "Claimed!"
        button.style = discord.ButtonStyle.secondary

        prev_xp, new_xp = await add_user_xp(interaction.user.id, self.xp_amount)

        embed = discord.Embed(
            title="🎉 XP DROP CLAIMED!",
            description=(
                f"Congratulations {interaction.user.mention}! You reacted the fastest!\n\n"
                f"💰 **Reward:** `+{self.xp_amount} XP`\n"
                f"📊 **Total XP:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)

        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)

    async def on_timeout(self):
        if not self.claimed and self.message:
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
                    child.label = "Expired"
                    child.style = discord.ButtonStyle.secondary
            try:
                timeout_embed = discord.Embed(
                    title="⌛ XP Drop Expired",
                    description="Nobody claimed the XP drop in time! Keep an eye out for the next one.",
                    color=discord.Color.dark_grey()
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except (discord.HTTPException, discord.NotFound):
                pass

class SuperXPDropView(View):
    def __init__(self, xp_amount: int):
        super().__init__(timeout=180.0)
        self.xp_amount = xp_amount
        self.claimed = False
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="⚡ CLAIM SUPER DROP ⚡", style=discord.ButtonStyle.danger, custom_id="claim_super_xp_drop")
    async def claim_super_drop(self, interaction: discord.Interaction, button: Button):
        if self.claimed:
            return await interaction.response.send_message("❌ Too late! Someone already claimed this Super Drop!", ephemeral=True)

        self.claimed = True
        button.disabled = True
        button.label = "Claimed!"
        button.style = discord.ButtonStyle.secondary

        prev_xp, new_xp = await add_user_xp(interaction.user.id, self.xp_amount)

        embed = discord.Embed(
            title="💥 SUPER XP DROP SECURED! 💥",
            description=(
                f"⚡ {interaction.user.mention} dominated the chat and grabbed the loot!\n\n"
                f"🔥 **Massive Reward:** `+{self.xp_amount:,} XP`\n"
                f"📊 **New Total:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})"
            ),
            color=discord.Color.from_rgb(255, 69, 0),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)

        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)

    async def on_timeout(self):
        if not self.claimed and self.message:
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
                    child.label = "Expired"
                    child.style = discord.ButtonStyle.secondary
            try:
                timeout_embed = discord.Embed(
                    title="💨 Super XP Drop Vanished",
                    description="The chat let a massive XP drop slip away into the void!",
                    color=discord.Color.dark_grey()
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except (discord.HTTPException, discord.NotFound):
                pass

class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(label="Why do you want to join?", style=discord.TextStyle.paragraph, placeholder="Tell us a bit about yourself...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = resolve_guild_context(interaction)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Could not determine server context.", ephemeral=True)

        member = guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.HTTPException:
                return await interaction.response.send_message("⚠️ Error: Member profile not found.", ephemeral=True)

        dob_val = self.dob.value.strip()
        parts = dob_val.split("/")
        if len(parts) >= 2:
            day, month = parts[0].zfill(2), parts[1].zfill(2)
            bdays = await load_birthdays()
            bdays[str(interaction.user.id)] = f"{day}/{month}"
            await save_birthdays(bdays)

        role = discord.utils.get(guild.roles, name="Member")
        if role and role < guild.me.top_role:
            try:
                await member.add_roles(role, reason="Completed Verification Modal")
            except discord.Forbidden:
                pass

        log_channel = discord.utils.get(guild.text_channels, name="💼・bot-commands")
        if log_channel:
            embed = discord.Embed(title="New Member Verified", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="User", value=interaction.user.mention, inline=False)
            embed.add_field(name="Full Name", value=self.real_full_name.value, inline=True)
            embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
            embed.add_field(name="DOB", value=self.dob.value, inline=True)
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass

        await interaction.response.send_message("Verification complete! Welcome to Chill-Verse.", ephemeral=True)

class TeamApplicationModal(Modal, title="Staff Team Application"):
    age_tz = TextInput(label="Age & Timezone", placeholder="18, EST", required=True, max_length=50)
    experience = TextInput(label="Previous Experience", style=discord.TextStyle.paragraph, placeholder="List past moderation experience...", required=True, max_length=300)
    reason = TextInput(label="Why do you want to join the Team?", style=discord.TextStyle.paragraph, placeholder="Tell us why we should choose you...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = resolve_guild_context(interaction)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context not found.", ephemeral=True)

        team_channel = discord.utils.get(guild.text_channels, name="💬・team-chat") or discord.utils.get(guild.text_channels, name="team-news")
        embed = discord.Embed(title="🚨 New Staff Application Submitted", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)
        embed.add_field(name="Age & Timezone", value=self.age_tz.value, inline=True)
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)

        if team_channel:
            try:
                await team_channel.send(embed=embed)
            except discord.HTTPException:
                pass

        await interaction.response.send_message("✅ Your application has been submitted for review!", ephemeral=True)

class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="persistent_accept_rules")
    async def accept(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VerificationModal())

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, custom_id="persistent_decline_rules")
    async def decline(self, interaction: discord.Interaction, button: Button):
        guild = resolve_guild_context(interaction)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context could not be resolved.", ephemeral=True)

        try:
            await guild.kick(interaction.user, reason="Declined server rules.")
            await interaction.response.send_message("You declined the rules and have been removed.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Error: Bot lacks permission to kick members.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Error handling kick: {e}", ephemeral=True)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="persistent_close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 This ticket will close in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket closed by user.")
        except (discord.HTTPException, discord.NotFound):
            pass

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent_open_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("Tickets can only be opened inside the server.", ephemeral=True)

        category = discord.utils.get(guild.categories, name="Team <3")
        clean_user_name = re.sub(r"[^a-zA-Z0-9_-]", "", interaction.user.name).lower() or "user"
        channel_name = f"ticket-{clean_user_name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        }

        for rname in ["Supreme Leader", "Highness", "Authority"]:
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_ch = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {interaction.user.name}"
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(f"⚠️ Failed to create ticket channel: {e}", ephemeral=True)

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {interaction.user.mention}! Explain your issue below. High Command will assist you shortly.",
            color=discord.Color.blue()
        )
        await ticket_ch.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created: {ticket_ch.mention}", ephemeral=True)

    @discord.ui.button(label="Apply for Team", style=discord.ButtonStyle.green, custom_id="persistent_apply_team", emoji="🛡️")
    async def apply_team(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TeamApplicationModal())

class ReactionRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(self, interaction: discord.Interaction, role_name: str):
        if not interaction.guild:
            return await interaction.response.send_message("Action can only be executed in a server channel.", ephemeral=True)

        role = discord.utils.find(lambda r: r.name.lower().strip() == role_name.lower().strip(), interaction.guild.roles)
        if not role:
            return await interaction.response.send_message(f"⚠️ Role `{role_name}` not found. Run `.setup_roles` first.", ephemeral=True)

        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("⚠️ Error: Role is above the bot's hierarchy limit.", ephemeral=True)

        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member:
            return await interaction.response.send_message("Could not resolve member identity.", ephemeral=True)

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed: **{role.name}**", ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message(f"✅ Added: **{role.name}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Permission denied modifying roles.", ephemeral=True)

    @discord.ui.button(label="🔴 Red", style=discord.ButtonStyle.secondary, custom_id="role_red", row=0)
    async def red_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Red")

    @discord.ui.button(label="🟡 Yellow", style=discord.ButtonStyle.secondary, custom_id="role_yellow", row=0)
    async def yellow_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Yellow")

    @discord.ui.button(label="🟢 Green", style=discord.ButtonStyle.secondary, custom_id="role_green", row=0)
    async def green_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Green")

    @discord.ui.button(label="🔵 Blue", style=discord.ButtonStyle.secondary, custom_id="role_blue", row=1)
    async def blue_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Blue")

    @discord.ui.button(label="🟠 Orange", style=discord.ButtonStyle.secondary, custom_id="role_orange", row=1)
    async def orange_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Orange")

    @discord.ui.button(label="🩷 Pink", style=discord.ButtonStyle.secondary, custom_id="role_pink", row=1)
    async def pink_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Pink")

    @discord.ui.button(label="⏰ Bump Pings", style=discord.ButtonStyle.primary, custom_id="role_bump_pings", row=2)
    async def bump_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Bump Pings")

    @discord.ui.button(label="📊 Poll Pings", style=discord.ButtonStyle.primary, custom_id="role_poll", row=2)
    async def poll_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Poll Pings")

    @discord.ui.button(label="🎮 Roblox Members", style=discord.ButtonStyle.primary, custom_id="role_roblox", row=2)
    async def roblox_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Roblox Members")

# ==============================================================================
# TEAM RULES PANEL DEPLOYER
# ==============================================================================
async def deploy_team_rules_panel(guild: discord.Guild):
    team_rules_ch = (
        discord.utils.get(guild.text_channels, name="🛡️・team-rules")
        or discord.utils.get(guild.text_channels, name="team-rules")
    )

    if not team_rules_ch:
        return

    try:
        async for msg in team_rules_ch.history(limit=50):
            if msg.author == guild.me:
                await msg.delete()
                await asyncio.sleep(0.3)
    except (discord.Forbidden, discord.HTTPException):
        pass

    rules_embed = discord.Embed(
        title="🛡️ CHILL-VERSE TEAM GUIDELINES & PROTOCOL",
        description=(
            "Welcome to the internal staff directory. As a team member, you represent "
            "the culture and safety of Chill-Verse. Adhere to these principles at all times:"
        ),
        color=discord.Color.dark_red(),
        timestamp=discord.utils.utcnow()
    )

    rules_embed.add_field(
        name="1. Impartiality & Maturity",
        value=(
            "• Moderate objectively. Never let personal disputes dictate punishments.\n"
            "• Never use permissions or administrative authority in casual arguments.\n"
            "• Keep staff disagreements strictly behind closed doors in `💬・team-chat`."
        ),
        inline=False
    )

    rules_embed.add_field(
        name="2. Confidentiality & Security",
        value=(
            "• Everything inside the `Team <3` and `Admin Area 🔒` categories is strictly classified.\n"
            "• Never leak ticket discussions, audit logs, or member disciplinary history.\n"
            "• Do not invite unofficial bots or alter category permissions without High Command approval."
        ),
        inline=False
    )

    rules_embed.add_field(
        name="3. Command Escalation Hierarchy",
        value=(
            "• **Supreme Leader / Highness**: Executive operations, architecture & backups.\n"
            "• **Authority**: Channel isolation, bulk cleanup, broadcasts & lockdowns.\n"
            "• **Moderators / Trial Mods**: Chat pacing, user warnings, timeouts, and tickets."
        ),
        inline=False
    )

    if guild.icon:
        rules_embed.set_thumbnail(url=guild.icon.url)
    rules_embed.set_footer(text="Chill-Verse Staff Operations • Internal Document")

    commands_embed = discord.Embed(
        title="💼 TEAM & AUTHORITY ACTIVE BOT COMMANDS",
        description="Reference manual for bot commands restricted to Team and High Command:",
        color=discord.Color.gold()
    )

    commands_embed.add_field(
        name="🧹 Moderation & Purge Suite",
        value=(
            f"`{bot.command_prefix}purge <1-1000> [target]` — Authority bulk deletion (supports `@user`, `bots`, or `links`).\n"
            f"`{bot.command_prefix}remove_bot_role <@role/@bot/all>` — Immediately cuts bot permissions from a channel."
        ),
        inline=False
    )

    commands_embed.add_field(
        name="🔒 Channel Security Controls",
        value=(
            f"`{bot.command_prefix}lock` / `{bot.command_prefix}unlock` — Mutes or opens the current room for members.\n"
            f"`{bot.command_prefix}hide` / `{bot.command_prefix}show` — Toggles channel visibility from standard members.\n"
            f"`{bot.command_prefix}permit <@user/@role>` — Whitelists a member or role into the channel.\n"
            f"`{bot.command_prefix}revoke <@user/@role>` — Evicts a member or role from the channel."
        ),
        inline=False
    )

    commands_embed.add_field(
        name="⭐ XP & Progression Management",
        value=(
            f"`{bot.command_prefix}addxp <@user> <amount>` — Manually awards XP and auto-upgrades rank roles.\n"
            f"`{bot.command_prefix}removexp <@user> <amount>` — Deducts XP and demotes level tiers accordingly."
        ),
        inline=False
    )

    commands_embed.add_field(
        name="📢 High Command Broadcasts & System Maintenance",
        value=(
            f"`{bot.command_prefix}announce <title> | <text> [--everyone/--here]` — Posts official embeds to `#announcements`.\n"
            f"`{bot.command_prefix}maintenance` — Gracefully flushes and terminates the bot with full backups.\n"
            f"`{bot.command_prefix}backup_all` / `{bot.command_prefix}restore_all` — Creates or restores complete architecture."
        ),
        inline=False
    )

    commands_embed.set_footer(text=f"Prefix: {bot.command_prefix} • Strictly restricted to Staff roles")

    try:
        await team_rules_ch.send(embed=rules_embed)
        await team_rules_ch.send(embed=commands_embed)
    except (discord.HTTPException, discord.Forbidden) as e:
        print(f"[Team Rules Deploy] Could not post in #{team_rules_ch.name}: {e}")

# ==============================================================================
# SUBCLASSED BOT ENGINE
# ==============================================================================
class ArkBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents)
        self.remove_command("help")

    async def setup_hook(self):
        await restore_runtime_state()
        self.add_view(RulesView())
        self.add_view(TicketView())
        self.add_view(CloseTicketView())
        self.add_view(ReactionRoleView())

        boot_backup = await safe_read_json(AUTO_BOOT_BACKUP_FILE, None)
        if boot_backup:
            print("[Auto-Boot] Restoring blueprint, channels, and state safely from backup...")
            asyncio.create_task(self._auto_restore_on_start(boot_backup))

        if not hourly_backup_task.is_running():
            hourly_backup_task.start()
        if not birthday_announcer_task.is_running():
            birthday_announcer_task.start()
        if not xp_drop_task.is_running():
            xp_drop_task.start()

    async def _auto_restore_on_start(self, backup_data: Dict[str, Any]):
        await self.wait_until_ready()
        guild = self.get_guild(backup_data.get("guild_id"))
        if not guild and self.guilds:
            guild = self.guilds[0]

        if guild:
            stats = await apply_unified_restore(guild, backup_data)
            print(f"[Auto-Boot Complete] Restored {stats['channels_created']} missing channels. Preserved {stats['perms_skipped']} existing overwrites.")

bot = ArkBot()

@bot.check
async def check_maintenance_mode(ctx: commands.Context):
    # If maintenance is OFF, allow all commands unconditionally
    if not MAINTENANCE_MODE:
        return True

    # Allow the maintenance command itself so it can be toggled back on/off
    if ctx.command and ctx.command.name in ["maintenance", "shutdown"]:
        return True

    is_admin = getattr(getattr(ctx.author, "guild_permissions", None), "administrator", False)
    staff_roles = {"supreme leader", "highness", "authority"}
    user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
    is_high_command = bool(staff_roles.intersection(user_roles))

    if is_admin or is_high_command:
        return True

    await ctx.send("🛠️ **Maintenance Mode Active:** Non-administrative commands are temporarily disabled.", delete_after=6)
    return False

# ==============================================================================
# AUDIT LOGGING & EVENTS
# ==============================================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse fully operational.")
    global UPDATE_NOTIFIED

    for guild in bot.guilds:
        await deploy_team_rules_panel(guild)
        await get_or_create_audit_channel(guild)

    if not UPDATE_NOTIFIED:
        for guild in bot.guilds:
            team_news_ch = discord.utils.get(guild.text_channels, name="team-news")
            if team_news_ch:
                embed = discord.Embed(
                    title="🚀 Arkbot Operational — Full Engine Online!",
                    description="Leveling, persistence locks, hourly XP drops, super drops, and staff manuals are online.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                try:
                    await team_news_ch.send(embed=embed)
                except Exception:
                    pass
        UPDATE_NOTIFIED = True

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    log_ch = await get_or_create_audit_channel(message.guild)
    if log_ch:
        content = message.content or "*None (attachment or embed)*"
        if len(content) > 1000:
            content = content[:1000] + "... [truncated]"

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=content, inline=False)
        embed.set_footer(text=f"Author: {message.author}")

        try:
            await log_ch.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            pass

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content:
        return

    log_ch = await get_or_create_audit_channel(before.guild)
    if log_ch:
        b_content = before.content or "*Empty*"
        a_content = after.content or "*Empty*"
        if len(b_content) > 1000:
            b_content = b_content[:1000] + "... [truncated]"
        if len(a_content) > 1000:
            a_content = a_content[:1000] + "... [truncated]"

        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Author", value=f"{before.author.mention} (`{before.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Jump to Message", value=f"[Click Here]({after.jump_url})", inline=True)
        embed.add_field(name="Before", value=b_content, inline=False)
        embed.add_field(name="After", value=a_content, inline=False)
        embed.set_footer(text=f"Author: {before.author}")

        try:
            await log_ch.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            pass

@bot.event
async def on_member_remove(member: discord.Member):
    log_ch = await get_or_create_audit_channel(member.guild)
    if log_ch:
        embed = discord.Embed(title="🚪 Member Left Server", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    print(f"DEBUG: Command [{ctx.command}] failed -> {type(error).__name__}: {error}")
    if isinstance(error, commands.CheckFailure):
        return await ctx.send(str(error), delete_after=6)
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"⚠️ **Command Error:** `{error}`", delete_after=8)

@bot.event
async def on_member_join(member: discord.Member):
    embed = discord.Embed(
        title="Welcome to Chill-Verse! 🎉",
        description=(
            "**Basic Server Rules:**\n"
            "1. Be respectful, kind, and inclusive to everyone.\n"
            "2. No bullying, hate speech, spam, or toxic behavior.\n"
            "3. Keep conversations teen and family-friendly.\n"
            "4. Follow Discord's Terms of Service at all times.\n\n"
            "To unlock server access, click **Accept** to submit your details via form, or **Decline** to exit."
        ),
        color=discord.Color.purple()
    )
    sent_dm = False
    try:
        await member.send(embed=embed, view=RulesView())
        sent_dm = True
    except discord.Forbidden:
        pass

    channel = discord.utils.get(member.guild.text_channels, name="👋・welcome")
    if channel:
        msg = f"{member.mention} Welcome! Please check your DMs to complete verification." if sent_dm else f"{member.mention} (Please enable DMs or click Accept below to verify!)"
        await channel.send(content=msg, embed=embed, view=RulesView())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 1. AFK Return Greeting
    if message.author.id in AFK_USERS and not message.content.strip().startswith(f"{bot.command_prefix}afk"):
        del AFK_USERS[message.author.id]
        await persist_runtime_state()
        welcome_template = random.choice(AFK_WELCOME_MESSAGES)
        welcome_embed = discord.Embed(
            description=welcome_template.format(user=message.author.mention),
            color=discord.Color.green()
        )
        await message.channel.send(embed=welcome_embed, delete_after=10)

    # 2. AFK Mention Interceptor
    if message.mentions:
        for mentioned in message.mentions:
            if mentioned.id in AFK_USERS and mentioned.id != message.author.id:
                afk_info = AFK_USERS[mentioned.id]
                afk_embed = discord.Embed(
                    description=f"💤 **{mentioned.display_name} is currently AFK:**\n*{afk_info['reason']}*",
                    color=discord.Color.dark_purple()
                )
                await message.channel.send(embed=afk_embed, delete_after=10)

    # 3. AutoMod (Links & Spam Prevention)
    if isinstance(message.author, discord.Member) and not is_team_member(message.author):
        if INVITE_REGEX.search(message.content):
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return await message.channel.send(f"⚠️ {message.author.mention}, posting invite links is prohibited!", delete_after=4)

        now = discord.utils.utcnow().timestamp()
        queue = USER_MESSAGE_TIMESTAMPS[message.author.id]
        queue.append(now)

        recent = [t for t in queue if now - t < 4.0]
        if len(recent) > 5:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return await message.channel.send(f"⚠️ {message.author.mention}, please slow down! Sending messages too quickly.", delete_after=4)

    # 4. Chat XP Gain & Super Drop Trigger
    if message.guild and not message.content.startswith(bot.command_prefix):
        now_ts = discord.utils.utcnow().timestamp()
        last_xp = USER_CHAT_XP_COOLDOWN.get(message.author.id, 0.0)
        if now_ts - last_xp >= 60.0:
            USER_CHAT_XP_COOLDOWN[message.author.id] = now_ts
            gained = random.randint(15, 25)
            prev_xp, new_xp = await add_user_xp(message.author.id, gained)
            await handle_level_up(message.author, prev_xp, new_xp, message.channel)

        cat_name = message.channel.category.name if message.channel.category else ""
        valid_channel_names = {"☁️・chat", "🪄・chat-en", "general", "chat"}
        valid_categories = {"Chill Area <3"}

        if message.channel.name in valid_channel_names or cat_name in valid_categories:
            activity_queue = CHANNEL_CHAT_ACTIVITY[message.channel.id]
            activity_queue.append((message.author.id, now_ts))

            recent_msgs = [entry for entry in activity_queue if now_ts - entry[1] <= 120.0]
            unique_active_users = {entry[0] for entry in recent_msgs}

            if len(unique_active_users) >= 3:
                last_super_drop = SUPER_DROP_COOLDOWNS.get(message.channel.id, 0.0)
                if (now_ts - last_super_drop >= SUPER_DROP_COOLDOWN_SECONDS) and (random.random() < 0.05):
                    SUPER_DROP_COOLDOWNS[message.channel.id] = now_ts
                    super_xp = random.randint(1000, 5000)

                    super_embed = discord.Embed(
                        title="🚨 🔥 SUPER XP DROP INCOMING! 🔥 🚨",
                        description=(
                            f"The chat is blazing hot with active members! A **SUPER DROP** has spawned!\n\n"
                            f"🎁 **Reward Range:** `1,000 - 5,000 XP`\n"
                            f"💎 **This Drop:** `+{super_xp:,} XP`\n\n"
                            f"**Click below immediately to claim it!** *(Disappears in 3 minutes)*"
                        ),
                        color=discord.Color.from_rgb(255, 69, 0),
                        timestamp=discord.utils.utcnow()
                    )
                    super_embed.set_footer(text="Triggered by High Server Activity • Chill-Verse")

                    view = SuperXPDropView(xp_amount=super_xp)
                    try:
                        sent_drop = await message.channel.send(embed=super_embed, view=view)
                        view.message = sent_drop
                    except discord.HTTPException:
                        pass

    # 5. Route Allowed Commands (Unconditionally process commands)
    await bot.process_commands(message)

# ==============================================================================
# AUTOMATED TASKS: BACKUPS, BIRTHDAYS & HOURLY DROPS
# ==============================================================================
@tasks.loop(hours=1.0)
async def xp_drop_task():
    await bot.wait_until_ready()
    if MAINTENANCE_MODE:
        return

    valid_channel_names = {"☁️・chat", "🪄・chat-en", "general", "chat"}
    valid_categories = {"Chill Area <3"}

    for guild in bot.guilds:
        eligible_channels: List[discord.TextChannel] = []

        for ch in guild.text_channels:
            cat_name = ch.category.name if ch.category else ""
            if ch.name in valid_channel_names or cat_name in valid_categories:
                perms = ch.permissions_for(guild.me)
                if perms.view_channel and perms.send_messages and perms.embed_links:
                    eligible_channels.append(ch)

        if not eligible_channels:
            continue

        target_channel = random.choice(eligible_channels)
        drop_xp = random.randint(50, 150)

        embed = discord.Embed(
            title="🎁 A WILD XP DROP APPEARED!",
            description=(
                f"Quick! Be the first member to click the button below to claim **+{drop_xp} XP**!\n\n"
                f"*(Disappears in 5 minutes if unclaimed)*"
            ),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Hourly Community Drop • Chill-Verse")

        view = ClaimXPDropView(xp_amount=drop_xp)
        try:
            sent_msg = await target_channel.send(embed=embed, view=view)
            view.message = sent_msg
        except discord.HTTPException:
            pass

@tasks.loop(hours=1.0)
async def hourly_backup_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        backup_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
        if not backup_channel:
            continue

        payload = await generate_unified_backup_payload(guild)
        await safe_write_json(AUTO_BOOT_BACKUP_FILE, payload)

        file = discord.File(io.BytesIO(json.dumps(payload, indent=4).encode("utf-8")), filename="server_backup.json")
        try:
            await backup_channel.send(content="🔒 **Automated Hourly Snapshot (Channels, Perms, Blueprint, XP)**", file=file)
            await prune_old_backups(backup_channel, keep_count=3)
        except Exception:
            pass

@tasks.loop(hours=1.0)
async def birthday_announcer_task():
    await bot.wait_until_ready()
    global ANNOUNCED_BIRTHDAYS_TODAY

    now = datetime.datetime.now(datetime.timezone.utc)
    today_str = now.strftime("%d/%m")

    if now.hour == 0 and len(ANNOUNCED_BIRTHDAYS_TODAY) > 0:
        ANNOUNCED_BIRTHDAYS_TODAY.clear()
        await persist_runtime_state()

    birthdays = await load_birthdays()
    for guild in bot.guilds:
        bday_ch = discord.utils.get(guild.text_channels, name="birthdays")
        if not bday_ch:
            continue

        for uid_str, bdate in birthdays.items():
            if bdate == today_str and int(uid_str) not in ANNOUNCED_BIRTHDAYS_TODAY:
                member = guild.get_member(int(uid_str))
                if member:
                    embed = discord.Embed(
                        title="🎂 HAPPY BIRTHDAY! 🎉",
                        description=f"Happy Birthday {member.mention}! Sending warmest wishes from Chill-Verse!",
                        color=discord.Color.gold(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    try:
                        await bday_ch.send(content=f"🎉 Wish {member.mention} a Happy Birthday today!", embed=embed)
                        ANNOUNCED_BIRTHDAYS_TODAY.append(member.id)
                        await persist_runtime_state()
                    except Exception:
                        pass

# ==============================================================================
# GENERAL & ADMINISTRATIVE COMMANDS
# ==============================================================================
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** Latency: `{latency}ms`")

@bot.command(name="bump")
async def bump(ctx: commands.Context):
    global LAST_BUMP_TIME, BUMP_TIMER_TASK
    guild = ctx.guild

    bump_channel = (
        discord.utils.get(guild.text_channels, name="⏰・bump")
        or discord.utils.get(guild.text_channels, name="bump")
    )

    if bump_channel and ctx.channel.id != bump_channel.id:
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass
        return await ctx.send(
            f"⚠️ {ctx.author.mention}, the `.bump` command can only be used in {bump_channel.mention}!",
            delete_after=6
        )

    now = discord.utils.utcnow()

    if LAST_BUMP_TIME is not None:
        elapsed = (now - LAST_BUMP_TIME).total_seconds()
        if elapsed < BUMP_COOLDOWN_SECONDS:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass

            remaining = int(BUMP_COOLDOWN_SECONDS - elapsed)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"

            lock_embed = discord.Embed(
                title="⛔ BUMP IS CURRENTLY LOCKED!",
                description=(
                    f"**Chill-Verse is on cooldown.**\n\n"
                    f"⏳ **Time Remaining:** `{time_str}`\n"
                    f"🔔 The bot will ping **@Bump Pings** in this channel **15 minutes prior** and **when ready**!"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=lock_embed, delete_after=7)

    LAST_BUMP_TIME = now
    await persist_runtime_state()
    prev_xp, new_total_xp = await add_user_xp(ctx.author.id, 250)
    selected_msg = random.choice(BUMP_PRESET_MESSAGES)

    embed = discord.Embed(
        title="✨ CHILL-VERSE BUMPED! ✨",
        description=(
            f"{selected_msg}\n\n"
            f"🎁 **Reward:** `{ctx.author.display_name}` earned **+250 XP**!\n"
            f"📊 **Total XP:** `{new_total_xp:,} XP` (Level {calculate_level(new_total_xp)})\n\n"
            f"🔒 **Bumping is now locked for the next 2 hours.**"
        ),
        color=discord.Color.gold(),
        timestamp=now
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Dual Reminder Armed: 15m prior alert & final ready ping")
    await ctx.send(embed=embed)

    await handle_level_up(ctx.author, prev_xp, new_total_xp, ctx.channel)

    if BUMP_TIMER_TASK and not BUMP_TIMER_TASK.done():
        BUMP_TIMER_TASK.cancel()

    target_channel = bump_channel or ctx.channel
    BUMP_TIMER_TASK = asyncio.create_task(schedule_bump_timers(ctx.guild, target_channel))

@bot.command(name="xp", aliases=["rank", "level"])
async def check_xp(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    user_xp = await get_user_xp(target.id)
    lvl = calculate_level(user_xp)
    nxt_lvl_xp = xp_for_level(lvl + 1)
    needed = nxt_lvl_xp - user_xp

    current_tier = "None"
    for min_lvl, r_name in LEVEL_TIERS:
        if lvl >= min_lvl:
            current_tier = r_name
            break

    embed = discord.Embed(
        title=f"📊 Level & XP Profile — {target.display_name}",
        color=discord.Color.purple(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Current Level", value=f"**Level {lvl}**", inline=True)
    embed.add_field(name="Total XP", value=f"**{user_xp:,} XP**", inline=True)
    embed.add_field(name="Current Rank Tier", value=f"🛡️ **{current_tier}**", inline=False)
    embed.add_field(name="Next Level At", value=f"**{nxt_lvl_xp:,} XP** (*{needed:,} XP remaining*)", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="addxp", aliases=["givexp"])
@is_authority_holder()
async def addxp(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("⚠️ Please specify an amount greater than 0.", delete_after=5)

    prev_xp, new_xp = await add_user_xp(member.id, amount)
    old_lvl = calculate_level(prev_xp)
    new_lvl = calculate_level(new_xp)

    current_tier_role = await sync_member_level_roles(member, new_xp)

    embed = discord.Embed(
        title="✨ XP Manually Granted",
        description=(
            f"Successfully added **+{amount:,} XP** to {member.mention}!\n\n"
            f"📊 **Total XP:** `{new_xp:,} XP`\n"
            f"🎖️ **Level:** `Level {new_lvl}` " + (f"*(Ranked up from {old_lvl}!)*" if new_lvl > old_lvl else "") + "\n"
            f"🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Granted by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="removexp", aliases=["takexp", "delxp"])
@is_authority_holder()
async def removexp(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("⚠️ Please specify an amount greater than 0.", delete_after=5)

    prev_xp, new_xp = await remove_user_xp(member.id, amount)
    old_lvl = calculate_level(prev_xp)
    new_lvl = calculate_level(new_xp)

    current_tier_role = await sync_member_level_roles(member, new_xp)

    embed = discord.Embed(
        title="🔻 XP Manually Deducted",
        description=(
            f"Successfully deducted **-{amount:,} XP** from {member.mention}.\n\n"
            f"📊 **Total XP:** `{new_xp:,} XP`\n"
            f"🎖️ **Level:** `Level {new_lvl}` " + (f"*(Demoted from {old_lvl})*" if new_lvl < old_lvl else "") + "\n"
            f"🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}"
        ),
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Deducted by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="backup_all")
@commands.has_permissions(administrator=True)
async def backup_all(ctx: commands.Context):
    status_msg = await ctx.send("🔄 **Generating complete unified backup snapshot...**")
    payload = await generate_unified_backup_payload(ctx.guild)
    await safe_write_json(AUTO_BOOT_BACKUP_FILE, payload)

    file_stream = io.BytesIO(json.dumps(payload, indent=4).encode("utf-8"))
    file = discord.File(file_stream, filename=f"chillverse_full_backup_{ctx.guild.id}.json")

    embed = discord.Embed(
        title="🔒 Full System Backup Generated",
        description=(
            f"Successfully archived:\n"
            f"• **Categories & Channels:** `{len(payload['categories'])}`\n"
            f"• **Blueprint Layouts:** Synchronized\n"
            f"• **Database Records:** `{len(payload['user_xp'])}` member profiles\n\n"
            f"*This snapshot is set as your **local auto-restore point on reboot**.*"
        ),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    await status_msg.delete()
    await ctx.send(embed=embed, file=file)

@bot.command(name="restore_all")
@commands.has_permissions(administrator=True)
async def restore_all(ctx: commands.Context):
    if not ctx.message.attachments:
        return await ctx.send(
            "⚠️ **Please attach a backup JSON file when running `.restore_all`!**\n"
            "*(Attach your `chillverse_full_backup.json` and type `.restore_all` in comment box)*",
            delete_after=8
        )

    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith(".json"):
        return await ctx.send("⚠️ Uploaded file must be a `.json` backup file.", delete_after=5)

    status_msg = await ctx.send("🔄 **Processing safe non-destructive restore (Preserving existing channels & perms)...**")

    try:
        content = await attachment.read()
        backup_data = json.loads(content.decode("utf-8"))
    except Exception as e:
        return await status_msg.edit(content=f"⚠️ Failed to parse backup file: `{e}`")

    await safe_write_json(AUTO_BOOT_BACKUP_FILE, backup_data)
    stats = await apply_unified_restore(ctx.guild, backup_data)

    embed = discord.Embed(
        title="✅ Full System Restored Safely",
        description=(
            f"Restoration from `{attachment.filename}` complete:\n\n"
            f"• **Missing Channels Rebuilt:** `{stats['channels_created']}`\n"
            f"• **Missing Permissions Applied:** `{stats['perms_applied']}`\n"
            f"• **Existing Permissions Preserved (Skipped):** `{stats['perms_skipped']}`\n"
            f"• **User XP Profiles Loaded:** `{stats['xp_users']}`\n"
            f"• **Blueprint Synced to Memory:** Active\n\n"
            f"*Zero existing channels were modified or duplicated.*"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await status_msg.edit(content=None, embed=embed)

@bot.command(name="maintenance", aliases=["shutdown", "maintenance_shutdown"])
@commands.has_permissions(administrator=True)
async def maintenance(ctx: commands.Context, *, reason: str = "Scheduled system maintenance and upgrade."):
    confirm_msg = await ctx.send("⚠️ **Initiating Maintenance Shutdown Protocol...**\n"
                                 "• Flushing database states to disk\n"
                                 "• Archiving channels, permissions & blueprint\n"
                                 "• Shutting down runtime process...")

    try:
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="⚠️ System Shutting Down")
        )
    except Exception:
        pass

    await persist_runtime_state()

    for guild in bot.guilds:
        try:
            payload = await generate_unified_backup_payload(guild)
            await safe_write_json(AUTO_BOOT_BACKUP_FILE, payload)

            err_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
            if err_channel:
                file_stream = io.BytesIO(json.dumps(payload, indent=4).encode("utf-8"))
                backup_file = discord.File(file_stream, filename=f"pre_maintenance_backup_{guild.id}.json")

                shutdown_embed = discord.Embed(
                    title="🛑 SYSTEM MAINTENANCE SHUTDOWN",
                    description=(
                        f"**Authorized by:** {ctx.author.mention}\n"
                        f"**Reason:** *{reason}*\n\n"
                        "🔒 **Pre-Shutdown Full Backup Attached.**\n"
                        "All runtime states, XP databases, and channel permission rules have been preserved.\n"
                        "The bot process is now disconnecting from Discord."
                    ),
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow()
                )
                shutdown_embed.set_footer(text="Arkbot Architecture Shutdown Engine")
                await err_channel.send(embed=shutdown_embed, file=backup_file)
                await prune_old_backups(err_channel, keep_count=3)
        except Exception as e:
            print(f"[Maintenance Shutdown Error] Guild {guild.id}: {e}")

    final_embed = discord.Embed(
        title="🛑 Process Termination Completed",
        description=(
            "✅ Full state snapshot archived to disk.\n"
            "✅ Backup JSON uploaded to `🩸・bot-errors`.\n"
            "🔌 Disconnecting gateway and exiting process now."
        ),
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    await confirm_msg.edit(content=None, embed=final_embed)

    if hourly_backup_task.is_running():
        hourly_backup_task.cancel()
    if birthday_announcer_task.is_running():
        birthday_announcer_task.cancel()
    if xp_drop_task.is_running():
        xp_drop_task.cancel()

    await asyncio.sleep(1.0)
    await bot.close()
    sys.exit(0)

# ==============================================================================
# ZERO-DUPLICATION ZERO-OVERWRITE CHANNEL & ROLE PROVISIONING
# ==============================================================================
@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def setup_channels(ctx: commands.Context):
    guild = ctx.guild
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]

    status_msg = await ctx.send("🔍 **Analyzing live structure to guarantee zero duplicates or overwrites...**")

    existing_categories = {normalize_name(cat.name): cat for cat in guild.categories}

    created_cats = 0
    created_channels = 0
    skipped_channels = 0

    for cat_data in SERVER_BLUEPRINT:
        raw_cat_name = cat_data["category"]
        norm_cat_name = normalize_name(raw_cat_name)

        if norm_cat_name in existing_categories:
            category = existing_categories[norm_cat_name]
        else:
            category = await guild.create_category(name=raw_cat_name, reason="Non-Destructive Blueprint Provisioning")
            existing_categories[norm_cat_name] = category
            created_cats += 1
            await asyncio.sleep(0.4)

        existing_channels_in_cat = {normalize_name(ch.name): ch for ch in category.channels}

        for ch_info in cat_data["channels"]:
            raw_ch_name = ch_info["name"]
            norm_ch_name = normalize_name(raw_ch_name)
            ch_type = ch_info["type"]
            is_restricted = ch_info.get("restricted", False)
            is_read_only = ch_info.get("read_only", False)
            user_lim = ch_info.get("user_limit", 0)

            if norm_ch_name in existing_channels_in_cat:
                skipped_channels += 1
                continue

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False if is_restricted else True,
                    send_messages=False if (is_restricted or is_read_only) else True,
                    add_reactions=True,
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True
                )
            }
            for rname in admin_roles:
                r = discord.utils.get(guild.roles, name=rname)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )

            try:
                if ch_type == "text":
                    new_ch = await guild.create_text_channel(
                        name=raw_ch_name,
                        category=category,
                        overwrites=overwrites,
                        reason="Non-Destructive Missing Channel Creation"
                    )
                elif ch_type == "voice":
                    new_ch = await guild.create_voice_channel(
                        name=raw_ch_name,
                        category=category,
                        user_limit=user_lim,
                        overwrites=overwrites,
                        reason="Non-Destructive Missing Channel Creation"
                    )
                elif ch_type == "forum":
                    try:
                        new_ch = await guild.create_forum_channel(
                            name=raw_ch_name,
                            category=category,
                            overwrites=overwrites,
                            reason="Non-Destructive Missing Channel Creation"
                        )
                    except (discord.HTTPException, AttributeError):
                        new_ch = await guild.create_text_channel(
                            name=raw_ch_name,
                            category=category,
                            overwrites=overwrites,
                            reason="Non-Destructive Missing Channel Creation (Forum Fallback)"
                        )

                existing_channels_in_cat[norm_ch_name] = new_ch
                created_channels += 1
                await asyncio.sleep(0.4)

            except discord.HTTPException as e:
                print(f"Failed to create channel {raw_ch_name}: {e}")

    await get_or_create_memory_channel(guild)
    await get_or_create_audit_channel(guild)

    embed = discord.Embed(
        title="✅ Server Blueprint Checked & Synced",
        description=(
            f"**Safe Provisioning Complete:**\n\n"
            f"• **New Categories Created:** `{created_cats}`\n"
            f"• **New Channels Created:** `{created_channels}`\n"
            f"• **Existing Channels Preserved (Skipped):** `{skipped_channels}`\n\n"
            f"*Zero existing channels or configurations were modified, overwritten, or duplicated.*"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await status_msg.edit(content=None, embed=embed)

@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx: commands.Context):
    guild = ctx.guild
    status_msg = await ctx.send("⚙️ **Checking server roles... Skips existing to prevent duplicates/overwrites.**")

    base_perms = discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)

    roles_to_create = [
        {"name": "Supreme Leader", "perms": discord.Permissions(administrator=True), "color": discord.Color.dark_red(), "hoist": True},
        {"name": "Highness", "perms": discord.Permissions(administrator=True), "color": discord.Color.gold(), "hoist": True},
        {"name": "Authority", "perms": discord.Permissions(ban_members=True, kick_members=True, manage_channels=True, manage_roles=True), "color": discord.Color.orange(), "hoist": True},
        {"name": "Head Moderator", "perms": discord.Permissions(ban_members=True, kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.red(), "hoist": True},
        {"name": "Moderator", "perms": discord.Permissions(kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.yellow(), "hoist": True},
        {"name": "Trial Mod", "perms": discord.Permissions(moderate_members=True, manage_messages=True), "color": discord.Color.blue(), "hoist": True},
        {"name": "Chill-Verse Team", "perms": discord.Permissions(view_channel=True, send_messages=True, read_message_history=True), "color": getattr(discord.Color, "dark_theme", lambda: discord.Color(0x313338))(), "hoist": True},
        {"name": "Sovereign (Levels 60-70)", "perms": base_perms, "color": discord.Color.purple(), "hoist": True},
        {"name": "Legend (Levels 50-59)", "perms": base_perms, "color": discord.Color.dark_purple(), "hoist": False},
        {"name": "Champion (Levels 40-49)", "perms": base_perms, "color": getattr(discord.Color, "brand_red", lambda: discord.Color(0xED4245))(), "hoist": False},
        {"name": "Elite (Levels 30-39)", "perms": base_perms, "color": discord.Color.dark_green(), "hoist": False},
        {"name": "Vanguard (Levels 20-29)", "perms": base_perms, "color": discord.Color.green(), "hoist": False},
        {"name": "Explorer (Levels 10-19)", "perms": base_perms, "color": discord.Color.teal(), "hoist": False},
        {"name": "Newbie (Levels 1-9)", "perms": base_perms, "color": discord.Color.light_grey(), "hoist": False},
        {"name": "Member", "perms": base_perms, "color": discord.Color.default(), "hoist": False},
        {"name": "OG", "perms": base_perms, "color": discord.Color.dark_gold(), "hoist": False},
        {"name": "Veteran", "perms": base_perms, "color": discord.Color.dark_grey(), "hoist": False},
        {"name": "Vanity", "perms": base_perms, "color": discord.Color.magenta(), "hoist": False},
        {"name": "Bump Pings", "perms": discord.Permissions.none(), "color": discord.Color.purple(), "hoist": False},
        {"name": "Poll Pings", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Roblox Members", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Male", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Female", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Non-Binary", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Yellow", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 255, 0), "hoist": False},
        {"name": "Red", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 0, 0), "hoist": False},
        {"name": "Pink", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 105, 180), "hoist": False},
        {"name": "Orange", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 165, 0), "hoist": False},
        {"name": "Blue", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(0, 0, 255), "hoist": False},
        {"name": "Green", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(0, 128, 0), "hoist": False},
    ]

    existing_role_names = {r.name.lower().strip() for r in guild.roles}

    created_count = 0
    skipped_count = 0

    for role_data in roles_to_create:
        r_name_clean = role_data["name"].lower().strip()
        if r_name_clean in existing_role_names:
            skipped_count += 1
            continue

        try:
            await guild.create_role(
                name=role_data["name"],
                permissions=role_data["perms"],
                color=role_data["color"],
                hoist=role_data["hoist"],
                reason="Non-Destructive Role Provisioning"
            )
            existing_role_names.add(r_name_clean)
            created_count += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Failed to create role {role_data['name']}: {e}")

    await status_msg.edit(
        content=f"✅ **Role Sync Complete:** Created **{created_count}** missing role(s). Preserved **{skipped_count}** existing role(s) without modifications."
    )

@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx: commands.Context):
    ch = discord.utils.get(ctx.guild.text_channels, name="🎫・tickets")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🎫・tickets`. Run `.setup_channels` first.")

    embed = discord.Embed(
        title="🎫 Chill-Verse Support & Staff Applications",
        description="Need help from staff, want to report an issue, or apply to join the Team?\n\nChoose an option below:",
        color=discord.Color.blue()
    )
    await ch.send(embed=embed, view=TicketView())
    await ctx.send("✅ Support & Application panel deployed to `🎫・tickets`!")

@bot.command(name="setup_roles_panel")
@commands.has_permissions(administrator=True)
async def setup_roles_panel(ctx: commands.Context):
    ch = discord.utils.get(ctx.guild.text_channels, name="🎨・colours")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🎨・colours`. Run `.setup_channels` first.")

    embed = discord.Embed(
        title="🎨 Chill-Verse Custom Roles & Pings",
        description="Click any button below to toggle color roles or notification pings!",
        color=discord.Color.magenta()
    )
    await ch.send(embed=embed, view=ReactionRoleView())
    await ctx.send("✅ Color & Ping panel deployed to `🎨・colours`!")

@bot.command(name="purge")
@is_authority_holder()
async def purge(ctx: commands.Context, amount: int = 10, target: Optional[Union[discord.Member, str]] = None):
    if amount < 1 or amount > 1000:
        return await ctx.send("⚠️ Specify a message count between 1 and 1,000.", delete_after=5)

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

    def purge_check(m: discord.Message) -> bool:
        if m.pinned:
            return False
        if isinstance(target, discord.Member):
            return m.author.id == target.id
        elif isinstance(target, str):
            t_lower = target.lower()
            if t_lower in ["bot", "bots"]:
                return m.author.bot
            if t_lower in ["link", "links"]:
                return bool(INVITE_REGEX.search(m.content) or "http://" in m.content.lower() or "https://" in m.content.lower())
        return True

    deleted_total = 0
    cutoff = discord.utils.utcnow() - datetime.timedelta(days=14)

    while deleted_total < amount:
        batch_limit = min(amount - deleted_total, 100)
        deleted_batch = await ctx.channel.purge(limit=batch_limit, check=purge_check, after=cutoff)
        count = len(deleted_batch)
        deleted_total += count
        if count < batch_limit:
            break
        await asyncio.sleep(0.5)

    if deleted_total < amount:
        remaining = amount - deleted_total
        async for old_msg in ctx.channel.history(limit=remaining, before=cutoff):
            if purge_check(old_msg):
                try:
                    await old_msg.delete()
                    deleted_total += 1
                    await asyncio.sleep(0.3)
                except (discord.NotFound, discord.HTTPException):
                    pass

    target_desc = f"from {target.mention}" if isinstance(target, discord.Member) else (f"matching `{target}`" if target else "")
    await ctx.send(f"🧹 Cleared **{deleted_total}** message(s) {target_desc}.", delete_after=4)

@bot.command(name="afk")
async def afk(ctx: commands.Context, *, reason: str = None):
    selected_status = reason if reason else random.choice(AFK_PRESET_MESSAGES)
    AFK_USERS[ctx.author.id] = {
        "reason": selected_status,
        "time": discord.utils.utcnow()
    }
    await persist_runtime_state()

    embed = discord.Embed(
        description=f"🌙 **{ctx.author.display_name} is now AFK**\n*{selected_status}*",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, delete_after=10)
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

@bot.command(name="refresh_rules")
@commands.has_permissions(administrator=True)
async def refresh_rules(ctx: commands.Context):
    await deploy_team_rules_panel(ctx.guild)
    await ctx.send("✅ **Team rules and command manual updated successfully in `🛡️・team-rules`!**", delete_after=5)

# ==============================================================================
# RUN BOT
# ==============================================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("⚠️ CRITICAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is missing!")
    else:
        bot.run(TOKEN)
