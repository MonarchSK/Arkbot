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

afk_users = {}
afk_mentions = {}
user_xp = {}
user_levels = {}
user_warnings = {}
user_mute_counts = {}

last_bump_time = 0
bump_cooldown_seconds = 7200  # 2 Hours

# ==========================================
# HELPER FUNCTIONS & STRICT PERMISSION CHECKS
# ==========================================
def is_admin_or_owner():
    """Restricts command execution exclusively to the Server Owner or Server Administrators."""
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
        raise commands.CheckFailure("⛔ **Permission Denied**: Only the Server Owner or an Administrator can use role management commands.")
    return commands.check(predicate)

def is_admin_or_higher():
    """Allows Owners, Admins, and predefined staff roles for general management tasks."""
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
        user_roles = [r.name.lower() for r in ctx.author.roles]
        if any(role_name in user_roles for role_name in RESTRICTED_ADMIN_ROLES):
            return True
        raise commands.CheckFailure(" You do not have permission to run this command.")
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
            guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channel=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
        }
        new_ch = await guild.create_text_channel("bot-memory", overwrites=overwrites)
        BOT_MEMORY_CHANNEL_ID = new_ch.id
        await new_ch.send("💾 **Bot Memory Channel Created.** Restricted to Server Administrators, Server Owner, and Bot System.")
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
                raw_json = message.content.split("```json")[1].split("```")[0].strip()
                data = json.loads(raw_json)

                user_xp = {int(k): v for k, v in data.get("user_xp", {}).items()}
                user_levels = {int(k): v for k, v in data.get("user_levels", {}).items()}
                user_warnings = {int(k): v for k, v in data.get("user_warnings", {}).items()}
                user_mute_counts = {int(k): v for k, v in data.get("user_mute_counts", {}).items()}
                afk_users = {int(k): v for k, v in data.get("afk_users", {}).items()}

                return len(user_levels)
            except Exception as e:
                print(f"Error restoring data: {e}")
                return False
    return False

# ==========================================
# LEVELING & EXPERIENCE SYSTEM
# ==========================================
async def add_xp(user, amount, guild, fallback_channel):
    user_id = user.id
    current_level = user_levels.get(user_id, 1)

    if current_level >= MAX_LEVEL:
        return

    current_xp = user_xp.get(user_id, 0) + amount
    user_xp[user_id] = current_xp
    xp_needed = get_xp_for_level(current_level)

    if current_xp >= xp_needed:
        new_level = min(current_level + 1, MAX_LEVEL)
        user_levels[user_id] = new_level
        
        await update_member_level_role(user, new_level)

        target_channel = await get_or_create_announcement_channel(guild) or fallback_channel
        if target_channel:
            tier_info = get_tier_info_for_level(new_level)
            await target_channel.send(
                f"🎉 **[LEVEL UP]** {user.mention} advanced to **Level {new_level}**! Tier: **{tier_info['name']}**!"
            )
    
    await save_data_to_channel(guild)

# ==========================================
# EVENT LISTENERS
# ==========================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print(f"System Creator: {BOT_CREATOR_USERNAME} ({BOT_CREATOR_REAL_NAME}) | {BOT_COMPANY_NAME}")
    
    for guild in bot.guilds:
        await get_or_create_bump_channel(guild)
        await get_or_create_bot_commands_channel(guild)
        announcement_channel = await get_or_create_announcement_channel(guild)

        restored_count = await restore_data_from_channel(guild)
        
        if restored_count:
            if announcement_channel:
                await announcement_channel.send(
                    f"♻️ **Database Recovered**: Loaded profiles for **{restored_count} members** from `#bot-memory`."
                )
        else:
            newly_added = 0
            for member in guild.members:
                if not member.bot and member.id not in user_levels:
                    user_levels[member.id] = 1
                    user_xp[member.id] = 0
                    newly_added += 1

            if newly_added > 0 and announcement_channel:
                await announcement_channel.send(
                    f"⚙️ **Initialization Complete**: Indexed **{newly_added} members** at Level 1."
                )
            await save_data_to_channel(guild)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(f"{error}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Access Denied**: Insufficient Discord permissions.")
    else:
        raise error

@bot.event
async def on_member_join(member):
    user_levels[member.id] = 1
    user_xp[member.id] = 0

    await update_member_level_role(member, 1)

    target_channel = await get_or_create_announcement_channel(member.guild) or member.guild.system_channel
    if target_channel:
        await target_channel.send(
            f" Welcome to the server, {member.mention}! You've been assigned **Newbie** (Level 1)."
        )
    await save_data_to_channel(member.guild)

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or message.author.bot or not message.guild:
        return

    # Clear AFK Status
    if message.author.id in afk_users and not message.content.startswith(".afk"):
        del afk_users[message.author.id]
        welcome_msg = f"👋 Welcome back {message.author.mention}, your AFK status was removed."
        
        if message.author.id in afk_mentions and afk_mentions[message.author.id]:
            missed = "\n".join(afk_mentions[message.author.id][-5:])
            welcome_msg += f"\n\n📬 **Missed Mentions:**\n{missed}"
            del afk_mentions[message.author.id]

        await message.channel.send(welcome_msg)
        await save_data_to_channel(message.guild)

    # Award Chat XP
    await add_xp(message.author, 15, message.guild, message.channel)

    bump_channel = await get_or_create_bump_channel(message.guild)

    # Disboard Bump Event Handler
    if bump_channel and message.channel.id == bump_channel.id:
        if message.author.id == DISBOARD_BOT_ID and message.embeds:
            for embed in message.embeds:
                description = embed.description or ""
                if "Bump done" in description:
                    global last_bump_time
                    current_time = asyncio.get_event_loop().time()
                    time_passed = current_time - last_bump_time

                    if last_bump_time != 0 and time_passed < bump_cooldown_seconds:
                        remaining = int(bump_cooldown_seconds - time_passed)
                        m, s = divmod(remaining, 60)
                        h, m = divmod(m, 60)
                        await message.channel.send(
                            f"⚠️ **Cooldown Active**: Wait **{h}h {m}s** before bumping again."
                        )
                        return

                    last_bump_time = current_time
                    bumper = message.interaction.user if message.interaction else None
                    cute_line = random.choice(CUTE_BUMP_MESSAGES)

                    if bumper:
                        await add_xp(bumper, 200, message.guild, message.channel)
                        await message.channel.send(f"Thank you for bumping, {bumper.mention}! (+200 XP)\n*{cute_line}*")
                    else:
                        await message.channel.send(f"Thank you for bumping! (+200 XP)\n*{cute_line}*")

                    await asyncio.sleep(bump_cooldown_seconds)
                    await message.channel.send("⏰ **Bump Available!** Type `.bump` to promote the server again!")

    # Check for AFK Mentions
    if message.mentions:
        for mention in message.mentions:
            if mention.id in afk_users and mention.id != message.author.id:
                reason = afk_users[mention.id]
                if mention.id not in afk_mentions:
                    afk_mentions[mention.id] = []
                afk_mentions[mention.id].append(f"From {message.author.display_name} in {message.channel.mention}: {message.content}")
                await message.channel.send(f"ℹ️ {mention.display_name} is currently AFK: **{reason}**")

    await bot.process_commands(message)

# ==========================================
# ADMIN & OWNER ONLY ROLE PROMOTION & MANAGEMENT
# ==========================================
@bot.command(name="promote")
@is_admin_or_owner()
async def promote_staff(ctx, member: discord.Member, *, new_role_name: str):
    """Direct promotion command restricted strictly to Admin / Owner.
    Usage: .promote @user Head Moderator
    """
    target_role = discord.utils.get(ctx.guild.roles, name=new_role_name)
    if not target_role:
        return await ctx.send(f"❌ Role `{new_role_name}` was not found on this server.")

    if ctx.guild.me.top_role <= target_role:
        return await ctx.send(f"❌ Cannot assign `{target_role.name}`. Ensure my bot role is higher in server settings.")

    if target_role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already has the **{target_role.name}** role.")

    await member.add_roles(target_role)
    await ctx.send(f"🎉 **PROMOTION**: {member.mention} has been promoted to **{target_role.name}** by {ctx.author.mention}!")

@bot.command(name="authority")
@is_admin_or_owner()
async def grant_authority(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Authority")
    if not role:
        return await ctx.send("❌ The `Authority` role does not exist. Run `.autorole_setup` first.")
    
    if role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already has the **Authority** role.")

    await member.add_roles(role)
    await ctx.send(f"✅ Successfully assigned **Authority** role to {member.mention}.")

@bot.command(name="assign")
@is_admin_or_owner()
async def assign_role(ctx, member: discord.Member, *, role: discord.Role):
    if ctx.guild.me.top_role <= role:
        return await ctx.send("❌ I cannot assign this role because it is higher than my highest role in the server hierarchy.")

    if role in member.roles:
        return await ctx.send(f"⚠️ {member.mention} already has the `{role.name}` role.")

    await member.add_roles(role)
    await ctx.send(f"✅ Assigned **{role.name}** to {member.mention}.")

@bot.command(name="revoke")
@is_admin_or_owner()
async def revoke_role(ctx, member: discord.Member, *, role: discord.Role):
    if role not in member.roles:
        return await ctx.send(f"⚠️ {member.mention} does not have the `{role.name}` role.")

    await member.remove_roles(role)
    await ctx.send(f"🗑️ Removed **{role.name}** from {member.mention}.")

@bot.command(name="addrole")
@is_admin_or_owner()
async def add_role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` was not found.")

    await member.add_roles(role)
    await ctx.send(f"✅ Assigned **{role.name}** to {member.mention}.")

@bot.command(name="removerole")
@is_admin_or_owner()
async def remove_role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` was not found.")

    await member.remove_roles(role)
    await ctx.send(f"✅ Removed **{role.name}** from {member.mention}.")

@bot.group(name="role", invoke_without_command=True)
@is_admin_or_owner()
async def role_group(ctx):
    await ctx.send("Use subcommands: `.role addall <Role>`, `.role removeall <Role>`, or `.role members <Role>`.")

@role_group.command(name="addall")
@is_admin_or_owner()
async def add_role_to_all(ctx, *, role: discord.Role):
    await ctx.send(f"Adding `{role.name}` to all non-bot members... Please wait.")
    count = 0
    for member in ctx.guild.members:
        if not member.bot and role not in member.roles:
            try:
                await member.add_roles(role)
                count += 1
            except discord.Forbidden:
                continue
    await ctx.send(f"Done! Added `{role.name}` to **{count}** members.")

@role_group.command(name="removeall")
@is_admin_or_owner()
async def remove_role_from_all(ctx, *, role: discord.Role):
    await ctx.send(f"Removing `{role.name}` from all members... Please wait.")
    count = 0
    for member in role.members:
        try:
            await member.remove_roles(role)
            count += 1
        except discord.Forbidden:
            continue
    await ctx.send(f"Done! Removed `{role.name}` from **{count}** members.")

@role_group.command(name="members")
@is_admin_or_higher()
async def list_role_members(ctx, *, role: discord.Role):
    members = [f"{m.name} ({m.mention})" for m in role.members if not m.bot]
    total = len(members)

    if total == 0:
        return await ctx.send(f"No human members currently have the `{role.name}` role.")

    member_list_str = "\n".join(members[:20])
    if total > 20:
        member_list_str += f"\n*...and {total - 20} more.*"

    embed = discord.Embed(
        title=f"Members with {role.name} ({total})",
        description=member_list_str,
        color=role.color
    )
    await ctx.send(embed=embed)

@bot.command(name="autorole_setup")
@is_admin_or_owner()
async def auto_role_setup(ctx):
    status_msg = await ctx.send("⚙️ **Configuring Auto-Roles and Tier Structure (Levels 1–60)...**")
    guild = ctx.guild

    for (min_lvl, max_lvl), tier_data in LEVEL_TIER_ROLES.items():
        await ensure_role_exists(guild, tier_data["name"], tier_data["color"])

    mod_role = discord.utils.get(guild.roles, name="Moderator")
    if not mod_role:
        await guild.create_role(name="Moderator", permissions=discord.Permissions(kick_members=True, manage_messages=True, moderate_members=True, mute_members=True), color=discord.Color.blue())

    auth_role = discord.utils.get(guild.roles, name="Authority")
    if not auth_role:
        await guild.create_role(name="Authority", permissions=discord.Permissions(kick_members=True, ban_members=True, manage_messages=True, moderate_members=True), color=discord.Color.dark_red())

    head_mod = discord.utils.get(guild.roles, name="Head Moderator")
    if not head_mod:
        await guild.create_role(name="Head Moderator", permissions=discord.Permissions(manage_channels=True, kick_members=True, ban_members=True, manage_messages=True, moderate_members=True, mute_members=True, deafen_members=True, move_members=True), color=discord.Color.gold())

    for role_name, color_obj in PRO_HEX_COLORS.items():
        await ensure_role_exists(guild, role_name, color_obj)

    await status_msg.edit(content="✅ **Setup Complete**: Level tier roles, administrative roles, and color choices are ready!")

@bot.command(name="createrole")
@is_admin_or_owner()
async def create_role(ctx, name: str, hex_color: str = "#99AAB5"):
    try:
        clean_hex = hex_color.lstrip("#")
        color = discord.Color(int(clean_hex, 16))
        role = await ctx.guild.create_role(name=name, color=color)
        await ctx.send(f"🎨 Created role **{role.name}** (`#{clean_hex}`).")
    except ValueError:
        await ctx.send("❌ Invalid Hex string. Example: `#FF0000`.")

@bot.command(name="deleterole")
@is_admin_or_owner()
async def delete_role(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` was not found.")
    await role.delete()
    await ctx.send(f"🗑️ Deleted role **{role_name}**.")

@bot.command(name="color")
async def set_color(ctx, *, color_name: str):
    matched_role_name = None
    for valid_color in PRO_HEX_COLORS.keys():
        if color_name.lower() in valid_color.lower():
            matched_role_name = valid_color
            break

    if not matched_role_name:
        return await ctx.send(f"❌ Invalid choice. Available options: {', '.join(PRO_HEX_COLORS.keys())}")

    role = discord.utils.get(ctx.guild.roles, name=matched_role_name)
    if not role:
        return await ctx.send(f"❌ Role `{matched_role_name}` doesn't exist on this server.")

    roles_to_remove = [r for r in ctx.author.roles if r.name in PRO_HEX_COLORS.keys()]
    if roles_to_remove:
        await ctx.author.remove_roles(*roles_to_remove)

    await ctx.author.add_roles(role)
    await ctx.send(f"🎨 Applied **{role.name}** color role to {ctx.author.mention}!")

# ==========================================
# LEVELING & LEVEL MANAGEMENT COMMANDS
# ==========================================
@bot.command(name="level")
async def check_level(ctx, member: discord.Member = None):
    target = member or ctx.author
    lvl = user_levels.get(target.id, 1)
    xp = user_xp.get(target.id, 0)
    tier_info = get_tier_info_for_level(lvl)
    
    if lvl >= MAX_LEVEL:
        await ctx.send(f"⭐ {target.display_name} is at max **Level {MAX_LEVEL}**! Tier: **{tier_info['name']}** ({xp} XP).")
    else:
        needed = get_xp_for_level(lvl)
        await ctx.send(f"📊 {target.display_name} is **Level {lvl}** | Tier: **{tier_info['name']}** ({xp} / {needed} XP).")

@bot.command(name="leaderboard")
async def show_leaderboard(ctx):
    sorted_users = sorted(user_levels.items(), key=lambda x: (x[1], user_xp.get(x[0], 0)), reverse=True)[:10]
    if not sorted_users:
        return await ctx.send("📋 No level data found yet.")

    embed = discord.Embed(
        title="🏆 Server Level Leaderboard",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    for idx, (uid, lvl) in enumerate(sorted_users, start=1):
        member = ctx.guild.get_member(uid)
        name = member.display_name if member else f"User ID: {uid}"
        xp = user_xp.get(uid, 0)
        tier = get_tier_info_for_level(lvl)["name"]
        embed.add_field(name=f"#{idx} {name}", value=f"Level {lvl} ({tier}) • {xp} XP", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="addxp")
@is_admin_or_higher()
async def give_xp(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ XP amount must be greater than 0.")
    await add_xp(member, amount, ctx.guild, ctx.channel)
    await ctx.send(f"✨ Awarded **{amount} XP** to {member.mention}.")

@bot.command(name="setlevel")
@is_admin_or_higher()
async def set_user_level(ctx, member: discord.Member, level: int):
    if level < 1 or level > MAX_LEVEL:
        return await ctx.send(f"❌ Level must be between **1 and {MAX_LEVEL}**.")
    
    user_levels[member.id] = level
    user_xp[member.id] = get_xp_for_level(level - 1) if level > 1 else 0
    await update_member_level_role(member, level)
    await save_data_to_channel(ctx.guild)
    await ctx.send(f"⚙️ Set {member.mention}'s level to **Level {level}**.")

# ==========================================
# CHANNEL & VC CONTROL COMMANDS
# ==========================================
@bot.command(name="lockdown")
@is_admin_or_higher()
async def lockdown_channel(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    overwrite = target_channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await target_channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔒 **Channel Locked**: Sending messages disabled in {target_channel.mention}.")

@bot.command(name="unlock")
@is_admin_or_higher()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    overwrite = target_channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None
    await target_channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(f"🔓 **Channel Unlocked**: Sending messages restored in {target_channel.mention}.")

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
async def voice_mute_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(mute=True)
    await ctx.send(f"🔇 Muted {member.mention} in Voice.")

@bot.command(name="vc_unmute")
@commands.has_permissions(mute_members=True)
async def voice_unmute_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(mute=False)
    await ctx.send(f"🔊 Unmuted {member.mention} in Voice.")

@bot.command(name="vc_deafen")
@commands.has_permissions(deafen_members=True)
async def voice_deafen_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(deafen=True)
    await ctx.send(f"🙉 Deafened {member.mention} in Voice.")

@bot.command(name="vc_undeafen")
@commands.has_permissions(deafen_members=True)
async def voice_undeafen_user(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.edit(deafen=False)
    await ctx.send(f"🎧 Undeafened {member.mention} in Voice.")

@bot.command(name="vc_move")
@commands.has_permissions(move_members=True)
async def voice_move_user(ctx, member: discord.Member, target_channel: discord.VoiceChannel):
    if not member.voice or not member.voice.channel:
        return await ctx.send(f"❌ {member.mention} is not in a voice channel.")
    await member.move_to(target_channel)
    await ctx.send(f"🚚 Relocated {member.mention} to **{target_channel.name}**.")

# ==========================================
# SYSTEM MANAGEMENT & UTILITY COMMANDS
# ==========================================
@bot.command(name="purge")
@is_admin_or_higher()
async def purge_messages(ctx, amount: int):
    if amount < 1 or amount > 100:
        return await ctx.send("❌ Choose between **1 and 100** messages.")

    deleted = await ctx.channel.purge(limit=amount + 1)
    confirm_msg = await ctx.send(f"🧹 Purged **{len(deleted) - 1}** messages.")
    await asyncio.sleep(3)
    await confirm_msg.delete()

@bot.command(name="synclevels")
@is_admin_or_higher()
async def sync_levels(ctx):
    announcement_channel = await get_or_create_announcement_channel(ctx.guild)
    synced_count = 0

    for member in ctx.guild.members:
        if not member.bot:
            if member.id not in user_levels:
                user_levels[member.id] = 1
                user_xp[member.id] = 0
            
            lvl = user_levels[member.id]
            await update_member_level_role(member, lvl)
            synced_count += 1

    msg = f"✅ Synchronized roles for **{synced_count} member(s)**."
    await ctx.send(msg)
    if announcement_channel and announcement_channel.id != ctx.channel.id:
        await announcement_channel.send(f"⚙️ **System Sync**: {msg}")
    await save_data_to_channel(ctx.guild)

@bot.command(name="savedata")
@is_admin_or_higher()
async def force_save_data(ctx):
    await save_data_to_channel(ctx.guild)
    await ctx.send("💾 Saved current state to `#bot-memory`.")

@bot.command(name="botcommands")
@is_admin_or_higher()
async def bot_commands(ctx):
    target_channel = await get_or_create_bot_commands_channel(ctx.guild)
    if target_channel and ctx.channel.id != target_channel.id:
        return await ctx.send(f"❌ Run command inside {target_channel.mention}.")

    embed = discord.Embed(
        title="📜 Server Management Command Reference",
        description="Comprehensive reference for all operational and administrative commands:",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(
        name="🎖️ Leveling & Member Commands",
        value=(
            "`.level [@user]` - View level & tier progress.\n"
            "`.leaderboard` - View top 10 ranked members.\n"
            "`.afk [reason]` - Set AFK status.\n"
            "`.bump` - Bump server (+200 XP).\n"
            "`.color <name>` - Equip hex color role.\n"
            "`.userinfo [@user]` - View member details.\n"
            "`.serverinfo` - Display server information."
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Administrative & Level Overrides",
        value=(
            "`.addxp @user <amount>` - Manual XP grant.\n"
            "`.setlevel @user <1-60>` - Force level assignment.\n"
            "`.synclevels` - Resync tier roles server-wide.\n"
            "`.savedata` - Force immediate memory sync.\n"
            "`.update <text>` - Publish system release update."
        ),
        inline=False
    )

    embed.add_field(
        name="🔒 Restricted Role Management (Admin/Owner Only)",
        value=(
            "`.promote @user <Role>` - Promote staff directly.\n"
            "`.authority @user` - Grant Authority role.\n"
            "`.assign @user <Role>` - Assign any server role.\n"
            "`.revoke @user <Role>` - Revoke any server role.\n"
            "`.addrole @user <Role>` - Manual role assignment.\n"
            "`.removerole @user <Role>` - Manual role removal.\n"
            "`.role addall <Role>` - Give role to all human members.\n"
            "`.role removeall <Role>` - Strip role from all members.\n"
            "`.autorole_setup` - Setup level and staff roles.\n"
            "`.createrole <Name> <#Hex>` - Custom color role.\n"
            "`.deleterole <Role>` - Delete custom role."
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation Engine",
        value=(
            "`.warn @user [reason]` - Issue warning (3 = Auto Ban).\n"
            "`.clearwarns @user` - Reset member warning count.\n"
            "`.mute @user [reason]` - Timeout member.\n"
            "`.unmute @user` - Remove active timeout.\n"
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
            "`.vc_lock <#vc>` / `.vc_unlock <#vc>` - Voice access.\n"
            "`.vc_mute @user` / `.vc_unmute @user` - Server mute in VC.\n"
            "`.vc_deafen @user` / `.vc_undeafen @user` - Server deafen.\n"
            "`.vc_move @user <#vc>` - Move user across voice channels."
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
        return await ctx.send("❌ Channel `#bot-commands` not found.")

    update_embed = discord.Embed(
        title="⚙️ Bot System Update",
        description=f"{update_details}\n\n*Maintained by {BOT_CREATOR_USERNAME} ({BOT_CREATOR_REAL_NAME}) | {BOT_COMPANY_NAME}*",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await target_channel.send(embed=update_embed)
    await ctx.send(f"✅ Published update notes in {target_channel.mention}.")

@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"💤 {ctx.author.mention} is now AFK: **{reason}**")
    await save_data_to_channel(ctx.guild)

@bot.command(name="about")
async def about_bot(ctx):
    embed = discord.Embed(title="🤖 System Credits", color=discord.Color.purple())
    embed.add_field(name="Username", value=BOT_CREATOR_USERNAME, inline=True)
    embed.add_field(name="Developer", value=BOT_CREATOR_REAL_NAME, inline=True)
    embed.add_field(name="Company", value=BOT_COMPANY_NAME, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="bump")
async def bump(ctx):
    bump_channel = await get_or_create_bump_channel(ctx.guild)
    if bump_channel and ctx.channel.id != bump_channel.id:
        return await ctx.send(f"❌ `.bump` is restricted to {bump_channel.mention}.")

    global last_bump_time
    current_time = asyncio.get_event_loop().time()
    time_passed = current_time - last_bump_time

    if last_bump_time != 0 and time_passed < bump_cooldown_seconds:
        remaining = int(bump_cooldown_seconds - time_passed)
        m, s = divmod(remaining, 60)
        h, m = divmod(m, 60)
        return await ctx.send(f"❌ **Cooldown**: Try again in **{h}h {m}s**.")

    last_bump_time = current_time
    await add_xp(ctx.author, 200, ctx.guild, ctx.channel)
    cute_line = random.choice(CUTE_BUMP_MESSAGES)
    await ctx.send(f"Thank you for bumping, {ctx.author.mention}! (**+200 XP**)\n*{cute_line}*")

@bot.command(name="userinfo")
async def user_info(ctx, member: discord.Member = None):
    target = member or ctx.author
    lvl = user_levels.get(target.id, 1)
    xp = user_xp.get(target.id, 0)
    warns = user_warnings.get(target.id, 0)
    mutes = user_mute_counts.get(target.id, 0)
    tier = get_tier_info_for_level(lvl)["name"]

    embed = discord.Embed(
        title=f"👤 User Profile - {target.display_name}",
        color=target.color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Account ID", value=target.id, inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Progression", value=f"Level {lvl} ({tier})\n{xp} Total XP", inline=False)
    embed.add_field(name="Moderation History", value=f"Warnings: {warns}/3\nTotal Timeouts: {mutes}", inline=False)
    
    roles = [r.mention for r in target.roles if r.name != "@everyone"]
    embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def server_info(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"🏰 {guild.name} Server Statistics",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="Server Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Total Members", value=guild.member_count, inline=True)
    embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=True)
    embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=True)
    embed.add_field(name="Roles Count", value=len(guild.roles), inline=True)
    embed.add_field(name="Creation Date", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

# ==========================================
# MODERATION ENGINE COMMANDS
# ==========================================
@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.bot:
        return await ctx.send("Cannot mute bots.")

    current_mutes = user_mute_counts.get(member.id, 0) + 1
    user_mute_counts[member.id] = current_mutes

    durations = {1: (datetime.timedelta(hours=1), "1 hour"), 
                 2: (datetime.timedelta(hours=6), "6 hours")}
    duration, duration_label = durations.get(current_mutes, (datetime.timedelta(hours=12), "12 hours"))

    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(f"🔇 {member.mention} muted for **{duration_label}** (Offense #{current_mutes}). Reason: {reason}")
        await save_data_to_channel(ctx.guild)
    except discord.Forbidden:
        await ctx.send("❌ Missing permissions to timeout this user.")

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await ctx.send(f"🔊 {member.mention} unmuted.")
    except discord.Forbidden:
        await ctx.send("❌ Missing permissions to unmute this user.")

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.bot:
        return await ctx.send("Cannot warn bots.")

    current_warns = user_warnings.get(member.id, 0) + 1
    user_warnings[member.id] = current_warns

    await ctx.send(f"⚠️ {member.mention} warned! **({current_warns}/3)**. Reason: {reason}")

    if current_warns >= 3:
        user_warnings[member.id] = 0
        await member.ban(reason=f"Reached 3 warnings. Reason: {reason}")
        await ctx.send(f"🔨 **AUTOMATIC BAN**: {member.mention} reached 3 warnings.")

    await save_data_to_channel(ctx.guild)

@bot.command(name="clearwarns")
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    user_warnings[member.id] = 0
    await ctx.send(f"✅ Cleared warnings for {member.mention}.")
    await save_data_to_channel(ctx.guild)

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} kicked. Reason: {reason}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} banned. Reason: {reason}")

bot.run(os.getenv("DISCORD_TOKEN"))
