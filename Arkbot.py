import os
import asyncio
import discord
from discord.ext import commands

# Bot Setup & Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True

bot = commands.Bot(command_prefix=".", intents=intents)

# Configuration
NEW_MEMBER_ROLE = "Newbie"
DISBOARD_BOT_ID = 302050872383422240
ANNOUNCEMENT_CHANNEL_ID = 0  # Replace 0 with your announcement/broadcast channel ID

# Storage Dictionaries
afk_users = {}
afk_mentions = {}
user_xp = {}
user_levels = {}
last_bump_time = 0

# List of managed "Pro Hex" color roles (Aesthetics only, strictly color-only)
PRO_HEX_COLORS = [
    "Pro Hex Red",
    "Pro Hex Green",
    "Pro Hex Blue",
    "Pro Hex Pink",
    "Pro Hex Yellow",
    "Pro Hex Orange",
]

BASE_XP_LEVEL_1 = 500  # 500 XP required to reach Level 2, doubles every level up to max level 60
MAX_LEVEL = 60

# Helper Functions
def get_xp_for_level(level):
    """Calculates total XP needed for the current level (caps at level 60)."""
    if level >= MAX_LEVEL:
        return BASE_XP_LEVEL_1 * (2 ** (MAX_LEVEL - 2))
    return BASE_XP_LEVEL_1 * (2 ** (level - 1))

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
        
        target_channel = guild.get_channel(ANNOUNCEMENT_CHANNEL_ID) if ANNOUNCEMENT_CHANNEL_ID else fallback_channel
        if target_channel:
            await target_channel.send(
                f"🎉 **[LEVEL UP]** {user.mention} has leveled up to **Level {new_level}**!"
            )

# Events
@bot.event
async def on_member_join(member):
    user_levels[member.id] = 1
    user_xp[member.id] = 0

    newbie_role = discord.utils.get(member.guild.roles, name=NEW_MEMBER_ROLE)
    if newbie_role:
        await member.add_roles(newbie_role)

    target_channel = member.guild.get_channel(ANNOUNCEMENT_CHANNEL_ID) if ANNOUNCEMENT_CHANNEL_ID else (member.guild.system_channel or (member.guild.text_channels[0] if member.guild.text_channels else None))
    if target_channel:
        await target_channel.send(
            f"Welcome to the server, {member.mention}! You have automatically received the **{NEW_MEMBER_ROLE}** role and are starting at **Level 1**."
        )

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or message.author.bot or not message.guild:
        return

    # Award XP for active messaging
    await add_xp(message.author, 15, message.guild, message.channel)

    # Detect Disboard Bump Success Automatically
    if message.author.id == DISBOARD_BOT_ID and message.embeds:
        for embed in message.embeds:
            description = embed.description or ""
            if "Bump done" in description:
                global last_bump_time
                last_bump_time = asyncio.get_event_loop().time()
                bumper = message.interaction.user if message.interaction else None

                if bumper:
                    await add_xp(bumper, 200, message.guild, message.channel)
                    await message.channel.send(
                        f"Thank you for bumping, {bumper.mention}! You earned 200 XP."
                    )
                else:
                    await message.channel.send("Thank you for bumping! You earned 200 XP.")

                await message.channel.send("I will notify everyone in this channel to bump again in 2 hours!")
                await asyncio.sleep(7200)
                await message.channel.send("⏰ **Time to bump!** Use `.bump` to boost the server again!")

    # AFK Mention Notification Collection
    if message.mentions:
        for mention in message.mentions:
            if mention.id in afk_users:
                reason = afk_users[mention.id]
                if mention.id not in afk_mentions:
                    afk_mentions[mention.id] = []
                afk_mentions[mention.id].append(f"From {message.author.display_name} in {message.channel.mention}: {message.content}")
                
                await message.channel.send(f"{mention.display_name} is currently AFK: {reason}")

    # Auto-Remove AFK Status & Deliver Missed Messages
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        welcome_msg = f"Welcome back, {message.author.display_name}! Your AFK status has been removed."
        
        if message.author.id in afk_mentions and afk_mentions[message.author.id]:
            missed = "\n".join(afk_mentions[message.author.id][-5:])
            welcome_msg += f"\n\n📬 **While you were AFK, you received these messages:**\n{missed}"
            del afk_mentions[message.author.id]

        await message.channel.send(welcome_msg)

    await bot.process_commands(message)

# Commands
@bot.command()
async def bump(ctx):
    global last_bump_time
    current_time = asyncio.get_event_loop().time()
    cooldown = 7200  # 2 hours in seconds
    time_passed = current_time - last_bump_time

    if time_passed < cooldown and last_bump_time != 0:
        remaining_seconds = int(cooldown - time_passed)
        minutes, seconds = divmod(remaining_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        await ctx.send(f"Please wait **{hours}h {minutes}m {seconds}s** before bumping again.")
        return

    # Update cooldown timer and add XP
    last_bump_time = current_time
    await add_xp(ctx.author, 200, ctx.guild, ctx.channel)
    
    # Send thank you note and start the 2-hour reminder timer
    await ctx.send(f"Thank you for bumping, {ctx.author.mention}! (+200 XP)\nI will notify everyone in this channel to bump again in 2 hours!")
    
    # Asynchronous wait for 2 hours (7200 seconds) then alert the channel
    await asyncio.sleep(7200)
    await ctx.send("⏰ **Time to bump!** Use `.bump` to boost the server again!")

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention}, I set your AFK status to: {reason}")

@bot.command()
async def color(ctx, *, color_name: str):
    """Grants a Pro Hex color role for pure aesthetics without any permissions."""
    matched_role_name = None
    for valid_color in PRO_HEX_COLORS:
        if color_name.lower() in valid_color.lower():
            matched_role_name = valid_color
            break

    if not matched_role_name:
        available = ", ".join(PRO_HEX_COLORS)
        await ctx.send(f"Invalid color choice. Available options: {available}")
        return

    role = discord.utils.get(ctx.guild.roles, name=matched_role_name)
    if not role:
        await ctx.send(f"The role `{matched_role_name}` does not exist on this server yet.")
        return

    roles_to_remove = [r for r in ctx.author.roles if r.name in PRO_HEX_COLORS]
    if roles_to_remove:
        await ctx.author.remove_roles(*roles_to_remove)

    await ctx.author.add_roles(role)
    await ctx.send(f"Successfully applied the {role.name} color role to you!")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} has been kicked. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} has been banned by {ctx.author.mention}. Violation Reason: **{reason}**")

@bot.command()
async def level(ctx, member: discord.Member = None):
    target = member or ctx.author
    lvl = user_levels.get(target.id, 1)
    xp = user_xp.get(target.id, 0)
    
    if lvl >= MAX_LEVEL:
        await ctx.send(f"{target.display_name} has reached the maximum **Level {MAX_LEVEL}**! ({xp} total XP).")
    else:
        needed = get_xp_for_level(lvl)
        await ctx.send(f"{target.display_name} is Level **{lvl}** ({xp} / {needed} XP).")

bot.run(os.getenv("DISCORD_TOKEN"))
