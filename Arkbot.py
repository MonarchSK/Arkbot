import asyncio
import datetime
import io
import json
import os
import random
import re
import signal
import sys
import traceback
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple, Union

import discord
from discord.ext import commands, tasks
from discord.ui import Button, Modal, TextInput, View

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
CONFESSIONS_FILE = "confessions.json"
MASTER_BACKUP_TEMPLATE = "master_backup_{guild_id}.json"

# In-memory caches & state
AFK_USERS: Dict[int, Dict[str, Any]] = {}
LAST_BUMP_TIME: Optional[datetime.datetime] = None
BUMP_TIMER_TASK: Optional[asyncio.Task] = None
BUMP_COOLDOWN_SECONDS = 7200  # 2 Hours
ANNOUNCED_BIRTHDAYS_TODAY: List[int] = []
REMINDED_BIRTHDAYS_TOMORROW: List[int] = []

# Chat Revive State & Cooldowns
LAST_REVIVE_TIME: Dict[int, float] = {}
REVIVE_COOLDOWN_SECONDS = 2700  # 45 Minutes Guild Cooldown

# XP In-Memory Cache
XP_CACHE: Dict[str, int] = {}
XP_CACHE_DIRTY = False

# Super Drop tracking (4 Hours Cooldown)
CHANNEL_CHAT_ACTIVITY: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
SUPER_DROP_COOLDOWNS: Dict[int, float] = {}
SUPER_DROP_COOLDOWN_SECONDS = 14400  # 4 Hours

# Message rate tracking
USER_MESSAGE_TIMESTAMPS: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))
USER_CHAT_XP_COOLDOWN: Dict[int, float] = {}
INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9_-]+",
    re.IGNORECASE,
)

SYSTEM_CHANNELS = {
    "bot-memory",
    "📜・audit-logs",
    "audit-logs",
    "🩸・bot-errors",
    "bot-errors",
    "🧪・bot-testing",
    "bot-testing",
}

LEVEL_TIERS: List[Tuple[int, str]] = [
    (60, "Sovereign (Levels 60-70)"),
    (50, "Legend (Levels 50-59)"),
    (40, "Champion (Levels 40-49)"),
    (30, "Elite (Levels 30-39)"),
    (20, "Vanguard (Levels 20-29)"),
    (10, "Explorer (Levels 10-19)"),
    (1, "Newbie (Levels 1-9)"),
]

COLOR_ROLES = ["Red", "Yellow", "Green", "Blue", "Orange", "Pink"]

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
    "🌧️ Drifting into silent solitude to heal and recharge. Keep a warm thought for me.",
]

AFK_WELCOME_MESSAGES = [
    "☀️ You're back! The entire room just lit up. Welcome back, {user}!",
    "💖 Welcome back, {user}! The server felt far too quiet without your energy!",
    "🎉 Look who returned! We missed you so much, {user}!",
    "🥳 You're finally back! Everything feels complete again. Welcome home, {user}!",
    "✨ Warmest welcome back, {user}! So genuinely happy to see you chatting again!",
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
    "🌙 **Twilight Ascendance!** Our voices echo louder thanks to your bump. Thank you for showing love!",
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
    "🎈 **Prepare for Liftoff!** 15 minutes on the countdown. Get your `.bump` command primed!",
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
    "💫 **BOOST WINDOW LIVE!** Let's make Chill-Verse shine across Discord again. Hit `.bump` now!",
]

REVIVE_ICEBREAKERS = [
    "If you could have any superpower for 24 hours, what would it be and why?",
    "What's your current favorite video game or series that you can't put down?",
    "If you could travel to any country tomorrow with everything paid for, where are you going?",
    "What is the single best food to eat while binge-watching shows?",
    "If you had to listen to only one music artist for an entire month, who is it?",
    "What's an unpopular opinion you have that will make everyone in chat debate?",
    "Coffee, Chai, Energy Drinks, or Cold Water? What fuels your day?",
    "What was the most fun thing that happened to you this week?",
    "If you could instantly master any language or musical instrument, which would you pick?",
    "What is your all-time favorite movie that you can rewatch without getting bored?",
]

# ==============================================================================
# SERVER BLUEPRINT
# ==============================================================================
SERVER_BLUEPRINT: List[Dict[str, Any]] = [
    {
        "category": "Welcome",
        "channels": [
            {"name": "📢・announcements", "type": "text", "restricted": False, "read_only": True},
            {"name": "server-rules", "type": "text", "restricted": False, "read_only": True},
            {"name": "👋・welcome", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "team-news", "type": "text", "restricted": True},
            {"name": "🛡️・team-rules", "type": "text", "restricted": True},
            {"name": "💬・team-chat", "type": "text", "restricted": True},
            {"name": "⏰・bump", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Events <3",
        "channels": [
            {"name": "🎉・gwys", "type": "text", "restricted": False},
            {"name": "⭐・vouch", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Chill Area <3",
        "channels": [
            {"name": "discussions-🐣", "type": "forum", "restricted": False},
            {"name": "☁️・chat", "type": "text", "restricted": False},
            {"name": "🍸・chat-ai", "type": "text", "restricted": False},
            {"name": "🪄・chat-en", "type": "text", "restricted": False},
            {"name": "🐥・discussions", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Media <3",
        "channels": [
            {"name": "pfp-share🛼", "type": "text", "restricted": False},
            {"name": "media-share🪹", "type": "text", "restricted": False},
            {"name": "selfies🫂", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Fun Area <3",
        "channels": [
            {"name": "playground-🥊", "type": "text", "restricted": False},
            {"name": "birthdays", "type": "text", "restricted": False},
            {"name": "🚦confession-🖇️", "type": "text", "restricted": False},
            {"name": "memes🤪", "type": "text", "restricted": False},
            {"name": "🖇️-daily-polls", "type": "text", "restricted": False},
            {"name": "🖇️-roblox-elites", "type": "text", "restricted": False},
            {"name": "🧩・puzzles", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Hobbies <3",
        "channels": [
            {"name": "photography📷", "type": "text", "restricted": False},
            {"name": "arts-and-crafts🎨", "type": "text", "restricted": False},
            {"name": "🎤drop-your-songs", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Voice Chat <3",
        "channels": [
            {"name": "🍕 | chit-chat", "type": "voice", "restricted": False, "user_limit": 12},
            {"name": "🍔 | Duo", "type": "voice", "restricted": False, "user_limit": 2},
            {"name": "🍞 | Trio", "type": "voice", "restricted": False, "user_limit": 3},
            {"name": "🧀 | squad", "type": "voice", "restricted": False, "user_limit": 4},
            {"name": "🍺 | Vip", "type": "voice", "restricted": False, "user_limit": 50},
        ],
    },
    {
        "category": "Music <3",
        "channels": [
            {"name": "🎵 Hade Music", "type": "voice", "restricted": False},
            {"name": "🎸 -Atom Music", "type": "voice", "restricted": False},
        ],
    },
    {
        "category": "Info 🩵",
        "channels": [
            {"name": "📢・level-announcements", "type": "text", "restricted": False, "read_only": True},
            {"name": "🎫・tickets", "type": "text", "restricted": False},
            {"name": "🎨・colours", "type": "text", "restricted": False},
        ],
    },
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "💼・bot-commands", "type": "text", "restricted": True},
            {"name": "📜・audit-logs", "type": "text", "restricted": True},
            {"name": "🩸・bot-errors", "type": "text", "restricted": True},
            {"name": "🧪・bot-testing", "type": "text", "restricted": True},
        ],
    },
]

# ==============================================================================
# ASYNC STORAGE & CACHING ENGINE
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


async def init_xp_cache():
    global XP_CACHE, XP_CACHE_DIRTY
    XP_CACHE = await safe_read_json(XP_DATABASE_FILE, {})
    XP_CACHE_DIRTY = False


async def flush_xp_cache():
    global XP_CACHE_DIRTY
    if XP_CACHE_DIRTY:
        await safe_write_json(XP_DATABASE_FILE, XP_CACHE)
        XP_CACHE_DIRTY = False


async def get_user_xp(user_id: int) -> int:
    return XP_CACHE.get(str(user_id), 0)


async def add_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    new_xp = prev_xp + amount
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp


async def remove_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    new_xp = max(0, prev_xp - amount)
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp


async def set_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    new_xp = max(0, amount)
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp


def calculate_level(xp: int) -> int:
    if xp <= 0:
        return 0
    return int((xp / 75) ** 0.5)


def xp_for_level(level: int) -> int:
    return int(75 * (level**2))


async def load_birthdays() -> Dict[str, str]:
    return await safe_read_json(BIRTHDAYS_FILE, {})


async def save_birthdays(data: Dict[str, str]) -> None:
    await safe_write_json(BIRTHDAYS_FILE, data)


async def record_confession(user_id: int, content: str) -> int:
    data = await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []})
    new_id = data.get("last_id", 0) + 1
    data["last_id"] = new_id
    if "entries" not in data or not isinstance(data["entries"], list):
        data["entries"] = []
    data["entries"].append(
        {
            "id": new_id,
            "user_id": user_id,
            "content": content,
            "timestamp": discord.utils.utcnow().isoformat(),
        }
    )
    await safe_write_json(CONFESSIONS_FILE, data)
    return new_id


async def persist_runtime_state():
    state = {
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
        "afk_users": {
            str(uid): {
                "reason": info["reason"],
                "time": info["time"].isoformat(),
            }
            for uid, info in AFK_USERS.items()
        },
        "announced_birthdays_today": ANNOUNCED_BIRTHDAYS_TODAY,
        "reminded_birthdays_tomorrow": REMINDED_BIRTHDAYS_TOMORROW,
        "maintenance_mode": MAINTENANCE_MODE,
    }
    await safe_write_json(STATE_FILE, state)


async def restore_runtime_state():
    global LAST_BUMP_TIME, AFK_USERS, ANNOUNCED_BIRTHDAYS_TODAY, REMINDED_BIRTHDAYS_TOMORROW, MAINTENANCE_MODE
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
                "time": datetime.datetime.fromisoformat(data["time"]),
            }
        except Exception:
            continue

    ANNOUNCED_BIRTHDAYS_TODAY = state.get("announced_birthdays_today", [])
    REMINDED_BIRTHDAYS_TOMORROW = state.get("reminded_birthdays_tomorrow", [])
    MAINTENANCE_MODE = state.get("maintenance_mode", False)


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
        r
        for r in member.roles
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


async def handle_level_up(
    member: discord.Member,
    prev_xp: int,
    new_xp: int,
    fallback_ch: Optional[discord.abc.Messageable] = None,
):
    old_lvl = calculate_level(prev_xp)
    new_lvl = calculate_level(new_xp)

    if new_lvl <= old_lvl:
        return

    unlocked_role = await sync_member_level_roles(member, new_xp)

    lvl_channel = discord.utils.get(member.guild.text_channels, name="📢・level-announcements") or fallback_ch
    if lvl_channel and hasattr(lvl_channel, "send"):
        embed = discord.Embed(
            title="🎊 LEVEL UP! 🎊",
            description=f"Congratulations {member.mention}! You leveled up from **Level {old_lvl}** to **Level {new_lvl}**!",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
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
# AUTHORITY CHECKS & SYSTEM HELPERS
# ==============================================================================
def is_authority_holder():
    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        authority_roles = {"supreme leader", "highness", "authority"}
        user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
        if bool(authority_roles.intersection(user_roles)):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Administrators and Authority holders can execute this command.")

    return commands.check(predicate)


def is_purge_authorized():
    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        purge_roles = {"supreme leader", "highness", "authority"}
        user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
        if bool(purge_roles.intersection(user_roles)):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** The purge command is strictly reserved for **Supreme Leader**, **Highness**, and **Authority**.")

    return commands.check(predicate)


def is_team_member(member: Union[discord.Member, discord.User]) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if getattr(member.guild_permissions, "administrator", False):
        return True
    team_roles = {
        "supreme leader",
        "highness",
        "authority",
        "head moderator",
        "moderator",
        "trial mod",
        "chill-verse team",
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


# ==============================================================================
# ADMIN AREA SECURITY ENFORCER
# ==============================================================================
async def enforce_admin_area_security(guild: discord.Guild):
    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    if not admin_cat:
        return

    supreme_role = discord.utils.get(guild.roles, name="Supreme Leader")
    highness_role = discord.utils.get(guild.roles, name="Highness")

    strict_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            manage_channels=True,
            manage_permissions=True,
            attach_files=True,
        ),
    }

    if supreme_role:
        strict_overwrites[supreme_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
    if highness_role:
        strict_overwrites[highness_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )

    try:
        for target in list(admin_cat.overwrites.keys()):
            if target not in strict_overwrites:
                await admin_cat.set_permissions(target, overwrite=None)
        await admin_cat.edit(overwrites=strict_overwrites)
    except Exception as e:
        print(f"[Security Enforcer] Failed setting Admin Area category permissions: {e}")

    for ch in admin_cat.channels:
        try:
            for target in list(ch.overwrites.keys()):
                if target not in strict_overwrites:
                    await ch.set_permissions(target, overwrite=None)
            await ch.edit(overwrites=strict_overwrites)
        except Exception:
            pass


async def get_or_create_audit_channel(guild: discord.Guild) -> discord.TextChannel:
    target_name = "📜・audit-logs"
    ch = discord.utils.get(guild.text_channels, name=target_name) or discord.utils.get(guild.text_channels, name="audit-logs")
    if ch:
        return ch

    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    admin_roles = ["Supreme Leader", "Highness"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            manage_channels=True,
        ),
    }

    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(
        name=target_name,
        category=admin_cat,
        overwrites=overwrites,
        reason="Private Audit Channel (Supreme Leader, Highness & Arkbot only)",
    )


async def get_or_create_testing_channel(guild: discord.Guild) -> discord.TextChannel:
    target_name = "🧪・bot-testing"
    ch = discord.utils.get(guild.text_channels, name=target_name) or discord.utils.get(guild.text_channels, name="bot-testing")
    if ch:
        return ch

    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    admin_roles = ["Supreme Leader", "Highness"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            manage_channels=True,
        ),
    }

    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    return await guild.create_text_channel(
        name=target_name,
        category=admin_cat,
        overwrites=overwrites,
        reason="Diagnostics Channel (Supreme Leader, Highness & Arkbot only)",
    )


async def get_or_create_memory_channel(guild: discord.Guild) -> discord.TextChannel:
    memory_ch = discord.utils.get(guild.text_channels, name="bot-memory")
    if memory_ch:
        return memory_ch

    admin_roles = ["Supreme Leader", "Highness"]
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
        ),
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(
        name="bot-memory",
        overwrites=overwrites,
        reason="Arkbot State Engine (Supreme Leader, Highness & Arkbot only)",
    )


async def find_latest_backup_from_discord(guild: discord.Guild) -> Optional[Dict[str, Any]]:
    channels = [
        discord.utils.get(guild.text_channels, name="🩸・bot-errors"),
        discord.utils.get(guild.text_channels, name="bot-errors"),
        discord.utils.get(guild.text_channels, name="bot-memory"),
    ]
    for ch in channels:
        if not ch:
            continue
        try:
            async for msg in ch.history(limit=50):
                if msg.author == guild.me and msg.attachments:
                    for att in msg.attachments:
                        if att.filename.endswith(".json"):
                            content = await att.read()
                            data = json.loads(content.decode("utf-8"))
                            if isinstance(data, dict) and ("user_xp" in data or "categories" in data):
                                return data
        except Exception as e:
            print(f"[Backup Search] Failed scanning #{ch.name}: {e}")
    return None


async def purge_all_old_backups(channel: discord.TextChannel):
    """Enforces single master backup retention by removing previous backups."""
    try:
        async for msg in channel.history(limit=100):
            if msg.author == channel.guild.me:
                has_backup_file = any(att.filename.endswith(".json") for att in msg.attachments)
                has_backup_text = "backup" in msg.content.lower() or "snapshot" in msg.content.lower()
                if has_backup_file or has_backup_text:
                    try:
                        await msg.delete()
                        await asyncio.sleep(0.3)
                    except (discord.NotFound, discord.HTTPException):
                        pass
    except Exception as e:
        print(f"Failed purging old backups: {e}")


# ==============================================================================
# UNIFIED SINGLE BACKUP & RESTORATION ENGINE
# ==============================================================================
async def generate_unified_backup_payload(guild: discord.Guild) -> Dict[str, Any]:
    await flush_xp_cache()

    categories_data = []
    for cat in guild.categories:
        cat_overwrites = {}
        for target, overwrite in cat.overwrites.items():
            allow, deny = overwrite.pair()
            cat_overwrites[str(target.id)] = {
                "name": target.name,
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": allow.value,
                "deny": deny.value,
            }

        cat_entry = {
            "name": cat.name,
            "position": cat.position,
            "overwrites": cat_overwrites,
            "channels": [],
        }

        for ch in cat.channels:
            ch_overwrites = {}
            for target, overwrite in ch.overwrites.items():
                allow, deny = overwrite.pair()
                ch_overwrites[str(target.id)] = {
                    "name": target.name,
                    "type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": allow.value,
                    "deny": deny.value,
                }

            cat_entry["channels"].append(
                {
                    "name": ch.name,
                    "type": str(ch.type),
                    "position": ch.position,
                    "user_limit": getattr(ch, "user_limit", 0),
                    "overwrites": ch_overwrites,
                }
            )
        categories_data.append(cat_entry)

    current_blueprint = []
    for cat in guild.categories:
        cat_blueprint = {"category": cat.name, "channels": []}
        for ch in cat.channels:
            if ch.name in SYSTEM_CHANNELS:
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
                "read_only": is_read_only,
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
                "hoist": r.hoist,
            }
            for r in guild.roles
            if not r.is_default() and not r.managed
        ],
        "user_xp": XP_CACHE.copy(),
        "user_birthdays": await load_birthdays(),
        "confessions": await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []}),
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
    }


async def apply_unified_restore(guild: discord.Guild, data: Dict[str, Any]) -> Dict[str, int]:
    global SERVER_BLUEPRINT, LAST_BUMP_TIME, XP_CACHE, XP_CACHE_DIRTY

    stats = {
        "channels_created": 0,
        "perms_applied": 0,
        "perms_skipped": 0,
        "xp_users": 0,
        "birthdays": 0,
        "confessions": 0,
    }

    saved_blueprint = data.get("blueprint")
    if saved_blueprint and isinstance(saved_blueprint, list):
        SERVER_BLUEPRINT = saved_blueprint

    # 1. Restore XP Data
    raw_xp = data.get("user_xp") or {}
    if raw_xp:
        for uid, xp_val in raw_xp.items():
            try:
                val = int(xp_val)
                XP_CACHE[str(uid)] = max(XP_CACHE.get(str(uid), 0), val)
            except (ValueError, TypeError):
                continue
        XP_CACHE_DIRTY = True
        stats["xp_users"] = len(raw_xp)
        await flush_xp_cache()

        for uid_str, xp_val in XP_CACHE.items():
            try:
                member = guild.get_member(int(uid_str))
                if member:
                    await sync_member_level_roles(member, xp_val)
            except Exception:
                pass

    # 2. Restore Birthday Records
    raw_bdays = data.get("user_birthdays") or {}
    if raw_bdays:
        curr_bdays = await load_birthdays()
        curr_bdays.update(raw_bdays)
        await save_birthdays(curr_bdays)
        stats["birthdays"] = len(curr_bdays)

    # 3. Restore Confession State
    raw_confessions = data.get("confessions")
    if raw_confessions and isinstance(raw_confessions, dict):
        curr_confessions = await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []})
        merged_last_id = max(curr_confessions.get("last_id", 0), raw_confessions.get("last_id", 0))

        existing_entry_ids = {e["id"] for e in curr_confessions.get("entries", []) if isinstance(e, dict) and "id" in e}
        combined_entries = list(curr_confessions.get("entries", []))

        for entry in raw_confessions.get("entries", []):
            if isinstance(entry, dict) and entry.get("id") not in existing_entry_ids:
                combined_entries.append(entry)
                existing_entry_ids.add(entry["id"])

        updated_confession_payload = {
            "last_id": merged_last_id,
            "entries": combined_entries,
        }
        await safe_write_json(CONFESSIONS_FILE, updated_confession_payload)
        stats["confessions"] = len(combined_entries)

    # 4. Restore Bump Time
    raw_bump = data.get("last_bump_time")
    if raw_bump:
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_bump, datetime.timezone.utc)
        await persist_runtime_state()

    # 5. Restore Categories, Channels, & Overwrites
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
                    await category.set_permissions(
                        target,
                        overwrite=discord.PermissionOverwrite.from_pair(allow, deny),
                    )
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
                        await channel.set_permissions(
                            target,
                            overwrite=discord.PermissionOverwrite.from_pair(allow, deny),
                        )
                        stats["perms_applied"] += 1
                    except Exception:
                        pass

    await enforce_admin_area_security(guild)
    return stats


# ==============================================================================
# BUMP NOTIFICATION ENGINE
# ==============================================================================
def get_bump_role_mentions(guild: discord.Guild) -> str:
    bump_role = discord.utils.find(
        lambda r: r.name.lower().strip() in ["bump pings", "bump ping", "bumping"],
        guild.roles,
    )
    return bump_role.mention if bump_role else "@here"


async def schedule_bump_timers(guild: discord.Guild, origin_channel: discord.TextChannel, initial_delay: int = 0):
    target_channel = discord.utils.get(guild.text_channels, name="⏰・bump") or discord.utils.get(
        guild.text_channels, name="bump"
    )

    if not target_channel:
        return

    try:
        fifteen_min_mark = 6300 - initial_delay
        if fifteen_min_mark > 0:
            await asyncio.sleep(fifteen_min_mark)
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
                timestamp=discord.utils.utcnow(),
            )
            reminder_embed.set_footer(text="Chill-Verse Bump Watch • 15 Minute Notice")
            await target_channel.send(content=pings, embed=reminder_embed)

        ready_mark = max(0, BUMP_COOLDOWN_SECONDS - initial_delay - max(0, fifteen_min_mark))
        await asyncio.sleep(ready_mark)

        pings = get_bump_role_mentions(guild)
        msg_ready = random.choice(BUMP_READY_MESSAGES)

        ready_embed = discord.Embed(
            title="🔔 Chill-Verse is Ready to Bump!",
            description=(
                f"{msg_ready}\n\n"
                f"Type **`.bump`** right now to boost the server and claim your **+250 XP** reward!"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        ready_embed.set_footer(text="Cooldown Ended • Bump Unlocked")
        await target_channel.send(content=pings, embed=ready_embed)

    except asyncio.CancelledError:
        pass


# ==============================================================================
# UI COMPONENTS (XP DROPS WITH AUTO-DISAPPEAR, CONFESSIONS, COLOURS, TICKETS, BDAY)
# ==============================================================================
async def _schedule_message_deletion(message: Optional[discord.Message], delay: float = 7.0):
    """Helper to cleanly delete a message after a brief delay."""
    if not message:
        return
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except (discord.NotFound, discord.HTTPException):
        pass


class ClaimXPDropView(View):
    def __init__(self, xp_amount: int):
        super().__init__(timeout=300.0)  # 5 Minutes timeout
        self.xp_amount = xp_amount
        self.claimed = False
        self.message: Optional[discord.Message] = None

    async def on_timeout(self):
        # Auto-disappear if left unclaimed
        if not self.claimed and self.message:
            try:
                await self.message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass

    @discord.ui.button(label="🎁 Claim XP", style=discord.ButtonStyle.green)
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
                f"📊 **Total XP:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})\n\n"
                f"*✨ This message will disappear in a few seconds.*"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

        # Disappear 7 seconds after claim
        target_msg = self.message or interaction.message
        asyncio.create_task(_schedule_message_deletion(target_msg, delay=7.0))

        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)


class SuperXPDropView(View):
    def __init__(self, xp_amount: int):
        super().__init__(timeout=180.0)  # 3 Minutes timeout
        self.xp_amount = xp_amount
        self.claimed = False
        self.message: Optional[discord.Message] = None

    async def on_timeout(self):
        # Auto-disappear if left unclaimed
        if not self.claimed and self.message:
            try:
                await self.message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass

    @discord.ui.button(label="⚡ CLAIM SUPER DROP ⚡", style=discord.ButtonStyle.danger)
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
                f"📊 **New Total:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})\n\n"
                f"*✨ This message will disappear in a few seconds.*"
            ),
            color=discord.Color.from_rgb(255, 69, 0),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

        # Disappear 7 seconds after claim
        target_msg = self.message or interaction.message
        asyncio.create_task(_schedule_message_deletion(target_msg, delay=7.0))

        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)


# --- Anonymous Confessions ---
class ConfessionModal(Modal, title="Submit Anonymous Confession"):
    confession = TextInput(
        label="Your Secret Confession",
        style=discord.TextStyle.paragraph,
        placeholder="Type your confession here... Please keep it respectful of server rules.",
        required=True,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = resolve_guild_context(interaction)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context could not be resolved.", ephemeral=True)

        confession_ch = discord.utils.get(guild.text_channels, name="🚦confession-🖇️") or discord.utils.get(
            guild.text_channels, name="confessions"
        )
        if not confession_ch:
            return await interaction.response.send_message("⚠️ Confession channel not found!", ephemeral=True)

        confession_id = await record_confession(interaction.user.id, self.confession.value)

        embed = discord.Embed(
            title=f"💌 Anonymous Confession #{confession_id}",
            description=self.confession.value,
            color=discord.Color.from_rgb(255, 105, 180),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text="Anonymous Submission • Chill-Verse Confessions")

        try:
            await confession_ch.send(embed=embed)
        except discord.HTTPException as e:
            return await interaction.response.send_message(f"⚠️ Failed to deliver confession: {e}", ephemeral=True)

        audit_ch = await get_or_create_audit_channel(guild)
        if audit_ch:
            log_embed = discord.Embed(
                title=f"🕵️ Confession #{confession_id} Trace Record",
                description=self.confession.value,
                color=discord.Color.dark_grey(),
                timestamp=discord.utils.utcnow(),
            )
            log_embed.add_field(name="Author", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
            try:
                await audit_ch.send(embed=log_embed)
            except discord.HTTPException:
                pass

        await interaction.response.send_message(f"✅ Your confession has been posted anonymously as **#{confession_id}**!", ephemeral=True)


class ConfessionPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🤫 Submit Confession", style=discord.ButtonStyle.secondary, custom_id="persistent_submit_confession", emoji="💌")
    async def submit_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionModal())


# --- Birthday Registration Panel & Modal ---
class BirthdayModal(Modal, title="Register Your Birthday"):
    birthday_input = TextInput(
        label="Date of Birth (DD/MM or DD/MM/YYYY)",
        placeholder="e.g. 24/09 or 24/09/2004",
        required=True,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        val = self.birthday_input.value.strip()
        dob_match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})", val)
        if not dob_match:
            return await interaction.response.send_message(
                "⚠️ Invalid format! Please enter your birthday in `DD/MM` or `DD/MM/YYYY` format (e.g. `14/06`).",
                ephemeral=True,
            )

        day = int(dob_match.group(1))
        month = int(dob_match.group(2))

        if day < 1 or day > 31 or month < 1 or month > 12:
            return await interaction.response.send_message("⚠️ That calendar date is invalid. Please enter a valid date.", ephemeral=True)

        day_str = str(day).zfill(2)
        month_str = str(month).zfill(2)
        formatted_bdate = f"{day_str}/{month_str}"

        bdays = await load_birthdays()
        bdays[str(interaction.user.id)] = formatted_bdate
        await save_birthdays(bdays)

        await interaction.response.send_message(
            f"🎂 **Birthday Registered!** Your birthday has been recorded as **{formatted_bdate}**.\n"
            f"Chill-Verse will send you a community celebration and pre-alert when your day arrives!",
            ephemeral=True,
        )


class BirthdayPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎂 Register / Update Birthday", style=discord.ButtonStyle.primary, custom_id="persistent_register_birthday", emoji="🎉")
    async def register_birthday_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BirthdayModal())


# --- Colours Selection ---
class ColourSelectionView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def select_color(self, interaction: discord.Interaction, role_name: str):
        if not interaction.guild:
            return await interaction.response.send_message("Action can only be executed in a server channel.", ephemeral=True)

        target_role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not target_role:
            return await interaction.response.send_message(f"⚠️ Role `{role_name}` not found. Run `.setup_roles` first.", ephemeral=True)

        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member:
            return await interaction.response.send_message("Could not resolve member identity.", ephemeral=True)

        roles_to_remove = [
            r for r in member.roles
            if r.name in COLOR_ROLES and r.name != role_name and r < interaction.guild.me.top_role
        ]

        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Colour role switch")

            if target_role in member.roles:
                await member.remove_roles(target_role, reason="Colour role removed")
                await interaction.response.send_message(f"⚪ Removed color **{target_role.name}**.", ephemeral=True)
            else:
                await member.add_roles(target_role, reason="Colour role assigned")
                await interaction.response.send_message(f"🎨 Selected color: **{target_role.name}** (No notifications attached)!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Permission denied modifying color roles.", ephemeral=True)

    @discord.ui.button(label="🔴 Red", style=discord.ButtonStyle.secondary, custom_id="pure_color_red", row=0)
    async def red(self, interaction: discord.Interaction, button: Button):
        await self.select_color(interaction, "Red")

    @discord.ui.button(label="🟡 Yellow", style=discord.ButtonStyle.secondary, custom_id="pure_color_yellow", row=0)
    async def yellow(self, interaction: discord.Interaction, button: Button):
        await self.select_color(interaction, "Yellow")

    @discord.ui.button(label="🟢 Green", style=discord.ButtonStyle.secondary, custom_id="pure_color_green", row=0)
    async def green(self, interaction: discord.Interaction, button: Button):
        await self.select_color(interaction, "Green")

    @discord.ui.button(label="🔵 Blue", style=discord.ButtonStyle.secondary, custom_id="pure_color_blue", row=1)
    async def blue(self, interaction: discord.Interaction, button: Button):
        await self.select_color(interaction, "Blue")

    @discord.ui.button(label="🟠 Orange", style=discord.ButtonStyle.secondary, custom_id="pure_color_orange", row=1)
    async def orange(self, interaction: discord.Interaction, button: Button):
        await self.select_color(interaction, "Orange")

    @discord.ui.button(label="🩷 Pink", style=discord.ButtonStyle.secondary, custom_id="pure_color_pink", row=1)
    async def pink(self, interaction: discord.Interaction, button: Button):
        await self.select_color(interaction, "Pink")

    @discord.ui.button(label="⚪ Remove Colour", style=discord.ButtonStyle.danger, custom_id="pure_color_clear", row=2)
    async def clear_color(self, interaction: discord.Interaction, button: Button):
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        current_colors = [r for r in member.roles if r.name in COLOR_ROLES and r < interaction.guild.me.top_role]
        if not current_colors:
            return await interaction.response.send_message("You don't currently have a colour role equipped.", ephemeral=True)
        await member.remove_roles(*current_colors, reason="Cleared colour roles")
        await interaction.response.send_message("⚪ All color roles have been removed.", ephemeral=True)


# --- Notification Preferences ---
class NotificationRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_ping(self, interaction: discord.Interaction, role_name: str):
        target_role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not target_role:
            return await interaction.response.send_message(f"⚠️ Role `{role_name}` not found.", ephemeral=True)

        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        try:
            if target_role in member.roles:
                await member.remove_roles(target_role, reason="Notification opt-out")
                await interaction.response.send_message(f"🔕 Removed: **{target_role.name}**", ephemeral=True)
            else:
                await member.add_roles(target_role, reason="Notification opt-in")
                await interaction.response.send_message(f"🔔 Added: **{target_role.name}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Permission denied modifying roles.", ephemeral=True)

    @discord.ui.button(label="⏰ Bump Pings", style=discord.ButtonStyle.primary, custom_id="ping_bump")
    async def bump_ping(self, interaction: discord.Interaction, button: Button):
        await self.toggle_ping(interaction, "Bump Pings")

    @discord.ui.button(label="📊 Poll Pings", style=discord.ButtonStyle.primary, custom_id="ping_polls")
    async def poll_ping(self, interaction: discord.Interaction, button: Button):
        await self.toggle_ping(interaction, "Poll Pings")

    @discord.ui.button(label="💬 Chat Revive", style=discord.ButtonStyle.primary, custom_id="ping_revive")
    async def revive_ping(self, interaction: discord.Interaction, button: Button):
        await self.toggle_ping(interaction, "Chat Revive")


# --- Verification & Tickets ---
class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(
        label="Why do you want to join?",
        style=discord.TextStyle.paragraph,
        placeholder="Tell us a bit about yourself...",
        required=True,
        max_length=500,
    )

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
        dob_match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})", dob_val)
        if dob_match:
            day, month = dob_match.group(1).zfill(2), dob_match.group(2).zfill(2)
            bdays = await load_birthdays()
            bdays[str(interaction.user.id)] = f"{day}/{month}"
            await save_birthdays(bdays)

        role = discord.utils.get(guild.roles, name="Member")
        if role and role < guild.me.top_role:
            try:
                await member.add_roles(role, reason="Completed Verification Modal")
            except discord.Forbidden:
                pass

        log_channel = await get_or_create_audit_channel(guild)
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
    experience = TextInput(
        label="Previous Experience",
        style=discord.TextStyle.paragraph,
        placeholder="List past moderation experience...",
        required=True,
        max_length=300,
    )
    reason = TextInput(
        label="Why do you want to join the Team?",
        style=discord.TextStyle.paragraph,
        placeholder="Tell us why we should choose you...",
        required=True,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = resolve_guild_context(interaction)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context not found.", ephemeral=True)

        team_channel = discord.utils.get(guild.text_channels, name="💬・team-chat") or discord.utils.get(
            guild.text_channels, name="team-news"
        )
        embed = discord.Embed(
            title="🚨 New Staff Application Submitted",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
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
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            ),
        }

        for rname in ["Supreme Leader", "Highness", "Authority"]:
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        try:
            ticket_ch = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {interaction.user.name}",
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(f"⚠️ Failed to create ticket channel: {e}", ephemeral=True)

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {interaction.user.mention}! Explain your issue below. High Command will assist you shortly.",
            color=discord.Color.blue(),
        )
        await ticket_ch.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created: {ticket_ch.mention}", ephemeral=True)

    @discord.ui.button(label="Apply for Team", style=discord.ButtonStyle.green, custom_id="persistent_apply_team", emoji="🛡️")
    async def apply_team(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TeamApplicationModal())


# ==============================================================================
# PANEL DEPLOYERS
# ==============================================================================
async def deploy_birthday_panel(guild: discord.Guild):
    bday_ch = discord.utils.get(guild.text_channels, name="birthdays")
    if not bday_ch:
        return

    try:
        async for msg in bday_ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Birthday Calendar & Registration" in (msg.embeds[0].title or ""):
                return
    except Exception:
        pass

    embed = discord.Embed(
        title="🎂 Chill-Verse Birthday Calendar & Registration",
        description=(
            "Never miss a community celebration!\n\n"
            "Click **Register / Update Birthday** below to submit your special day.\n\n"
            "• **Automated Wishes**: Chill-Verse will announce and celebrate with you when your birthday arrives!\n"
            "• **Advance Notice**: The server receives a reminder alert 24 hours prior!\n"
            "• **Upcoming List**: Type `.birthdays` anytime to view all upcoming server birthdays."
        ),
        color=discord.Color.gold(),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Chill-Verse Celebrations • Click Below to Register")

    try:
        await bday_ch.send(embed=embed, view=BirthdayPanelView())
    except discord.HTTPException as e:
        print(f"[Birthday Panel Deploy Error]: {e}")


async def deploy_confession_panel(guild: discord.Guild):
    confession_ch = discord.utils.get(guild.text_channels, name="🚦confession-🖇️") or discord.utils.get(
        guild.text_channels, name="confessions"
    )
    if not confession_ch:
        return

    try:
        async for msg in confession_ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Confession Box" in (msg.embeds[0].title or ""):
                return
    except Exception:
        pass

    embed = discord.Embed(
        title="💌 Chill-Verse Anonymous Confession Box",
        description=(
            "Have a secret, unsaid feeling, or funny confession?\n\n"
            "Click **Submit Confession** below to post your thought 100% anonymously into the channel!\n\n"
            "*Hate speech, spam, and severe rule breaches will be dealt with by server administrators.*"
        ),
        color=discord.Color.from_rgb(255, 105, 180),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Chill-Verse Anonymous Confessions • Click Below")
    try:
        await confession_ch.send(embed=embed, view=ConfessionPanelView())
    except discord.HTTPException as e:
        print(f"[Panel Deploy] Failed deploying confession box: {e}")


async def deploy_colours_panel(guild: discord.Guild):
    ch = discord.utils.get(guild.text_channels, name="🎨・colours") or discord.utils.get(guild.text_channels, name="colours")
    if not ch:
        return

    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Username Colours" in (msg.embeds[0].title or ""):
                return
    except Exception:
        pass

    embed = discord.Embed(
        title="🎨 Chill-Verse Username Colours",
        description=(
            "Pick a name color below to customize your chat appearance.\n\n"
            "• **Pure Cosmetic**: These roles do not receive pings, announcements, or notifications.\n"
            "• **Single Selection**: Choosing a new color automatically replaces your previous one.\n"
            "• Click **Remove Colour** anytime to return to the server default."
        ),
        color=discord.Color.magenta(),
    )
    embed.set_footer(text="Cosmetic Profile Styling • No Notifications Attached")
    try:
        await ch.send(embed=embed, view=ColourSelectionView())
    except discord.HTTPException as e:
        print(f"[Colour Deploy Error]: {e}")


async def deploy_notifications_panel(guild: discord.Guild, target_channel: Optional[discord.TextChannel] = None):
    ch = target_channel or discord.utils.get(guild.text_channels, name="📢・announcements")
    if not ch:
        return

    embed = discord.Embed(
        title="🔔 Community Notification Preferences",
        description="Opt-in to optional community pings by clicking below:",
        color=discord.Color.blurple(),
    )
    try:
        await ch.send(embed=embed, view=NotificationRolesView())
    except Exception:
        pass


async def deploy_team_rules_panel(guild: discord.Guild):
    team_rules_ch = discord.utils.get(guild.text_channels, name="🛡️・team-rules") or discord.utils.get(
        guild.text_channels, name="team-rules"
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
        description="Welcome to the internal staff directory. Adhere strictly to moderation escalation orders at all times.",
        color=discord.Color.dark_red(),
        timestamp=discord.utils.utcnow(),
    )
    rules_embed.add_field(
        name="1. Impartiality & Maturity",
        value=(
            "• Moderate objectively. Never let personal disputes dictate punishments.\n"
            "• Never use permissions or administrative authority in casual arguments.\n"
            "• Keep staff disagreements strictly behind closed doors in `💬・team-chat`."
        ),
        inline=False,
    )
    rules_embed.add_field(
        name="2. Confidentiality & Security",
        value=(
            "• Everything inside `Team <3` and `Admin Area 🔒` is strictly classified.\n"
            "• Never leak ticket discussions, audit logs, or member disciplinary history.\n"
            "• Do not invite external bots or modify permissions without High Command approval."
        ),
        inline=False,
    )
    rules_embed.add_field(
        name="3. Command Escalation Hierarchy",
        value=(
            "• **Supreme Leader / Highness**: Executive architecture & disaster restores.\n"
            "• **Authority**: Channel isolation, bulk cleanup, broadcasts & lockdowns.\n"
            "• **Moderators / Trial Mods**: Chat pacing, user warnings, timeouts, and tickets."
        ),
        inline=False,
    )

    if guild.icon:
        rules_embed.set_thumbnail(url=guild.icon.url)
    rules_embed.set_footer(text="Chill-Verse Staff Operations • Internal Document")

    try:
        await team_rules_ch.send(embed=rules_embed)
    except Exception:
        pass


async def deploy_team_news_commands_panel(guild: discord.Guild, prefix: str = "."):
    team_news_ch = discord.utils.get(guild.text_channels, name="team-news")
    if not team_news_ch:
        return

    try:
        async for msg in team_news_ch.history(limit=50):
            if msg.author == guild.me and msg.embeds and "TEAM & AUTHORITY ACTIVE BOT COMMANDS" in (msg.embeds[0].title or ""):
                await msg.delete()
                await asyncio.sleep(0.3)
    except Exception:
        pass

    commands_embed = discord.Embed(
        title="💼 TEAM & AUTHORITY ACTIVE BOT COMMANDS",
        description="Reference manual for bot commands accessible to Authority, Moderators, and Team members:",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow(),
    )

    commands_embed.add_field(
        name="🧹 Moderation & Purge Suite (Authority)",
        value=(
            f"`{prefix}purge <1-1000> [target]` — Bulk delete messages with user/bot/link filters (Supreme Leader, Highness & Authority).\n"
            f"`{prefix}remove_bot_role <@role/@bot/all>` — Immediately cuts bot access from a room."
        ),
        inline=False,
    )

    commands_embed.add_field(
        name="🔒 Channel Security & Overrides (Authority)",
        value=(
            f"`{prefix}lock` / `{prefix}unlock` — Mutes or opens the current room for members.\n"
            f"`{prefix}hide` / `{prefix}show` — Toggles channel visibility from standard members.\n"
            f"`{prefix}permit <@user/@role>` — Whitelists a member or role into the channel.\n"
            f"`{prefix}revoke <@user/@role>` — Evicts a member or role from the channel."
        ),
        inline=False,
    )

    commands_embed.add_field(
        name="⭐ XP Management & Spawners (Authority)",
        value=(
            f"`{prefix}addxp <@user> <amount>` — Grants XP and automatically recalculates rank roles.\n"
            f"`{prefix}removexp <@user> <amount>` — Deducts XP and updates tier roles accordingly.\n"
            f"`{prefix}setxp <@user> <amount>` — Sets exact XP and syncs corresponding rank roles.\n"
            f"`{prefix}superdrop [amount] [#ch]` — Spawns a massive Super XP drop.\n"
            f"`{prefix}xpdrop [amount] [#ch]` — Spawns a standard wild XP drop."
        ),
        inline=False,
    )

    commands_embed.add_field(
        name="📢 Announcements & Community Pacing (Staff & Team)",
        value=(
            f"`{prefix}announce [optional #channel] <title> | <text> [--everyone/--here]` — Posts official announcement embeds.\n"
            f"`{prefix}revive [optional topic]` — Pings the Chat Revive role with an icebreaker prompt.\n"
            f"`{prefix}afk [reason]` — Sets an AFK status while moderating."
        ),
        inline=False,
    )

    commands_embed.set_footer(text=f"Prefix: {prefix} • Strictly restricted to Authority and Staff ranks")

    try:
        await team_news_ch.send(embed=commands_embed)
    except Exception as e:
        print(f"[Team News Deploy Error]: {e}")


async def deploy_bot_commands_panel(guild: discord.Guild, prefix: str = "."):
    """Deploys a complete, categorized breakdown of EVERY single bot command."""
    cmd_channel = discord.utils.get(guild.text_channels, name="💼・bot-commands") or discord.utils.get(
        guild.text_channels, name="bot-commands"
    )

    if not cmd_channel:
        return

    try:
        async for msg in cmd_channel.history(limit=50):
            if msg.author == guild.me:
                await msg.delete()
                await asyncio.sleep(0.3)
    except (discord.Forbidden, discord.HTTPException):
        pass

    header_embed = discord.Embed(
        title="🤖 CHILL-VERSE BOT MASTER COMMAND DIRECTORY",
        description=(
            "Welcome to the official, complete command index for **Arkbot**.\n"
            "Below is the comprehensive list of all member, staff, moderation, and system commands.\n\n"
            f"📌 **Default Prefix:** `{prefix}` *(Example: `{prefix}ping`)*"
        ),
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    if guild.icon:
        header_embed.set_thumbnail(url=guild.icon.url)

    member_embed = discord.Embed(
        title="👥 1. General & Member Commands",
        description="Commands accessible to all verified community members:",
        color=discord.Color.green(),
    )
    member_embed.add_field(name=f"`{prefix}ping`", value="Checks the bot websocket heartbeat and gateway latency.", inline=False)
    member_embed.add_field(name=f"`{prefix}bump`", value="Bumps Chill-Verse in `⏰・bump` for **+250 XP** (2-hour server cooldown).", inline=False)
    member_embed.add_field(name=f"`{prefix}revive` / `{prefix}chatrevive [topic]`", value="Pings **@Chat Revive** with a random icebreaker or custom topic.", inline=False)
    member_embed.add_field(name=f"`{prefix}xp` / `{prefix}rank` / `{prefix}level [@user]`", value="Inspects your own or another member's level, rank, and XP progress.", inline=False)
    member_embed.add_field(name=f"`{prefix}birthdays` / `{prefix}upcoming_birthdays`", value="Displays upcoming community birthdays and active celebrations.", inline=False)
    member_embed.add_field(name=f"`{prefix}afk [reason]`", value="Sets an AFK status. Notifies anyone who pings you and greets you upon return.", inline=False)

    mod_embed = discord.Embed(
        title="🛡️ 2. Authority, Moderation & Access Control",
        description="Reserved for **Authority**, **Highness**, and **Supreme Leader**:",
        color=discord.Color.orange(),
    )
    mod_embed.add_field(name=f"`{prefix}purge <1-1000> [target]`", value="Bulk deletes messages with support for filters (`@user`, `bot`, `links`).", inline=False)
    mod_embed.add_field(name=f"`{prefix}lock [optional #channel]`", value="Locks the channel, preventing regular members from sending messages.", inline=False)
    mod_embed.add_field(name=f"`{prefix}unlock [optional #channel]`", value="Unlocks the channel, restoring normal chatting permissions.", inline=False)
    mod_embed.add_field(name=f"`{prefix}hide [optional #channel]`", value="Hides the channel visibility completely from standard members.", inline=False)
    mod_embed.add_field(name=f"`{prefix}show [optional #channel]`", value="Makes a hidden channel visible to standard members again.", inline=False)
    mod_embed.add_field(name=f"`{prefix}permit <@user / @role>`", value="Explicitly whitelists a user or role to view and speak in the current channel.", inline=False)
    mod_embed.add_field(name=f"`{prefix}revoke <@user / @role>`", value="Removes explicit channel overrides for the target user or role.", inline=False)
    mod_embed.add_field(name=f"`{prefix}remove_bot_role <@role / @bot / all>`", value="Immediately strips room access for external bots.", inline=False)
    mod_embed.add_field(name=f"`{prefix}announce [#channel] <title> | <text> [--everyone/--here]`", value="Dispatches a formatted official announcement embed.", inline=False)

    xp_embed = discord.Embed(
        title="⭐ 3. XP Engine & Manual Spawners",
        description="Tools to grant, modify, and manually spawn interactive XP drops:",
        color=discord.Color.gold(),
    )
    xp_embed.add_field(name=f"`{prefix}addxp <@user> <amount>`", value="Grants XP to a member and automatically upgrades rank tier roles.", inline=False)
    xp_embed.add_field(name=f"`{prefix}removexp <@user> <amount>`", value="Deducts XP from a member and demotes rank tier roles if needed.", inline=False)
    xp_embed.add_field(name=f"`{prefix}setxp <@user> <amount>`", value="Directly sets a member's XP to an exact number and recalculates rank tiers.", inline=False)
    xp_embed.add_field(name=f"`{prefix}superdrop [amount] [#ch]`", value="**Manually spawns a Super XP Drop** (defaults to 1,000–5,000 XP).", inline=False)
    xp_embed.add_field(name=f"`{prefix}xpdrop [amount] [#ch]`", value="**Manually spawns a Standard XP Drop** (defaults to 50–150 XP).", inline=False)

    admin_embed = discord.Embed(
        title="⚙️ 4. Administration, Panels & Disaster Recovery",
        description="System recovery suite restricted to **Supreme Leader** & **Highness**:",
        color=discord.Color.red(),
    )
    admin_embed.add_field(name=f"`{prefix}setup_channels`", value="Non-destructively provisions missing blueprint channels & categories.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_roles`", value="Provisions missing staff, ping, cosmetic, and tier level roles.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_birthdays`", value="Deploys the interactive Birthday Registration panel in `birthdays`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_tickets`", value="Deploys the persistent Support & Staff Application panel in `🎫・tickets`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}colours`", value="Deploys the cosmetic color selection panel in `🎨・colours`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_confession_panel`", value="Deploys the anonymous confession box in `🚦confession-🖇️`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_notifications`", value="Deploys optional community notification role buttons.", inline=False)
    admin_embed.add_field(name=f"`{prefix}refresh_rules`", value="Refreshes guidelines in `#🛡️・team-rules` and command list in `#team-news`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}refresh_commands`", value="Refreshes this complete master manual in `#💼・bot-commands`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}backup_all`", value="Generates and overwrites the single unified master backup snapshot.", inline=False)
    admin_embed.add_field(name=f"`{prefix}restore_all`", value="Restores channels, permissions, XP, birthdays, and confessions.", inline=False)
    admin_embed.add_field(name=f"`{prefix}maintenance [on/off/status]`", value="Locks or unlocks non-administrative commands for maintenance.", inline=False)
    admin_embed.add_field(name=f"`{prefix}shutdown [reason]`", value="Flushes state, saves master backup, and terminates cleanly.", inline=False)

    try:
        await cmd_channel.send(embed=header_embed)
        await cmd_channel.send(embed=member_embed)
        await cmd_channel.send(embed=mod_embed)
        await cmd_channel.send(embed=xp_embed)
        await cmd_channel.send(embed=admin_embed)
    except Exception as e:
        print(f"[Bot Commands Deploy Error]: {e}")


async def deploy_tickets_panel(guild: discord.Guild):
    ch = discord.utils.get(guild.text_channels, name="🎫・tickets")
    if not ch:
        return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Support & Staff Applications" in (msg.embeds[0].title or ""):
                return
    except Exception:
        pass

    embed = discord.Embed(
        title="🎫 Chill-Verse Support & Staff Applications",
        description="Need staff assistance, want to report an issue, or apply for Team?\n\nChoose an option below:",
        color=discord.Color.blue(),
    )
    try:
        await ch.send(embed=embed, view=TicketView())
    except Exception:
        pass


# ==============================================================================
# SUBCLASSED BOT ENGINE
# ==============================================================================
class ArkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=".",
            intents=intents,
            strip_after_prefix=True,
        )
        self.remove_command("help")
        self.first_run_completed: bool = False
        self.restore_complete = asyncio.Event()

    async def setup_hook(self):
        await restore_runtime_state()
        await init_xp_cache()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.close()))
            except (NotImplementedError, RuntimeError):
                pass

        # Register Persistent Views
        self.add_view(RulesView())
        self.add_view(TicketView())
        self.add_view(CloseTicketView())
        self.add_view(ColourSelectionView())
        self.add_view(NotificationRolesView())
        self.add_view(ConfessionPanelView())
        self.add_view(BirthdayPanelView())

        asyncio.create_task(self._auto_restore_all_guilds())

        if not hourly_backup_task.is_running():
            hourly_backup_task.start()
        if not birthday_announcer_task.is_running():
            birthday_announcer_task.start()
        if not xp_drop_task.is_running():
            xp_drop_task.start()
        if not xp_flush_task.is_running():
            xp_flush_task.start()

    async def _auto_restore_all_guilds(self):
        """Restores first from the single master backup, then immediately overwrites it with a fresh snapshot."""
        await self.wait_until_ready()
        global BUMP_TIMER_TASK

        try:
            for guild in self.guilds:
                backup_file = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
                boot_backup = await safe_read_json(backup_file, None)

                # If local master file doesn't exist, search Discord for latest
                if not boot_backup or not boot_backup.get("categories"):
                    remote_backup = await find_latest_backup_from_discord(guild)
                    if remote_backup:
                        boot_backup = remote_backup

                # Step 1: Restore first if backup exists
                if boot_backup:
                    stats = await apply_unified_restore(guild, boot_backup)
                    print(
                        f"[Auto-Boot] Restored {stats['channels_created']} channels, "
                        f"{stats['xp_users']} XP profiles, {stats['birthdays']} birthdays, "
                        f"{stats['confessions']} confessions in {guild.name}."
                    )
                else:
                    for uid_str, xp_val in XP_CACHE.items():
                        member = guild.get_member(int(uid_str))
                        if member:
                            await sync_member_level_roles(member, xp_val)

                # Step 2: Overwrite existing backup with fresh snapshot
                fresh_payload = await generate_unified_backup_payload(guild)
                await safe_write_json(backup_file, fresh_payload)

                err_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
                    guild.text_channels, name="bot-errors"
                )
                if err_channel:
                    await purge_all_old_backups(err_channel)
                    file_stream = io.BytesIO(json.dumps(fresh_payload, indent=4).encode("utf-8"))
                    backup_file_attachment = discord.File(file_stream, filename=f"master_backup_{guild.id}.json")
                    await err_channel.send(
                        content="🔒 **Master Single Backup Snapshot (Overwritten on Boot)**",
                        file=backup_file_attachment,
                    )

                await enforce_admin_area_security(guild)
        except Exception as e:
            print(f"[Auto-Boot Critical Error]: {e}")
            traceback.print_exc()
        finally:
            self.restore_complete.set()

        if LAST_BUMP_TIME:
            elapsed = (datetime.datetime.now(datetime.timezone.utc) - LAST_BUMP_TIME).total_seconds()
            if elapsed < BUMP_COOLDOWN_SECONDS and self.guilds:
                target_g = self.guilds[0]
                target_ch = discord.utils.get(target_g.text_channels, name="⏰・bump")
                if target_ch:
                    BUMP_TIMER_TASK = asyncio.create_task(
                        schedule_bump_timers(target_g, target_ch, initial_delay=int(elapsed))
                    )

    async def close(self):
        print("[Shutdown Engine] Flushing state and XP cache to disk...")
        await flush_xp_cache()
        await persist_runtime_state()
        await super().close()


bot = ArkBot()

# ==============================================================================
# AUDIT LOGGING & EVENTS
# ==============================================================================
@bot.check
async def check_maintenance_mode(ctx: commands.Context):
    if not MAINTENANCE_MODE:
        return True

    if ctx.command and ctx.command.name in ["maintenance", "shutdown"]:
        return True

    is_owner = ctx.guild and ctx.author.id == ctx.guild.owner_id
    is_admin = getattr(getattr(ctx.author, "guild_permissions", None), "administrator", False)
    staff_roles = {"supreme leader", "highness", "authority"}
    user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
    is_high_command = bool(staff_roles.intersection(user_roles))

    if is_owner or is_admin or is_high_command:
        return True

    await ctx.send("🛠️ **Maintenance Mode Active:** Non-administrative commands are temporarily disabled.", delete_after=6)
    return False


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse operational.")
    global UPDATE_NOTIFIED

    await bot.restore_complete.wait()

    if bot.first_run_completed:
        return
    bot.first_run_completed = True

    for guild in bot.guilds:
        test_ch = await get_or_create_testing_channel(guild)
        await get_or_create_audit_channel(guild)

        created_channels = 0
        existing_cats = {normalize_name(cat.name): cat for cat in guild.categories}
        for cat_data in SERVER_BLUEPRINT:
            raw_cat_name = cat_data["category"]
            norm_cat = normalize_name(raw_cat_name)
            if norm_cat in existing_cats:
                category = existing_cats[norm_cat]
            else:
                category = await guild.create_category(name=raw_cat_name)
                existing_cats[norm_cat] = category

            existing_chs = {normalize_name(ch.name): ch for ch in category.channels}
            for ch_info in cat_data["channels"]:
                ch_name = ch_info["name"]
                if normalize_name(ch_name) in existing_chs:
                    continue

                ch_type = ch_info["type"]
                if ch_type == "voice":
                    await guild.create_voice_channel(name=ch_name, category=category, user_limit=ch_info.get("user_limit", 0))
                elif ch_type == "forum":
                    try:
                        await guild.create_forum_channel(name=ch_name, category=category)
                    except Exception:
                        await guild.create_text_channel(name=ch_name, category=category)
                else:
                    await guild.create_text_channel(name=ch_name, category=category)
                created_channels += 1

        created_roles = 0
        existing_roles = {r.name.lower().strip() for r in guild.roles}
        roles_to_deploy = [
            ("Supreme Leader", discord.Color.dark_red(), True, True),
            ("Highness", discord.Color.gold(), True, True),
            ("Authority", discord.Color.orange(), True, True),
            ("Head Moderator", discord.Color.red(), True, True),
            ("Moderator", discord.Color.yellow(), True, True),
            ("Trial Mod", discord.Color.blue(), True, True),
            ("Chill-Verse Team", discord.Color(0x313338), True, False),
            ("Chat Revive", discord.Color.from_rgb(26, 188, 156), False, True),
            ("Member", discord.Color.default(), False, False),
            ("Bump Pings", discord.Color.purple(), False, True),
            ("Poll Pings", discord.Color.default(), False, True),
            ("Red", discord.Color.from_rgb(255, 0, 0), False, False),
            ("Yellow", discord.Color.from_rgb(255, 255, 0), False, False),
            ("Green", discord.Color.from_rgb(0, 128, 0), False, False),
            ("Blue", discord.Color.from_rgb(0, 0, 255), False, False),
            ("Orange", discord.Color.from_rgb(255, 165, 0), False, False),
            ("Pink", discord.Color.from_rgb(255, 105, 180), False, False),
        ]
        for r_name, r_color, r_hoist, r_mentionable in roles_to_deploy:
            if r_name.lower().strip() not in existing_roles:
                try:
                    await guild.create_role(
                        name=r_name,
                        color=r_color,
                        hoist=r_hoist,
                        mentionable=r_mentionable,
                        reason="Startup Role Provisioning",
                    )
                    created_roles += 1
                except Exception:
                    pass

        await enforce_admin_area_security(guild)
        await deploy_team_rules_panel(guild)
        await deploy_team_news_commands_panel(guild, bot.command_prefix)
        await deploy_bot_commands_panel(guild, bot.command_prefix)
        await deploy_tickets_panel(guild)
        await deploy_colours_panel(guild)
        await deploy_confession_panel(guild)
        await deploy_birthday_panel(guild)

        if test_ch:
            embed = discord.Embed(
                title="🧪 Arkbot Startup Diagnostic Report",
                description="Startup synchronization complete across all operational nodes.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="Gateway Latency", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
            embed.add_field(name="Channels Provisioned", value=f"`+{created_channels} created`", inline=True)
            embed.add_field(name="Roles Provisioned", value=f"`+{created_roles} created`", inline=True)
            embed.add_field(name="XP Profiles", value=f"`{len(XP_CACHE)} loaded`", inline=True)
            await test_ch.send(embed=embed)

    if not UPDATE_NOTIFIED:
        for guild in bot.guilds:
            team_news_ch = discord.utils.get(guild.text_channels, name="team-news")
            if team_news_ch:
                embed = discord.Embed(
                    title="🚀 Arkbot Operational — Full Engine Online!",
                    description="Leveling, master auto-backups, bump trackers, birthday reminders, and moderation engines online.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
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
            timestamp=discord.utils.utcnow(),
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
        b_content = before.content.strip() or "*Empty*"
        a_content = after.content.strip() or "*Empty*"
        if len(b_content) > 1000:
            b_content = b_content[:1000] + "... [truncated]"
        if len(a_content) > 1000:
            a_content = a_content[:1000] + "... [truncated]"

        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
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
        embed = discord.Embed(
            title="🚪 Member Left Server",
            color=discord.Color.dark_grey(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        try:
            await log_ch.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            pass


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CheckFailure):
        err_msg = str(error).strip()
        if err_msg:
            await ctx.send(err_msg, delete_after=6)
        return

    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"⚠️ **Missing argument:** `{error.param.name}`. Run command properly.", delete_after=6)
    if isinstance(error, commands.BadArgument):
        return await ctx.send(f"⚠️ **Invalid argument:** {error}", delete_after=6)

    orig_error = getattr(error, "original", error)
    tb_text = "".join(traceback.format_exception(type(orig_error), orig_error, orig_error.__traceback__))
    if len(tb_text) > 1000:
        tb_text = tb_text[-1000:]

    await ctx.send(f"⚠️ **Command Error:** `{orig_error}`", delete_after=8)

    if ctx.guild:
        err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
            ctx.guild.text_channels, name="bot-errors"
        )
        if err_channel:
            err_embed = discord.Embed(
                title="🚨 Command Runtime Error",
                description="An unhandled exception occurred during command execution.",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow(),
            )
            err_embed.add_field(name="Command", value=f"`{ctx.command}`" if ctx.command else "`Unknown`", inline=True)
            err_embed.add_field(name="Invoker", value=f"{ctx.author} (`{ctx.author.id}`)", inline=True)
            err_embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
            err_embed.add_field(name="Exception", value=f"```py\n{type(orig_error).__name__}: {orig_error}\n```", inline=False)
            err_embed.add_field(name="Traceback", value=f"```py\n{tb_text}\n```", inline=False)

            try:
                await err_channel.send(embed=err_embed)
            except discord.HTTPException:
                pass


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
        color=discord.Color.purple(),
    )
    sent_dm = False
    try:
        await member.send(embed=embed, view=RulesView())
        sent_dm = True
    except discord.Forbidden:
        pass

    channel = discord.utils.get(member.guild.text_channels, name="👋・welcome")
    if channel:
        msg = (
            f"{member.mention} Welcome! Please check your DMs to complete verification."
            if sent_dm
            else f"{member.mention} (Please enable DMs or click Accept below to verify!)"
        )
        await channel.send(content=msg, embed=embed, view=RulesView())


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    ctx = await bot.get_context(message)

    # 1. AFK Return Greeting
    if message.author.id in AFK_USERS and ctx.command and ctx.command.name == "afk":
        pass
    elif message.author.id in AFK_USERS:
        del AFK_USERS[message.author.id]
        await persist_runtime_state()
        welcome_template = random.choice(AFK_WELCOME_MESSAGES)
        welcome_embed = discord.Embed(
            description=welcome_template.format(user=message.author.mention),
            color=discord.Color.green(),
        )
        await message.channel.send(embed=welcome_embed, delete_after=10)

    # 2. AFK Mention Interceptor
    if message.mentions:
        for mentioned in message.mentions:
            if mentioned.id in AFK_USERS and mentioned.id != message.author.id:
                afk_info = AFK_USERS[mentioned.id]
                afk_embed = discord.Embed(
                    description=f"💤 **{mentioned.display_name} is currently AFK:**\n*{afk_info['reason']}*",
                    color=discord.Color.dark_purple(),
                )
                await message.channel.send(embed=afk_embed, delete_after=10)

    # 3. AutoMod (Links & Anti-Spam)
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
            queue.clear()
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return await message.channel.send(
                f"⚠️ {message.author.mention}, please slow down! Sending messages too quickly.",
                delete_after=4,
            )

    # 4. Standard Chat XP Gain
    if message.guild and not ctx.valid:
        now_ts = discord.utils.utcnow().timestamp()
        last_xp = USER_CHAT_XP_COOLDOWN.get(message.author.id, 0.0)
        if now_ts - last_xp >= 60.0:
            USER_CHAT_XP_COOLDOWN[message.author.id] = now_ts
            gained = random.randint(15, 25)
            prev_xp, new_xp = await add_user_xp(message.author.id, gained)
            await handle_level_up(message.author, prev_xp, new_xp, message.channel)

        # 5. Super Drop Trigger (Strictly locked to Chill Area channels)
        is_chill_area = (
            isinstance(message.channel, discord.TextChannel)
            and message.channel.category
            and "chill area" in message.channel.category.name.lower()
            and message.channel.name not in SYSTEM_CHANNELS
        )

        if is_chill_area:
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
                            f"The Chill Area is blazing hot with active members! A **SUPER DROP** has spawned!\n\n"
                            f"🎁 **Reward Range:** `1,000 - 5,000 XP`\n"
                            f"💎 **This Drop:** `+{super_xp:,} XP`\n\n"
                            f"**Click below immediately to claim it!** *(Disappears in 3 minutes)*"
                        ),
                        color=discord.Color.from_rgb(255, 69, 0),
                        timestamp=discord.utils.utcnow(),
                    )
                    super_embed.set_footer(text="Triggered in Chill Area • Chill-Verse")

                    view = SuperXPDropView(xp_amount=super_xp)
                    try:
                        sent_drop = await message.channel.send(embed=super_embed, view=view)
                        view.message = sent_drop
                    except discord.HTTPException:
                        pass

    await bot.process_commands(message)


# ==============================================================================
# AUTOMATED TASKS
# ==============================================================================
@tasks.loop(seconds=60.0)
async def xp_flush_task():
    await flush_xp_cache()


@tasks.loop(hours=2.0)
async def xp_drop_task():
    await bot.wait_until_ready()
    if MAINTENANCE_MODE:
        return

    for guild in bot.guilds:
        chill_cat = discord.utils.find(lambda c: "chill area" in c.name.lower(), guild.categories)
        if not chill_cat:
            continue

        eligible_channels: List[discord.TextChannel] = []
        for ch in chill_cat.text_channels:
            if ch.name in SYSTEM_CHANNELS:
                continue

            member_perms = ch.permissions_for(guild.default_role)
            if not member_perms.view_channel:
                continue

            bot_perms = ch.permissions_for(guild.me)
            if bot_perms.view_channel and bot_perms.send_messages and bot_perms.embed_links:
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
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text="Chill Area Community Drop (Every 2 Hours) • Chill-Verse")

        view = ClaimXPDropView(xp_amount=drop_xp)
        try:
            sent_msg = await target_channel.send(embed=embed, view=view)
            view.message = sent_msg
        except discord.HTTPException:
            pass


@tasks.loop(hours=1.0)
async def hourly_backup_task():
    """Overwrites the single master backup hourly locally and purges old Discord copies."""
    await bot.wait_until_ready()
    for guild in bot.guilds:
        backup_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
            guild.text_channels, name="bot-errors"
        )
        if not backup_channel:
            continue

        payload = await generate_unified_backup_payload(guild)
        backup_file_path = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
        await safe_write_json(backup_file_path, payload)

        await purge_all_old_backups(backup_channel)
        file = discord.File(io.BytesIO(json.dumps(payload, indent=4).encode("utf-8")), filename=f"master_backup_{guild.id}.json")
        try:
            await backup_channel.send(
                content="🔒 **Master Hourly Single Snapshot (Auto-Overwritten)**",
                file=file,
            )
        except Exception:
            pass


@tasks.loop(hours=1.0)
async def birthday_announcer_task():
    """Checks for today's birthdays and announces advance reminders for tomorrow."""
    await bot.wait_until_ready()
    global ANNOUNCED_BIRTHDAYS_TODAY, REMINDED_BIRTHDAYS_TOMORROW

    now = datetime.datetime.now(datetime.timezone.utc)
    today_str = now.strftime("%d/%m")
    tomorrow = now + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d/%m")

    # Reset day tracking at midnight
    if now.hour == 0:
        if ANNOUNCED_BIRTHDAYS_TODAY:
            ANNOUNCED_BIRTHDAYS_TODAY.clear()
        if REMINDED_BIRTHDAYS_TOMORROW:
            REMINDED_BIRTHDAYS_TOMORROW.clear()
        await persist_runtime_state()

    birthdays = await load_birthdays()

    for guild in bot.guilds:
        bday_ch = discord.utils.get(guild.text_channels, name="birthdays")
        if not bday_ch:
            continue

        for uid_str, bdate in birthdays.items():
            uid = int(uid_str)
            member = guild.get_member(uid)
            if not member:
                continue

            # 1. Celebrate Today's Birthday
            if bdate == today_str and uid not in ANNOUNCED_BIRTHDAYS_TODAY:
                embed = discord.Embed(
                    title="🎂 HAPPY BIRTHDAY! 🎉",
                    description=(
                        f"Today is a very special day! Happy Birthday {member.mention}!\n\n"
                        f"Wishing you happiness, good health, and an amazing year ahead from all of us at **Chill-Verse**! 💖"
                    ),
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="Chill-Verse Daily Birthday Celebration")
                try:
                    await bday_ch.send(content=f"🎉 Wish {member.mention} a Happy Birthday today! 🥳", embed=embed)
                    ANNOUNCED_BIRTHDAYS_TODAY.append(uid)
                    await persist_runtime_state()
                except Exception:
                    pass

            # 2. 24-Hour Advance Birthday Reminder Alert
            elif bdate == tomorrow_str and uid not in REMINDED_BIRTHDAYS_TOMORROW and now.hour >= 12:
                reminder_embed = discord.Embed(
                    title="⏰ UPCOMING BIRTHDAY ALERT! 🎂",
                    description=(
                        f"Heads up everyone! Tomorrow is **{member.mention}**'s birthday (`{tomorrow_str}`)!\n\n"
                        f"Get your wishes ready to celebrate with them tomorrow! 🎈"
                    ),
                    color=discord.Color.from_rgb(255, 182, 193),
                    timestamp=discord.utils.utcnow(),
                )
                reminder_embed.set_thumbnail(url=member.display_avatar.url)
                reminder_embed.set_footer(text="Chill-Verse 24-Hour Birthday Alert")
                try:
                    await bday_ch.send(embed=reminder_embed)
                    REMINDED_BIRTHDAYS_TOMORROW.append(uid)
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

    bump_channel = discord.utils.get(guild.text_channels, name="⏰・bump") or discord.utils.get(
        guild.text_channels, name="bump"
    )

    if bump_channel and ctx.channel.id != bump_channel.id:
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass
        return await ctx.send(
            f"⚠️ {ctx.author.mention}, the `.bump` command can only be used in {bump_channel.mention}!",
            delete_after=6,
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
                color=discord.Color.red(),
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
        timestamp=now,
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Dual Reminder Armed: 15m prior alert & final ready ping")
    await ctx.send(embed=embed)

    await handle_level_up(ctx.author, prev_xp, new_total_xp, ctx.channel)

    if BUMP_TIMER_TASK and not BUMP_TIMER_TASK.done():
        BUMP_TIMER_TASK.cancel()

    target_channel = bump_channel or ctx.channel
    BUMP_TIMER_TASK = asyncio.create_task(schedule_bump_timers(ctx.guild, target_channel))


@bot.command(name="revive", aliases=["chatrevive"])
@commands.guild_only()
async def chat_revive(ctx: commands.Context, *, topic: Optional[str] = None):
    guild_id = ctx.guild.id
    now = discord.utils.utcnow().timestamp()
    last_revive = LAST_REVIVE_TIME.get(guild_id, 0.0)

    if now - last_revive < REVIVE_COOLDOWN_SECONDS:
        remaining = int(REVIVE_COOLDOWN_SECONDS - (now - last_revive))
        mins = remaining // 60
        secs = remaining % 60
        return await ctx.send(
            f"⏳ **Chat Revive Cooldown:** You can ping the chat again in **{mins}m {secs}s**!",
            delete_after=6,
        )

    revive_role = discord.utils.get(ctx.guild.roles, name="Chat Revive")
    mention_target = revive_role.mention if revive_role else "@here"

    chosen_topic = topic.strip() if topic else random.choice(REVIVE_ICEBREAKERS)
    LAST_REVIVE_TIME[guild_id] = now

    embed = discord.Embed(
        title="⚡ CHAT REVIVE SUMMONS! ⚡",
        description=(
            f"**{ctx.author.mention} wants to wake up the chat!**\n\n"
            f"🗣️ **Topic / Question:**\n> *\"{chosen_topic}\"*\n\n"
            f"Come join the conversation and earn some active XP!"
        ),
        color=discord.Color.from_rgb(26, 188, 156),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text=f"Initiated by {ctx.author.display_name} • Chill-Verse")
    if ctx.author.display_avatar:
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(
        content=mention_target,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True, everyone=True),
    )

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass


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
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Current Level", value=f"**Level {lvl}**", inline=True)
    embed.add_field(name="Total XP", value=f"**{user_xp:,} XP**", inline=True)
    embed.add_field(name="Current Rank Tier", value=f"🛡️ **{current_tier}**", inline=False)
    embed.add_field(
        name="Next Level At",
        value=f"**{nxt_lvl_xp:,} XP** (*{needed:,} XP remaining*)",
        inline=False,
    )

    await ctx.send(embed=embed)


# --- Birthday Reminder & Schedule Command ---
@bot.command(name="birthdays", aliases=["upcoming_birthdays", "upcoming_bdays", "bdayremind"])
async def upcoming_birthdays_cmd(ctx: commands.Context):
    """Displays registered community birthdays and upcoming dates."""
    bdays = await load_birthdays()
    if not bdays:
        return await ctx.send("🎂 No birthdays are currently registered. Click the button in `#birthdays` to add yours!", delete_after=6)

    now = datetime.datetime.now(datetime.timezone.utc)
    today_date = datetime.date(now.year, now.month, now.day)

    upcoming_list = []
    for uid_str, bdate in bdays.items():
        try:
            d, m = map(int, bdate.split("/"))
            member = ctx.guild.get_member(int(uid_str))
            if not member:
                continue

            bday_this_year = datetime.date(now.year, m, d)
            if bday_this_year < today_date:
                bday_next = datetime.date(now.year + 1, m, d)
            else:
                bday_next = bday_this_year

            days_left = (bday_next - today_date).days
            upcoming_list.append((days_left, member, bdate))
        except Exception:
            continue

    upcoming_list.sort(key=lambda x: x[0])
    top_upcoming = upcoming_list[:12]

    if not top_upcoming:
        return await ctx.send("🎂 No upcoming birthdays found among current server members.", delete_after=6)

    embed = discord.Embed(
        title="🎂 Upcoming Chill-Verse Birthdays",
        description="Here are the upcoming member birthdays recorded in the sanctuary:",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow(),
    )

    lines = []
    for days_left, member, bdate in top_upcoming:
        if days_left == 0:
            status = "🎉 **TODAY!**"
        elif days_left == 1:
            status = "⏳ **Tomorrow!**"
        else:
            status = f"in **{days_left} days**"
        lines.append(f"• {member.mention} — `{bdate}` ({status})")

    embed.description = "\n".join(lines)
    embed.set_footer(text="Register or update your date anytime in #birthdays!")
    await ctx.send(embed=embed)


# --- Manual XP Suite (Add, Remove, Set) ---
@bot.command(name="addxp", aliases=["givexp", "add-xp"])
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
            f"🎖️ **Level:** `Level {new_lvl}` "
            + (f"*(Ranked up from Level {old_lvl}!)*" if new_lvl > old_lvl else "")
            + "\n"
            f"🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command(name="removexp", aliases=["takexp", "delxp", "remove-xp"])
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
            f"🎖️ **Level:** `Level {new_lvl}` "
            + (f"*(Demoted from Level {old_lvl})*" if new_lvl < old_lvl else "")
            + "\n"
            f"🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}"
        ),
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command(name="setxp", aliases=["set-xp"])
@is_authority_holder()
async def setxp(ctx: commands.Context, member: discord.Member, amount: int):
    if amount < 0:
        return await ctx.send("⚠️ XP cannot be a negative value.", delete_after=5)

    prev_xp, new_xp = await set_user_xp(member.id, amount)
    old_lvl = calculate_level(prev_xp)
    new_lvl = calculate_level(new_xp)

    current_tier_role = await sync_member_level_roles(member, new_xp)

    embed = discord.Embed(
        title="⚙️ XP Manually Overridden",
        description=(
            f"Successfully updated total XP for {member.mention}.\n\n"
            f"📊 **Previous:** `{prev_xp:,} XP` (Level {old_lvl})\n"
            f"📊 **New Total:** `{new_xp:,} XP` (Level {new_lvl})\n"
            f"🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}"
        ),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    await ctx.send(embed=embed)


# --- Manual Drop Spawners (Super Drop & Regular Drop) ---
@bot.command(name="superdrop", aliases=["spawndrop", "dropsuper"])
@is_authority_holder()
async def manual_super_drop(ctx: commands.Context, amount: Optional[int] = None, channel: Optional[discord.TextChannel] = None):
    """Spawns an interactive Super XP Drop manually into a designated or current room."""
    target_ch = channel or ctx.channel
    super_xp = amount if (amount and amount > 0) else random.randint(1000, 5000)

    super_embed = discord.Embed(
        title="🚨 🔥 SUPER XP DROP INCOMING! 🔥 🚨",
        description=(
            f"An authorized administrator has summoned a **SUPER DROP**!\n\n"
            f"🎁 **Reward:** `+{super_xp:,} XP`\n\n"
            f"**Click below immediately to claim it!** *(Disappears in 3 minutes)*"
        ),
        color=discord.Color.from_rgb(255, 69, 0),
        timestamp=discord.utils.utcnow(),
    )
    super_embed.set_footer(text=f"Summoned by {ctx.author.display_name} • Chill-Verse")

    view = SuperXPDropView(xp_amount=super_xp)
    try:
        sent_drop = await target_ch.send(embed=super_embed, view=view)
        view.message = sent_drop
        if target_ch.id != ctx.channel.id:
            await ctx.send(f"✅ Super Drop of `{super_xp:,} XP` spawned in {target_ch.mention}!", delete_after=5)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to spawn Super Drop: {e}", delete_after=6)


@bot.command(name="xpdrop", aliases=["dropxp"])
@is_authority_holder()
async def manual_xp_drop(ctx: commands.Context, amount: Optional[int] = None, channel: Optional[discord.TextChannel] = None):
    """Spawns a standard wild XP drop manually."""
    target_ch = channel or ctx.channel
    drop_xp = amount if (amount and amount > 0) else random.randint(50, 150)

    embed = discord.Embed(
        title="🎁 A WILD XP DROP APPEARED!",
        description=(
            f"Quick! Be the first member to click the button below to claim **+{drop_xp:,} XP**!\n\n"
            f"*(Disappears in 5 minutes if unclaimed)*"
        ),
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text=f"Spawned by {ctx.author.display_name} • Chill-Verse")

    view = ClaimXPDropView(xp_amount=drop_xp)
    try:
        sent_msg = await target_ch.send(embed=embed, view=view)
        view.message = sent_msg
        if target_ch.id != ctx.channel.id:
            await ctx.send(f"✅ Wild XP Drop of `{drop_xp:,} XP` spawned in {target_ch.mention}!", delete_after=5)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to spawn XP Drop: {e}", delete_after=6)


# ==============================================================================
# CHANNEL ISOLATION & ACCESS CONTROL
# ==============================================================================
@bot.command(name="lock")
@is_authority_holder()
async def lock_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"Locked by {ctx.author}")
    await ctx.send(f"🔒 {target.mention} has been locked for standard members.")


@bot.command(name="unlock")
@is_authority_holder()
async def unlock_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, send_messages=True, reason=f"Unlocked by {ctx.author}")
    await ctx.send(f"🔓 {target.mention} has been unlocked.")


@bot.command(name="hide")
@is_authority_holder()
async def hide_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, view_channel=False, reason=f"Hidden by {ctx.author}")
    await ctx.send(f"👁️‍🗨️ {target.mention} is now hidden from standard members.")


@bot.command(name="show")
@is_authority_holder()
async def show_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, view_channel=True, reason=f"Unhidden by {ctx.author}")
    await ctx.send(f"👁️ {target.mention} is now visible to standard members.")


@bot.command(name="permit")
@is_authority_holder()
async def permit(ctx: commands.Context, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(
        target,
        view_channel=True,
        send_messages=True,
        reason=f"Permitted by {ctx.author}",
    )
    await ctx.send(f"✅ Whitelisted {target.mention} in {ctx.channel.mention}.")


@bot.command(name="revoke")
@is_authority_holder()
async def revoke(ctx: commands.Context, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, overwrite=None, reason=f"Revoked by {ctx.author}")
    await ctx.send(f"🚫 Cleared specific overrides for {target.mention} in this channel.")


@bot.command(name="remove_bot_role")
@is_authority_holder()
async def remove_bot_role(ctx: commands.Context, target: Union[discord.Role, discord.Member, str]):
    if isinstance(target, (discord.Role, discord.Member)):
        await ctx.channel.set_permissions(target, view_channel=False, send_messages=False, reason=f"Cut by {ctx.author}")
        return await ctx.send(f"✂️ Removed channel permissions for {target.mention}.")

    if isinstance(target, str) and target.lower() == "all":
        for member in ctx.guild.members:
            if member.bot and member.id != bot.user.id:
                await ctx.channel.set_permissions(member, view_channel=False, send_messages=False)
        return await ctx.send("✂️ Revoked channel visibility from all external bots.")

    await ctx.send("⚠️ Pass a valid `@role`, `@bot`, or `all`.")


@bot.command(name="announce")
@is_authority_holder()
async def announce(ctx: commands.Context, *, raw_content: Optional[str] = None):
    if not raw_content or not raw_content.strip():
        return await ctx.send(
            "⚠️ **Usage:** `.announce [optional #channel] <Title> | <Message> [--everyone/--here]`\n"
            "**Example:** `.announce 📢 Updates | The new Puzzle channel is live! --everyone`",
            delete_after=10,
        )

    content = raw_content.strip()
    target_channel = None

    if ctx.message.channel_mentions:
        first_mention = ctx.message.channel_mentions[0]
        if content.startswith(first_mention.mention):
            target_channel = first_mention
            content = content[len(first_mention.mention):].strip()

    if not target_channel:
        target_channel = (
            discord.utils.get(ctx.guild.text_channels, name="📢・announcements")
            or discord.utils.get(ctx.guild.text_channels, name="announcements")
            or next((ch for ch in ctx.guild.text_channels if "announcement" in ch.name.lower()), None)
            or ctx.channel
        )

    mention_str = None
    if "--everyone" in content:
        mention_str = "@everyone"
        content = content.replace("--everyone", "").strip()
    elif "--here" in content:
        mention_str = "@here"
        content = content.replace("--here", "").strip()

    if "|" in content:
        parts = content.split("|", 1)
        title = parts[0].strip() or "Community Announcement"
        body = parts[1].strip()
    else:
        title = "Community Announcement"
        body = content.strip()

    if not body:
        body = "*No message body provided.*"

    bot_perms = target_channel.permissions_for(ctx.guild.me)
    if not (bot_perms.send_messages and bot_perms.embed_links):
        return await ctx.send(
            f"⚠️ **Permission Error:** I lack `Send Messages` or `Embed Links` in {target_channel.mention}.",
            delete_after=8,
        )

    embed = discord.Embed(
        title=title,
        description=body,
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text=f"Issued by {ctx.author.display_name}")
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    try:
        await target_channel.send(
            content=mention_str,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
        )
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        if target_channel.id != ctx.channel.id:
            await ctx.send(f"✅ Announcement dispatched to {target_channel.mention}.", delete_after=5)
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to send announcement: `{e}`", delete_after=8)


@bot.command(name="purge")
@is_purge_authorized()
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
        fetch_limit = min((amount - deleted_total) * 4, 300)
        async for old_msg in ctx.channel.history(limit=fetch_limit, before=cutoff):
            if deleted_total >= amount:
                break
            if purge_check(old_msg):
                try:
                    await old_msg.delete()
                    deleted_total += 1
                    await asyncio.sleep(0.3)
                except (discord.NotFound, discord.HTTPException):
                    pass

    target_desc = f"from {target.mention}" if isinstance(target, discord.Member) else (f"matching `{target}`" if target else "")
    await ctx.send(f"🧹 Cleared **{deleted_total}** message(s) {target_desc}.", delete_after=4)


# ==============================================================================
# BLUEPRINT, PANELS & MASTER BACKUP CONTROLS
# ==============================================================================
@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def setup_channels(ctx: commands.Context):
    guild = ctx.guild
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

            if raw_cat_name == "Admin Area 🔒":
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True, manage_channels=True
                    ),
                }
                for rname in ["Supreme Leader", "Highness"]:
                    r = discord.utils.get(guild.roles, name=rname)
                    if r:
                        overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            else:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False if is_restricted else True,
                        send_messages=False if (is_restricted or is_read_only) else True,
                        add_reactions=True,
                        read_message_history=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True, manage_channels=True
                    ),
                }
                admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]
                for rname in admin_roles:
                    r = discord.utils.get(guild.roles, name=rname)
                    if r:
                        overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            try:
                if ch_type == "text":
                    new_ch = await guild.create_text_channel(
                        name=raw_ch_name,
                        category=category,
                        overwrites=overwrites,
                        reason="Non-Destructive Missing Channel Creation",
                    )
                elif ch_type == "voice":
                    new_ch = await guild.create_voice_channel(
                        name=raw_ch_name,
                        category=category,
                        user_limit=user_lim,
                        overwrites=overwrites,
                        reason="Non-Destructive Missing Channel Creation",
                    )
                elif ch_type == "forum":
                    try:
                        new_ch = await guild.create_forum_channel(
                            name=raw_ch_name,
                            category=category,
                            overwrites=overwrites,
                            reason="Non-Destructive Missing Channel Creation",
                        )
                    except (discord.HTTPException, AttributeError):
                        new_ch = await guild.create_text_channel(
                            name=raw_ch_name,
                            category=category,
                            overwrites=overwrites,
                            reason="Non-Destructive Missing Channel Creation (Forum Fallback)",
                        )

                existing_channels_in_cat[norm_ch_name] = new_ch
                created_channels += 1
                await asyncio.sleep(0.4)

            except discord.HTTPException as e:
                print(f"Failed to create channel {raw_ch_name}: {e}")

    await get_or_create_memory_channel(guild)
    await get_or_create_audit_channel(guild)
    await get_or_create_testing_channel(guild)
    await enforce_admin_area_security(guild)

    embed = discord.Embed(
        title="✅ Server Blueprint Checked & Synced",
        description=(
            f"**Safe Provisioning Complete:**\n\n"
            f"• **New Categories Created:** `{created_cats}`\n"
            f"• **New Channels Created:** `{created_channels}`\n"
            f"• **Existing Channels Preserved (Skipped):** `{skipped_channels}`\n"
            f"• **Admin Area Security:** Strictly Supreme Leader, Highness & Arkbot only\n\n"
            f"*Zero existing channels or configurations were modified, overwritten, or duplicated.*"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )
    await status_msg.edit(content=None, embed=embed)


@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx: commands.Context):
    guild = ctx.guild
    status_msg = await ctx.send("⚙️ **Checking server roles... Skips existing to prevent duplicates/overwrites.**")

    base_perms = discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)

    roles_to_create = [
        {"name": "Supreme Leader", "perms": discord.Permissions(administrator=True), "color": discord.Color.dark_red(), "hoist": True, "mentionable": True},
        {"name": "Highness", "perms": discord.Permissions(administrator=True), "color": discord.Color.gold(), "hoist": True, "mentionable": True},
        {"name": "Authority", "perms": discord.Permissions(ban_members=True, kick_members=True, manage_channels=True, manage_roles=True), "color": discord.Color.orange(), "hoist": True, "mentionable": True},
        {"name": "Head Moderator", "perms": discord.Permissions(ban_members=True, kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.red(), "hoist": True, "mentionable": True},
        {"name": "Moderator", "perms": discord.Permissions(kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.yellow(), "hoist": True, "mentionable": True},
        {"name": "Trial Mod", "perms": discord.Permissions(moderate_members=True, manage_messages=True), "color": discord.Color.blue(), "hoist": True, "mentionable": True},
        {"name": "Chill-Verse Team", "perms": discord.Permissions(view_channel=True, send_messages=True, read_message_history=True), "color": discord.Color(0x313338), "hoist": True, "mentionable": False},
        {"name": "Chat Revive", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(26, 188, 156), "hoist": False, "mentionable": True},
        {"name": "Sovereign (Levels 60-70)", "perms": base_perms, "color": discord.Color.purple(), "hoist": True, "mentionable": False},
        {"name": "Legend (Levels 50-59)", "perms": base_perms, "color": discord.Color.dark_purple(), "hoist": False, "mentionable": False},
        {"name": "Champion (Levels 40-49)", "perms": base_perms, "color": discord.Color(0xED4245), "hoist": False, "mentionable": False},
        {"name": "Elite (Levels 30-39)", "perms": base_perms, "color": discord.Color.dark_green(), "hoist": False, "mentionable": False},
        {"name": "Vanguard (Levels 20-29)", "perms": base_perms, "color": discord.Color.green(), "hoist": False, "mentionable": False},
        {"name": "Explorer (Levels 10-19)", "perms": base_perms, "color": discord.Color.teal(), "hoist": False, "mentionable": False},
        {"name": "Newbie (Levels 1-9)", "perms": base_perms, "color": discord.Color.light_grey(), "hoist": False, "mentionable": False},
        {"name": "Member", "perms": base_perms, "color": discord.Color.default(), "hoist": False, "mentionable": False},
        {"name": "Bump Pings", "perms": discord.Permissions.none(), "color": discord.Color.purple(), "hoist": False, "mentionable": True},
        {"name": "Poll Pings", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False, "mentionable": True},
        {"name": "Red", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 0, 0), "hoist": False, "mentionable": False},
        {"name": "Yellow", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 255, 0), "hoist": False, "mentionable": False},
        {"name": "Green", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(0, 128, 0), "hoist": False, "mentionable": False},
        {"name": "Blue", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(0, 0, 255), "hoist": False, "mentionable": False},
        {"name": "Orange", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 165, 0), "hoist": False, "mentionable": False},
        {"name": "Pink", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 105, 180), "hoist": False, "mentionable": False},
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
                mentionable=role_data.get("mentionable", False),
                reason="Non-Destructive Role Provisioning",
            )
            existing_role_names.add(r_name_clean)
            created_count += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Failed to create role {role_data['name']}: {e}")

    await status_msg.edit(
        content=f"✅ **Role Sync Complete:** Created **{created_count}** missing role(s). Preserved **{skipped_count}** existing role(s)."
    )


@bot.command(name="setup_birthdays", aliases=["deploy_birthdays", "birthday_panel"])
@commands.has_permissions(administrator=True)
async def cmd_setup_birthdays(ctx: commands.Context):
    await deploy_birthday_panel(ctx.guild)
    await ctx.send("✅ Interactive birthday registration panel deployed to `#birthdays`!", delete_after=5)


@bot.command(name="colours", aliases=["colors", "setup_colours"])
@commands.has_permissions(administrator=True)
async def cmd_colours(ctx: commands.Context):
    await deploy_colours_panel(ctx.guild)
    await ctx.send("✅ Cosmetic colours panel deployed to `#🎨・colours` (Zero notifications attached)!", delete_after=5)


@bot.command(name="setup_confession_panel")
@commands.has_permissions(administrator=True)
async def cmd_setup_confession(ctx: commands.Context):
    await deploy_confession_panel(ctx.guild)
    await ctx.send("✅ Anonymous confession panel deployed to `#🚦confession-🖇️`!", delete_after=5)


@bot.command(name="setup_notifications", aliases=["setup_pings"])
@commands.has_permissions(administrator=True)
async def cmd_notifications(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    await deploy_notifications_panel(ctx.guild, channel or ctx.channel)
    await ctx.send("✅ Notification panel deployed!", delete_after=5)


@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx: commands.Context):
    await deploy_tickets_panel(ctx.guild)
    await ctx.send("✅ Support & Application panel deployed to `🎫・tickets`!", delete_after=5)


@bot.command(name="refresh_rules")
@commands.has_permissions(administrator=True)
async def refresh_rules(ctx: commands.Context):
    await deploy_team_rules_panel(ctx.guild)
    await deploy_team_news_commands_panel(ctx.guild, bot.command_prefix)
    await ctx.send("✅ **Team rules updated in `🛡️・team-rules` and command directory posted in `team-news`!**", delete_after=5)


@bot.command(name="refresh_commands", aliases=["refresh_bot_commands"])
@commands.has_permissions(administrator=True)
async def refresh_commands(ctx: commands.Context):
    await deploy_bot_commands_panel(ctx.guild, bot.command_prefix)
    await ctx.send("✅ **Master bot command manual refreshed in `💼・bot-commands`!**", delete_after=5)


@bot.command(name="afk")
async def afk(ctx: commands.Context, *, reason: Optional[str] = None):
    selected_status = reason.strip() if reason else random.choice(AFK_PRESET_MESSAGES)
    AFK_USERS[ctx.author.id] = {
        "reason": selected_status,
        "time": discord.utils.utcnow(),
    }
    await persist_runtime_state()

    embed = discord.Embed(
        description=f"🌙 **{ctx.author.display_name} is now AFK**\n*{selected_status}*",
        color=discord.Color.purple(),
    )
    await ctx.send(embed=embed, delete_after=10)
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass


@bot.command(name="backup_all")
@commands.has_permissions(administrator=True)
async def backup_all(ctx: commands.Context):
    """Generates the single unified master backup and overwrites previous ones."""
    status_msg = await ctx.send("🔄 **Generating single master backup & overwriting previous snapshots...**")
    payload = await generate_unified_backup_payload(ctx.guild)
    backup_file_path = MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id)
    await safe_write_json(backup_file_path, payload)

    file_stream = io.BytesIO(json.dumps(payload, indent=4).encode("utf-8"))
    file = discord.File(file_stream, filename=f"master_backup_{ctx.guild.id}.json")

    embed = discord.Embed(
        title="🔒 Single Master Backup Overwritten",
        description=(
            f"Successfully archived all server systems into one master file:\n"
            f"• **Categories & Channels:** `{len(payload['categories'])}`\n"
            f"• **Blueprint Layouts:** Synchronized\n"
            f"• **User XP Profiles:** `{len(payload['user_xp'])}`\n"
            f"• **Birthdays Recorded:** `{len(payload['user_birthdays'])}`\n"
            f"• **Confessions Stored:** `{len(payload['confessions'].get('entries', []))}`\n\n"
            f"*Previous backups cleared. This is now the sole recovery point.*"
        ),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )
    await status_msg.delete()
    await ctx.send(embed=embed, file=file)

    err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
        ctx.guild.text_channels, name="bot-errors"
    )
    if err_channel:
        await purge_all_old_backups(err_channel)
        file_stream.seek(0)
        await err_channel.send(
            content="🔒 **Master System Backup (Single Instance)**",
            file=discord.File(file_stream, filename=f"master_backup_{ctx.guild.id}.json"),
        )


@bot.command(name="restore_all")
@commands.has_permissions(administrator=True)
async def restore_all(ctx: commands.Context):
    """Restores from the single master backup and overwrites the backup point."""
    status_msg = await ctx.send("🔄 **Scanning for single master backup source...**")
    backup_data = None
    source_description = ""

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith(".json"):
            try:
                content = await attachment.read()
                backup_data = json.loads(content.decode("utf-8"))
                source_description = f"Uploaded File `{attachment.filename}`"
            except Exception as e:
                return await status_msg.edit(content=f"⚠️ Failed to parse attached JSON: `{e}`")

    if not backup_data:
        err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
            ctx.guild.text_channels, name="bot-errors"
        )
        if err_channel:
            await status_msg.edit(content="🔍 **Searching master snapshot in `🩸・bot-errors`...**")
            async for msg in err_channel.history(limit=50):
                if msg.author == ctx.guild.me and msg.attachments:
                    for att in msg.attachments:
                        if att.filename.endswith(".json"):
                            try:
                                content = await att.read()
                                backup_data = json.loads(content.decode("utf-8"))
                                source_description = f"Discord Master Snapshot `{att.filename}`"
                                break
                            except Exception:
                                continue
                if backup_data:
                    break

    if not backup_data:
        local_path = MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id)
        backup_data = await safe_read_json(local_path, None)
        if backup_data:
            source_description = f"Local Master File `{local_path}`"

    if not backup_data:
        return await status_msg.edit(
            content="⚠️ **No master backup found!** Either attach a `.json` backup file or ensure one exists in `🩸・bot-errors`."
        )

    await status_msg.edit(content=f"🔄 **Restoring system from {source_description}...**")

    stats = await apply_unified_restore(ctx.guild, backup_data)

    # Overwrite master backup after restoration
    fresh_payload = await generate_unified_backup_payload(ctx.guild)
    local_path = MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id)
    await safe_write_json(local_path, fresh_payload)

    err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
        ctx.guild.text_channels, name="bot-errors"
    )
    if err_channel:
        await purge_all_old_backups(err_channel)
        file_stream = io.BytesIO(json.dumps(fresh_payload, indent=4).encode("utf-8"))
        await err_channel.send(
            content="🔒 **Master System Backup (Overwritten Post-Restore)**",
            file=discord.File(file_stream, filename=f"master_backup_{ctx.guild.id}.json"),
        )

    embed = discord.Embed(
        title="✅ System Restored & Master Backup Overwritten",
        description=(
            f"Restoration from **{source_description}** complete:\n\n"
            f"• **Missing Channels Rebuilt:** `{stats['channels_created']}`\n"
            f"• **Missing Permissions Applied:** `{stats['perms_applied']}`\n"
            f"• **Existing Overwrites Preserved (Skipped):** `{stats['perms_skipped']}`\n"
            f"• **User XP Profiles Synchronized:** `{stats['xp_users']}`\n"
            f"• **Birthdays Restored:** `{stats['birthdays']}`\n"
            f"• **Confessions Restored:** `{stats['confessions']}`\n"
            f"• **Admin Area Security:** Strictly Supreme Leader, Highness & Arkbot only\n\n"
            f"*The single master backup has been overwritten with current verified server state.*"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )
    await status_msg.edit(content=None, embed=embed)


@bot.command(name="maintenance")
@commands.has_permissions(administrator=True)
async def maintenance_toggle(ctx: commands.Context, state: Optional[str] = None):
    global MAINTENANCE_MODE
    if state is None:
        MAINTENANCE_MODE = not MAINTENANCE_MODE
    elif state.lower() in ["on", "enable", "true"]:
        MAINTENANCE_MODE = True
    elif state.lower() in ["off", "disable", "false"]:
        MAINTENANCE_MODE = False
    elif state.lower() == "status":
        pass
    else:
        return await ctx.send("⚠️ Usage: `.maintenance [on/off/status]`", delete_after=5)

    await persist_runtime_state()
    status_str = "🔴 **ENABLED** (Commands locked to High Command only)" if MAINTENANCE_MODE else "🟢 **DISABLED** (All commands active)"
    embed = discord.Embed(
        title="🛠️ Maintenance Mode Status",
        description=f"Maintenance state is currently: {status_str}",
        color=discord.Color.red() if MAINTENANCE_MODE else discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )
    await ctx.send(embed=embed)


@bot.command(name="shutdown")
@commands.has_permissions(administrator=True)
async def shutdown(ctx: commands.Context, *, reason: str = "Scheduled system maintenance and upgrade."):
    confirm_msg = await ctx.send(
        "⚠️ **Initiating Maintenance Shutdown Protocol...**\n"
        "• Flushing database states to disk\n"
        "• Archiving single master backup\n"
        "• Shutting down runtime process..."
    )

    try:
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="⚠️ System Shutting Down"),
        )
    except Exception:
        pass

    await persist_runtime_state()
    await flush_xp_cache()

    for guild in bot.guilds:
        try:
            payload = await generate_unified_backup_payload(guild)
            backup_file_path = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
            await safe_write_json(backup_file_path, payload)

            err_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(
                guild.text_channels, name="bot-errors"
            )
            if err_channel:
                await purge_all_old_backups(err_channel)
                file_stream = io.BytesIO(json.dumps(payload, indent=4).encode("utf-8"))
                backup_file = discord.File(file_stream, filename=f"master_backup_{guild.id}.json")

                shutdown_embed = discord.Embed(
                    title="🛑 SYSTEM MAINTENANCE SHUTDOWN",
                    description=(
                        f"**Authorized by:** {ctx.author.mention}\n"
                        f"**Reason:** *{reason}*\n\n"
                        "🔒 **Pre-Shutdown Single Master Backup Attached.**\n"
                        "All runtime states, XP databases, channel configurations, and birthdays have been preserved.\n"
                        "The bot process is now disconnecting from Discord."
                    ),
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow(),
                )
                shutdown_embed.set_footer(text="Arkbot Architecture Shutdown Engine")
                await err_channel.send(embed=shutdown_embed, file=backup_file)
        except Exception as e:
            print(f"[Maintenance Shutdown Error] Guild {guild.id}: {e}")

    final_embed = discord.Embed(
        title="🛑 Process Termination Completed",
        description=(
            "✅ Single master snapshot archived to disk.\n"
            "✅ Clean master backup uploaded to `🩸・bot-errors`.\n"
            "🔌 Disconnecting gateway and exiting process now."
        ),
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    await confirm_msg.edit(content=None, embed=final_embed)

    if hourly_backup_task.is_running():
        hourly_backup_task.cancel()
    if birthday_announcer_task.is_running():
        birthday_announcer_task.cancel()
    if xp_drop_task.is_running():
        xp_drop_task.cancel()
    if xp_flush_task.is_running():
        xp_flush_task.cancel()

    await asyncio.sleep(1.0)
    await bot.close()
    sys.exit(0)


# ==============================================================================
# RUN BOT
# ==============================================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("⚠️ CRITICAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is missing!")
    else:
        bot.run(TOKEN)
