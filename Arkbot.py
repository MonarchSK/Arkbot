import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import datetime
import json
import io
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

def is_allowed_channel(channel):
    if not isinstance(channel, discord.TextChannel):
        return False
    if channel.name.lower() == "playground":
        return False
    if channel.category and "music" in channel.category.name.lower():
        return False
    return True

SERVER_BLUEPRINT = [
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "supreme-logs", "type": "text", "restricted": True},
            {"name": "admin-chat", "type": "text", "restricted": True},
            {"name": "bot-config", "type": "text", "restricted": True}
        ]
    },
    {
        "category": "Info 🍸",
        "channels": [
            {"name": "welcome", "type": "text", "restricted": False},
            {"name": "rules", "type": "text", "restricted": False},
            {"name": "announcements", "type": "text", "restricted": False},
            {"name": "boosters", "type": "text", "restricted": False},
            {"name": "bot-commands", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "team-chat", "type": "text", "restricted": True},
            {"name": "staff-logs", "type": "text", "restricted": True},
            {"name": "support-tickets", "type": "text", "restricted": True}
        ]
    },
    {
        "category": "Events 🎊",
        "channels": [
            {"name": "giveaways", "type": "text", "restricted": False},
            {"name": "event-chat", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Chill Area 🍹",
        "channels": [
            {"name": "general-chat", "type": "text", "restricted": False},
            {"name": "bot-spam", "type": "text", "restricted": False},
            {"name": "chat-ai", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Media 📷",
        "channels": [
            {"name": "media-feed", "type": "text", "restricted": False},
            {"name": "colours", "type": "text", "restricted": False},
            {"name": "identity-roles", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Fun Area 🎮",
        "channels": [
            {"name": "polls", "type": "text", "restricted": False},
            {"name": "confessions", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Hobbies 🎲",
        "channels": [
            {"name": "roblox-elites", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Voice Chats 🔊",
        "channels": [
            {"name": "Lounge 1", "type": "voice", "restricted": False},
            {"name": "Lounge 2", "type": "voice", "restricted": False},
            {"name": "VIP Room", "type": "voice", "restricted": False, "user_limit": 4}
        ]
    },
    {
        "category": "Music 🎵",
        "channels": [
            {"name": "Music Lounge", "type": "voice", "restricted": False}
        ]
    }
]

class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(label="Why do you want to join?", style=discord.TextStyle.paragraph, placeholder="Tell us a bit about yourself...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        mutual_guilds = interaction.user.mutual_guilds
        guild = mutual_guilds[0] if mutual_guilds else None

        if guild:
            role = discord.utils.get(guild.roles, name="Member")
            member = guild.get_member(interaction.user.id)
            if role and member:
                await member.add_roles(role)
            
            log_channel = discord.utils.get(guild.text_channels, name="staff-logs") or discord.utils.get(guild.text_channels, name="bot-commands")
            if log_channel:
                embed = discord.Embed(title="New Member Verified", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                embed.add_field(name="User", value=interaction.user.mention, inline=False)
                embed.add_field(name="Real Full Name", value=self.real_full_name.value, inline=True)
                embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
                embed.add_field(name="Date of Birth", value=self.dob.value, inline=True)
                embed.add_field(name="Reason to Join", value=self.reason.value, inline=False)
                await log_channel.send(embed=embed)

        await interaction.response.send_message("Verification complete! You now have access to Chill-Verse.", ephemeral=True)

class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept_rules")
    async def accept(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VerificationModal())

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, custom_id="decline_rules")
    async def decline(self, interaction: discord.Interaction, button: Button):
        mutual_guilds = interaction.user.mutual_guilds
        guild = mutual_guilds[0] if mutual_guilds else None
        if guild:
            try:
                await guild.ban(interaction.user, reason="Declined server terms and rules.")
                await interaction.response.send_message("You have been banned for declining the rules.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Error: Missing permission to ban.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse operational.")
    if not hourly_backup_task.is_running():
        hourly_backup_task.start()

@tasks.loop(hours=1.0)
async def hourly_backup_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        backup_channel = discord.utils.get(guild.text_channels, name="backup")
        if not backup_channel:
            continue
        backup_data = {
            "server_name": guild.name,
            "roles": [{"name": role.name, "permissions": role.permissions.value} for role in guild.roles],
            "text_channels": [{"name": channel.name, "category": str(channel.category)} for channel in guild.text_channels]
        }
        file = discord.File(io.BytesIO(json.dumps(backup_data, indent=4).encode('utf-8')), filename="server_backup.json")
        try:
            await backup_channel.send(content="🔒 **Automated Hourly Backup**", file=file)
        except Exception:
            pass

@bot.event
async def on_member_join(member):
    embed = discord.Embed(
        title="Welcome to Chill-Verse! 🎉", 
        description=(
            "**Basic Server Rules:**\n"
            "1. Be respectful, kind, and inclusive to everyone.\n"
            "2. No bullying, hate speech, spam, or toxic behavior.\n"
            "3. Keep conversations teen and family-friendly.\n"
            "4. Follow Discord's Terms of Service at all times.\n\n"
            "To unlock server access, click **Accept** to submit your details via pop-up form, or **Decline** to exit via immediate ban."
        ),
        color=discord.Color.purple()
    )
    try:
        await member.send(embed=embed, view=RulesView())
    except discord.Forbidden:
        channel = discord.utils.get(member.guild.text_channels, name="welcome")
        if channel:
            await channel.send(content=f"{member.mention} (Open your DMs!)", embed=embed, view=RulesView())

@bot.event
async def on_message(message):
    if message.author.bot or not is_allowed_channel(message.channel):
        return
    await bot.process_commands(message)

@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    guild = ctx.guild
    roles = {
        "Supreme Leader": discord.Permissions(administrator=True),
        "Highness": discord.Permissions(administrator=True),
        "Authority": discord.Permissions(ban_members=True, kick_members=True, manage_channels=True, manage_roles=True),
        "Head Moderator": discord.Permissions(ban_members=True, kick_members=True, moderate_members=True, manage_messages=True),
        "Moderator": discord.Permissions(kick_members=True, moderate_members=True, manage_messages=True),
        "Trial Mod": discord.Permissions(moderate_members=True, manage_messages=True),
        "Chill-Verse Team": discord.Permissions(view_channel=True, send_messages=True, read_message_history=True),
        "Member": discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)
    }
    
    created_count = 0
    for name, perms in roles.items():
        if not discord.utils.get(guild.roles, name=name):
            await guild.create_role(name=name, permissions=perms, reason="Chill-Verse hierarchy setup")
            created_count += 1
            
    await ctx.send(f"Hierarchy configuration complete! Created **{created_count}** new roles.")

@bot.command(name="delete_roles")
@commands.has_permissions(administrator=True)
async def delete_roles(ctx):
    guild = ctx.guild
    deleted_count = 0
    skipped_count = 0

    await ctx.send("🧹 Starting safe bulk deletion of server roles...")

    for role in list(guild.roles):
        if role.is_default() or role.managed or role >= guild.me.top_role:
            skipped_count += 1
            continue
        try:
            await role.delete(reason=f"Bulk delete requested by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.35)
        except Exception:
            skipped_count += 1

    await ctx.send(f"✅ Role cleanup complete! Successfully deleted **{deleted_count}** roles. Skipped/Protected: **{skipped_count}**.")

@bot.command(name="delete_channels")
@commands.has_permissions(administrator=True)
async def delete_channels(ctx, *channels: discord.abc.GuildChannel):
    """Deletes multiple specified channels at the same time. Usage: .delete_channels #channel1 #channel2"""
    if not channels:
        await ctx.send("⚠️ Please mention the channels you want to delete. Example: `.delete_channels #channel1 #channel2`", delete_after=10)
        return

    deleted_count = 0
    failed_count = 0

    await ctx.send(f"🗑️ Attempting to delete {len(channels)} channel(s)...")

    for channel in channels:
        try:
            await channel.delete(reason=f"Batch manual deletion requested by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.35) # Avoid rate limits
        except Exception:
            failed_count += 1

    await ctx.send(f"✅ Channel deletion complete! Successfully deleted **{deleted_count}** channel(s). Failed: **{failed_count}**.")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def setup_channels(ctx):
    guild = ctx.guild
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]

    for cat_data in SERVER_BLUEPRINT:
        cat_name = cat_data["category"]
        category = discord.utils.get(guild.categories, name=cat_name)
        
        if not category:
            category = await guild.create_category(name=cat_name)

        for ch_info in cat_data["channels"]:
            ch_name = ch_info["name"]
            ch_type = ch_info["type"]
            is_restricted = ch_info.get("restricted", False)
            user_lim = ch_info.get("user_limit", 0)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False if is_restricted else True)
            }
            if is_restricted:
                for rname in admin_roles:
                    r = discord.utils.get(guild.roles, name=rname)
                    if r:
                        overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            if ch_type == "text":
                existing = discord.utils.get(category.text_channels, name=ch_name)
                if not existing:
                    await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites)
            else:
                existing = discord.utils.get(category.voice_channels, name=ch_name)
                if not existing:
                    await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim, overwrites=overwrites)

    memory_ch = discord.utils.get(guild.text_channels, name="bot-memory")
    if not memory_ch:
        memory_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        for rname in admin_roles:
            r = discord.utils.get(guild.roles, name=rname)
            if r:
                memory_overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)
        await guild.create_text_channel(name="bot-memory", overwrites=memory_overwrites, reason="State persistence storage")

    await ctx.send("✅ Chill-Verse channels deployed successfully with full staff visibility across administrative and public spaces!")

@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def backup(ctx):
    guild = ctx.guild
    ch = discord.utils.get(guild.text_channels, name="backup")
    if not ch:
        return await ctx.send("`#backup` channel not found.")
    data = {"server": guild.name, "roles": [r.name for r in guild.roles]}
    file = discord.File(io.BytesIO(json.dumps(data, indent=4).encode('utf-8')), filename="server_backup.json")
    await ch.send(file=file)
    await ctx.send("Backup complete!", delete_after=5)

bot.run("YOUR_BOT_TOKEN_HERE")
