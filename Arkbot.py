import os
import io
import asyncio
import datetime
import random
import json
from collections import defaultdict

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

# Leveling & Cooldown Configuration
MAX_LEVEL = 60
XP_COOLDOWN_SECONDS = 60
BUMP_COOLDOWN_SECONDS = 7200

LEVEL_TIER_ROLES = {
    (1, 9): {"name": "Newbie", "color": discord.Color.teal()},
    (10, 19): {"name": "Explorer", "color": discord.Color.green()},
    (20, 29): {"name": "Veteran", "color": discord.Color.blue()},
    (30, 39): {"name": "Elite", "color": discord.Color.purple()},
    (40, 49): {"name": "Champion", "color": discord.Color.gold()},
    (50, 59): {"name": "Legend", "color": discord.Color.orange()},
    (60, 60): {"name": "Sovereign", "color": discord.Color.dark_red()}
}

RESTRICTED_ADMIN_ROLES = ["authority", "head moderator", "moderator"]

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

# Per-Guild State Dictionaries: {guild_id: {user_id: data}}
user_xp = defaultdict(dict)
user_levels = defaultdict(dict)
user_warnings = defaultdict(dict)
user_mute_counts = defaultdict(dict)
afk_users = defaultdict(dict)
afk_mentions = defaultdict(lambda: defaultdict(list))
user_birthdays = defaultdict(dict)
last_birthday_wished = defaultdict(dict)

last_xp_awarded = defaultdict(dict)
last_bump_times = defaultdict(float)

# ==========================================
# PERMISSION & HIERARCHY GUARDS
# ==========================================
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
# PROGRESSION SYSTEM CALCULATIONS
# ==========================================
def get_xp_for_level(level: int) -> int:
    if level >= MAX_LEVEL:
        return 100 * (MAX_LEVEL ** 2) + 400 * MAX_LEVEL
    return 100 * (level ** 2) + 400 * level

def get_tier_info_for_level(level: int) -> dict:
    for (min_lvl, max_lvl), tier_data in LEVEL_TIER_ROLES.items():
        if min_lvl <= level <= max_lvl:
            return tier_data
    return LEVEL_TIER_ROLES[(1, 9)]

async def ensure_role_exists(guild: discord.Guild, role_name: str, color: discord.Color):
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            role = await guild.create_role(name=role_name, color=color, reason="Auto System Setup")
        except discord.Forbidden:
            return None
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
    except discord.Forbidden:
        pass

async def add_xp(user: discord.Member, amount: int):
    if user.bot or not user.guild:
        return

    guild_id = user.guild.id
    user_id = user.id
    current_level = user_levels[guild_id].get(user_id, 1)

    if current_level >= MAX_LEVEL:
        return

    current_xp = user_xp[guild_id].get(user_id, 0) + amount
    xp_needed = get_xp_for_level(current_level)

    if current_xp >= xp_needed:
        new_level = min(current_level + 1, MAX_LEVEL)
        user_levels[guild_id][user_id] = new_level
        user_xp[guild_id][user_id] = current_xp - xp_needed

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
            await target_channel.send(embed=embed)
    else:
        user_xp[guild_id][user_id] = current_xp

# ==========================================
# CHANNEL MANAGER (EXACT-CHANNEL ROUTING)
# ==========================================
async def get_or_create_announcement_channel(guild: discord.Guild):
    ch_id = announcement_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() in ["announcements", "level-announcements", "level-ups"], guild.text_channels)
    if channel:
        announcement_channels[guild.id] = channel.id
        return channel

    try:
        new_ch = await guild.create_text_channel("level-announcements")
        announcement_channels[guild.id] = new_ch.id
        return new_ch
    except discord.Forbidden:
        return None

async def get_or_create_bot_commands_channel(guild: discord.Guild):
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
    except discord.Forbidden:
        return None

async def get_or_create_bump_channel(guild: discord.Guild):
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
    except discord.Forbidden:
        return None

async def get_or_create_birthday_channel(guild: discord.Guild):
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
    except discord.Forbidden:
        return None

async def get_or_create_memory_channel(guild: discord.Guild):
    ch_id = bot_memory_channels.get(guild.id)
    if ch_id and guild.get_channel(ch_id):
        return guild.get_channel(ch_id)

    channel = discord.utils.find(lambda c: c.name.lower() == "bot-memory", guild.text_channels)
    if channel:
        bot_memory_channels[guild.id] = channel.id
        return channel

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channel=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True, attach_files=True)
        }
        new_ch = await guild.create_text_channel("bot-memory", overwrites=overwrites)
        bot_memory_channels[guild.id] = new_ch.id
        return new_ch
    except discord.Forbidden:
        return None

# ==========================================
# FILE-ATTACHMENT BACKUP ENGINE
# ==========================================
async def save_data_to_channel(guild: discord.Guild):
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
        "user_birthdays": {str(k): v for k, v in user_birthdays[gid].items()}
    }

    raw_json = json.dumps(payload, indent=2).encode("utf-8")
    data_file = discord.File(io.BytesIO(raw_json), filename=f"backup_{gid}.json")
    timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    await memory_channel.send(f"💾 **[DATABASE STATE SYNC]** `{timestamp}`", file=data_file)

async def restore_data_from_channel(guild: discord.Guild) -> int:
    memory_channel = await get_or_create_memory_channel(guild)
    if not memory_channel:
        return 0

    gid = guild.id
    async for message in memory_channel.history(limit=25):
        if message.author.id == bot.user.id and message.attachments:
            for attachment in message.attachments:
                if attachment.filename.endswith(".json"):
                    try:
                        content = await attachment.read()
                        data = json.loads(content.decode("utf-8"))

                        user_xp[gid] = {int(k): v for k, v in data.get("user_xp", {}).items()}
                        user_levels[gid] = {int(k): v for k, v in data.get("user_levels", {}).items()}
                        user_warnings[gid] = {int(k): v for k, v in data.get("user_warnings", {}).items()}
                        user_mute_counts[gid] = {int(k): v for k, v in data.get("user_mute_counts", {}).items()}
                        afk_users[gid] = {int(k): v for k, v in data.get("afk_users", {}).items()}
                        user_birthdays[gid] = {int(k): v for k, v in data.get("user_birthdays", {}).items()}

                        return len(user_levels[gid])
                    except Exception as e:
                        print(f"Failed to restore snapshot: {e}")
                        return 0
    return 0

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

# ==========================================
# SCHEDULED HOURLY BIRTHDAY CHECKER
# ==========================================
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

                await bday_ch.send(content=f"🎊 Happy Birthday {member.mention}! 🎊", embed=embed)
                await add_xp(member, 500)

@check_birthdays_loop.before_loop
async def before_birthdays():
    await bot.wait_until_ready()

# ==========================================
# DUAL-TIMER DISBOARD BUMP REMINDER
# ==========================================
async def schedule_bump_reminders(guild: discord.Guild, bump_channel: discord.TextChannel):
    """Handles the two-stage countdown and pings the Bump Ping role when available."""
    # Timer 1: 1 Hour 45 Minutes (6300s) -> 15-Minute Warning
    await asyncio.sleep(6300)
    target_unix = int(datetime.datetime.now(datetime.timezone.utc).timestamp() + 900)
    await bump_channel.send(
        f"⏳ **Bump Heads-Up**: Next bump available in **15 minutes** (<t:{target_unix}:R>)!"
    )

    # Timer 2: Remaining 15 Minutes (900s) -> Total 2 Hours (7200s)
    await asyncio.sleep(900)
    bump_role = discord.utils.get(guild.roles, name="Bump Ping")
    role_mention = bump_role.mention if bump_role else "@here"

    await bump_channel.send(
        f"🔔 {role_mention} **It's Time To Bump!** Use `/bump` to promote the server again!"
    )

# ==========================================
# UI CONFIRMATION VIEW FOR RESTOREDATA
# ==========================================
class RestoreConfirmView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "⛔ **Access Denied**: Only the administrator running this command can interact.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm Overwrite", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="⏳ **Reading snapshot and restoring server data from `#bot-memory`...**",
            embed=None,
            view=self
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🛑 **Operation Aborted**: Active in-memory state remains untouched.",
            embed=None,
            view=self
        )
        self.stop()

# ==========================================
# SYSTEM EVENT LISTENERS
# ==========================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"System Creator: {BOT_CREATOR_USERNAME} ({BOT_CREATOR_REAL_NAME}) | {BOT_COMPANY_NAME}")

    if not periodic_backup_loop.is_running():
        periodic_backup_loop.start()
    if not check_birthdays_loop.is_running():
        check_birthdays_loop.start()

    for guild in bot.guilds:
        await get_or_create_bump_channel(guild)
        await get_or_create_bot_commands_channel(guild)
        await get_or_create_birthday_channel(guild)
        announcement_ch = await get_or_create_announcement_channel(guild)

        restored_count = await restore_data_from_channel(guild)
        if restored_count and announcement_ch:
            await announcement_ch.send(f"♻️ **Database Recovered**: Loaded profiles for **{restored_count} members**.")
        else:
            for member in guild.members:
                if not member.bot and member.id not in user_levels[guild.id]:
                    user_levels[guild.id][member.id] = 1
                    user_xp[guild.id][member.id] = 0

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
        await ctx.send("❌ **Invalid Parameter**: Check user mentions, roles, or integer amounts.")
    else:
        print(f"Unhandled Error on command {ctx.command}: {error}")

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    gid = member.guild.id
    user_levels[gid][member.id] = 1
    user_xp[gid][member.id] = 0

    await update_member_level_role(member, 1)

    announcement_ch = await get_or_create_announcement_channel(member.guild)
    if announcement_ch:
        await announcement_ch.send(f"👋 Welcome to the server, {member.mention}! You've been assigned **Newbie** (Level 1).")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    gid = message.guild.id
    uid = message.author.id
    current_time = asyncio.get_event_loop().time()

    # Clear AFK Status
    if uid in afk_users[gid] and not message.content.startswith(".afk"):
        del afk_users[gid][uid]
        welcome_back = f"👋 Welcome back {message.author.mention}, your AFK status has been cleared."
        if uid in afk_mentions[gid] and afk_mentions[gid][uid]:
            missed = "\n".join(afk_mentions[gid][uid][-5:])
            welcome_back += f"\n\n📬 **Missed Pings (Last 5):**\n{missed}"
            del afk_mentions[gid][uid]
        await message.channel.send(welcome_back)

    # Award Chat XP with Cooldown
    last_xp = last_xp_awarded[gid].get(uid, 0.0)
    if current_time - last_xp >= XP_COOLDOWN_SECONDS:
        last_xp_awarded[gid][uid] = current_time
        await add_xp(message.author, 15)

    # Disboard Bump Event Tracking
    bump_ch = await get_or_create_bump_channel(message.guild)
    if bump_ch and message.channel.id == bump_ch.id:
        if message.author.id == DISBOARD_BOT_ID and message.embeds:
            for embed in message.embeds:
                desc = embed.description or ""
                if "Bump done" in desc:
                    last_bump = last_bump_times[gid]
                    elapsed = current_time - last_bump

                    if last_bump != 0 and elapsed < BUMP_COOLDOWN_SECONDS:
                        diff = int(BUMP_COOLDOWN_SECONDS - elapsed)
                        m, s = divmod(diff, 60)
                        h, m = divmod(m, 60)
                        await message.channel.send(f"⚠️ **Disboard Cooldown Active**: Next bump ready in **{h}h {m}m**.")
                        return

                    last_bump_times[gid] = current_time
                    bumper = message.interaction.user if message.interaction else None
                    cheer = random.choice(CUTE_BUMP_MESSAGES)

                    if bumper and isinstance(bumper, discord.Member):
                        await add_xp(bumper, 200)
                        await message.channel.send(f"Thank you for bumping, {bumper.mention}! (+200 XP)\n*{cheer}*")
                    else:
                        await message.channel.send(f"Server bumped successfully! (+200 XP)\n*{cheer}*")

                    # Launch two-stage reminder timers
                    asyncio.create_task(schedule_bump_reminders(message.guild, bump_ch))

    # AFK Ping Watcher
    if message.mentions:
        for target in message.mentions:
            if target.id in afk_users[gid] and target.id != uid:
                reason = afk_users[gid][target.id]
                afk_mentions[gid][target.id].append(
                    f"• {message.author.display_name} in {message.channel.mention}: {message.clean_content}"
                )
                await message.channel.send(f"ℹ️ {target.display_name} is currently AFK: **{reason}**")

    await bot.process_commands(message)

# ==========================================
# BIRTHDAY COMMANDS (#birthdays ONLY)
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
    gid = ctx.guild.id
    bday_data = user_birthdays[gid].get(target.id)

    if not bday_data:
        msg = "You haven't set a birthday yet! Use `.setbirthday DD-MM`." if target == ctx.author else f"{target.display_name} hasn't registered a birthday."
        return await ctx.send(f"ℹ️ {msg}")

    display = f"{bday_data['day']:02d}/{bday_data['month']:02d}"
    if bday_data.get("year"):
        display += f"/{bday_data['year']}"

    await ctx.send(f"🎈 {target.mention}'s birthday is set for **{display}**.")

# ==========================================
# LEVEL & XP PROGRESSION COMMANDS
# ==========================================
@bot.command(name="level")
async def check_level(ctx, member: discord.Member = None):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Please use {cmd_ch.mention} to check levels.")

    target = member or ctx.author
    gid = ctx.guild.id
    lvl = user_levels[gid].get(target.id, 1)
    xp = user_xp[gid].get(target.id, 0)
    tier_data = get_tier_info_for_level(lvl)

    if lvl >= MAX_LEVEL:
        await ctx.send(f"⭐ {target.display_name} is at maximum **Level {MAX_LEVEL}**! Tier: **{tier_data['name']}** ({xp} XP).")
    else:
        needed = get_xp_for_level(lvl)
        await ctx.send(f"📊 {target.display_name}: **Level {lvl}** | Tier: **{tier_data['name']}** ({xp} / {needed} XP).")

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
        return await ctx.send(f"❌ Level range boundary: **1 to {MAX_LEVEL}**.")

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
    await ctx.send(f"✅ Synchronized level tier roles for **{synced} member(s)**.")

# ==========================================
# RESTRICTED ROLE MANAGEMENT
# ==========================================
@bot.command(name="promote")
@is_admin_or_owner()
async def promote_staff(ctx, member: discord.Member, *, new_role_name: str):
    target_role = discord.utils.get(ctx.guild.roles, name=new_role_name)
    if not target_role:
        return await ctx.send(f"❌ Role `{new_role_name}` not found.")

    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Action rejected: Target holds an equal or higher role.")

    if ctx.guild.me.top_role <= target_role:
        return await ctx.send("❌ Hierarchy conflict: Bot role is lower than target role.")

    if target_role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already holds the **{target_role.name}** role.")

    await member.add_roles(target_role, reason=f"Promoted by {ctx.author}")
    await ctx.send(f"🎉 **PROMOTION**: {member.mention} promoted to **{target_role.name}** by {ctx.author.mention}!")

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
        return await ctx.send("❌ Action rejected: Target holds an equal or higher role.")
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ Cannot assign a role positioned above or equal to the bot.")
    if role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already holds `{role.name}`.")
    await member.add_roles(role, reason=f"Assigned by {ctx.author}")
    await ctx.send(f"✅ Assigned **{role.name}** to {member.mention}.")

@bot.command(name="revoke")
@is_admin_or_owner()
async def revoke_role(ctx, member: discord.Member, *, role: discord.Role):
    if not can_moderate_member(ctx, member):
        return await ctx.send("❌ Action rejected: Target holds an equal or higher role.")
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ Cannot revoke a role positioned above the bot.")
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
                await asyncio.sleep(0.5)
            except discord.Forbidden:
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
            await asyncio.sleep(0.5)
        except discord.Forbidden:
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
    status = await ctx.send("⚙️ Configuring Level Tiers and Staff Structure...")
    guild = ctx.guild

    for _, tier in LEVEL_TIER_ROLES.items():
        await ensure_role_exists(guild, tier["name"], tier["color"])

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

@bot.command(name="color")
async def set_color(ctx, *, color_name: str):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Color roles can only be selected in {cmd_ch.mention}.")

    matched_role_name = None
    for name in PRO_HEX_COLORS.keys():
        if color_name.lower() in name.lower():
            matched_role_name = name
            break

    if not matched_role_name:
        return await ctx.send(f"❌ Invalid selection. Available: {', '.join(PRO_HEX_COLORS.keys())}")

    role = discord.utils.get(ctx.guild.roles, name=matched_role_name)
    if not role:
        return await ctx.send(f"❌ Role `{matched_role_name}` is not initialized. Run `.autorole_setup`.")

    active_colors = [r for r in ctx.author.roles if r.name in PRO_HEX_COLORS.keys()]
    if active_colors:
        await ctx.author.remove_roles(*active_colors)

    await ctx.author.add_roles(role)
    await ctx.send(f"🎨 Assigned **{role.name}** to {ctx.author.mention}!")

# ==========================================
# SERVER MODERATION ENGINE
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
            await ctx.send(f"❌ Failed to auto-ban {member.mention}: Missing top-role clearance.")

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

# ==========================================
# TEXT & VOICE CHANNEL CONTROLS
# ==========================================
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
# SYSTEM, DATA & UTILITY COMMANDS
# ==========================================
@bot.command(name="savedata")
@is_admin_or_higher()
async def force_save(ctx):
    await save_data_to_channel(ctx.guild)
    await ctx.send("💾 State snapshot safely committed to `#bot-memory`.")

@bot.command(name="restoredata", aliases=["loaddata", "recoverdata"])
@is_admin_or_owner()
async def force_restore_data(ctx):
    view = RestoreConfirmView(ctx)
    embed = discord.Embed(
        title="⚠️ Database Recovery Confirmation",
        description=(
            "Restoring will **overwrite all live session data** (XP, Levels, Warnings, Timeouts, AFK, Birthdays) "
            "with the latest snapshot in `#bot-memory`.\n\n"
            "Do you want to proceed?"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Prompt expires in 30 seconds.")
    prompt_msg = await ctx.send(embed=embed, view=view)

    await view.wait()

    if view.value is None:
        for child in view.children:
            child.disabled = True
        return await prompt_msg.edit(content="⏱️ **Confirmation Timed Out**: Restore aborted.", embed=None, view=view)

    if not view.value:
        return

    restored_count = await restore_data_from_channel(ctx.guild)
    if restored_count > 0:
        await prompt_msg.edit(content=f"♻️ **State Restored**: Indexed **{restored_count} members** from `#bot-memory`.", view=None)
    else:
        await prompt_msg.edit(content="❌ **Recovery Failed**: No valid backup file located in `#bot-memory`.", view=None)

@bot.command(name="botcommands")
@is_admin_or_higher()
async def bot_commands(ctx):
    cmd_ch = await get_or_create_bot_commands_channel(ctx.guild)
    if cmd_ch and ctx.channel.id != cmd_ch.id:
        return await ctx.send(f"❌ Please run this command inside {cmd_ch.mention}.")

    embed = discord.Embed(
        title="📜 Server Management Command Reference",
        description="Reference guide for operations, moderation, and member features:",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="🎖️ Leveling & Members (#bot-commands)",
        value=(
            "`.level [@user]` - Check progression & tier rank.\n"
            "`.leaderboard` - View top 10 ranked members.\n"
            "`.color <name>` - Equip custom hex role.\n"
            "`.userinfo [@user]` - View member overview.\n"
            "`.serverinfo` - Display guild analytics.\n"
            "`.afk [reason]` - Set personal AFK status."
        ),
        inline=False
    )
    embed.add_field(
        name="🎂 Birthday Engine (#birthdays)",
        value=(
            "`.setbirthday DD-MM[-YYYY]` - Register your birthday.\n"
            "`.birthday [@user]` - Look up a birthday date."
        ),
        inline=False
    )
    embed.add_field(
        name="🚀 Server Growth (#bump)",
        value="`.bump` - Track Disboard bump (+200 XP).",
        inline=False
    )
    embed.add_field(
        name="🛠️ Administrative & Level Overrides",
        value=(
            "`.addxp @user <amount>` - Manual XP grant.\n"
            "`.setlevel @user <1-60>` - Force level override.\n"
            "`.synclevels` - Resync tier roles server-wide.\n"
            "`.savedata` - Save immediate backup snapshot.\n"
            "`.restoredata` - Restore state from `#bot-memory`.\n"
            "`.update <text>` - Publish system update release."
        ),
        inline=False
    )
    embed.add_field(
        name="🔒 Role Administration (Admin / Owner Only)",
        value=(
            "`.promote @user <Role>` - Direct staff promotion.\n"
            "`.authority @user` - Grant Authority role.\n"
            "`.assign @user <Role>` - Assign role to user.\n"
            "`.revoke @user <Role>` - Revoke role from user.\n"
            "`.role addall <Role>` - Assign role to all members.\n"
            "`.role removeall <Role>` - Strip role from all members.\n"
            "`.role members <Role>` - List members holding role.\n"
            "`.autorole_setup` - Initialize roles & colors.\n"
            "`.createrole <Name> <Hex>` - Create colored role.\n"
            "`.deleterole <Role>` - Delete server role."
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Moderation Engine",
        value=(
            "`.warn @user [reason]` - Issue warning (3 strikes = Ban).\n"
            "`.clearwarns @user` - Reset member warnings.\n"
            "`.mute @user [reason]` - Tiered timeout (1h, 6h, 12h).\n"
            "`.unmute @user` - Lift user timeout.\n"
            "`.kick @user [reason]` - Kick user from server.\n"
            "`.ban @user [reason]` - Ban user from server.\n"
            "`.purge <1-100>` - Bulk delete messages."
        ),
        inline=False
    )
    embed.add_field(
        name="🔒 Text & Voice Controls",
        value=(
            "`.lockdown [#channel]` / `.unlock [#channel]` - Text rights.\n"
            "`.vc_lock <#vc>` / `.vc_unlock <#vc>` - Connect rights.\n"
            "`.vc_mute @user` / `.vc_unmute @user` - Server mute in VC.\n"
            "`.vc_deafen @user` / `.vc_undeafen @user` - Server deafen.\n"
            "`.vc_move @user <#vc>` - Move member to another voice channel."
        ),
        inline=False
    )
    embed.set_footer(text=f"Authorized Staff Reference • {BOT_COMPANY_NAME}")
    await ctx.send(embed=embed)

@bot.command(name="update")
@is_admin_or_higher()
async def bot_update(ctx, *, update_details: str):
    target_channel = await get_or_create_bot_commands_channel(ctx.guild)
    if not target_channel:
        return await ctx.send("❌ Channel `#bot-commands` not initialized.")

    update_embed = discord.Embed(
        title="⚙️ Bot System Update",
        description=f"{update_details}\n\n*Maintained by {BOT_CREATOR_USERNAME} ({BOT_CREATOR_REAL_NAME}) | {BOT_COMPANY_NAME}*",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    await target_channel.send(embed=update_embed)
    if ctx.channel.id != target_channel.id:
        await ctx.send(f"✅ Update posted to {target_channel.mention}.")

@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.guild.id][ctx.author.id] = reason
    await ctx.send(f"💤 {ctx.author.mention} is now AFK: **{reason}**")

@bot.command(name="bump")
async def bump(ctx):
    bump_ch = await get_or_create_bump_channel(ctx.guild)
    if bump_ch and ctx.channel.id != bump_ch.id:
        return await ctx.send(f"❌ `.bump` is restricted to {bump_ch.mention}.")

    gid = ctx.guild.id
    current_time = asyncio.get_event_loop().time()
    last_bump = last_bump_times[gid]
    elapsed = current_time - last_bump

    if last_bump != 0 and elapsed < BUMP_COOLDOWN_SECONDS:
        diff = int(BUMP_COOLDOWN_SECONDS - elapsed)
        m, s = divmod(diff, 60)
        h, m = divmod(m, 60)
        return await ctx.send(f"❌ **Cooldown Active**: Wait **{h}h {m}m** before bumping.")

    last_bump_times[gid] = current_time
    await add_xp(ctx.author, 200)
    cheer = random.choice(CUTE_BUMP_MESSAGES)
    await ctx.send(f"Thank you for bumping, {ctx.author.mention}! (**+200 XP**)\n*{cheer}*")

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
# BOT EXECUTION
# ==========================================
bot.run(os.getenv("DISCORD_TOKEN"))
