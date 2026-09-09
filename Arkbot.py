import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import datetime
import json
import io
import asyncio
import os

# ==============================================================================
# BOT SETUP & INTENTS
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)
bot.remove_command('help') 

def is_allowed_channel(channel):
    """Prevents commands from working in Playground or Music categories."""
    if not isinstance(channel, discord.TextChannel):
        return False
    if "playground" in channel.name.lower():
        return False
    if channel.category and "music" in channel.category.name.lower():
        return False
    return True

# ==============================================================================
# CUSTOM BLUEPRINT CONFIGURATION (FROM SCREENSHOTS)
# ==============================================================================
SERVER_BLUEPRINT = [
    {
        "category": "Welcome",
        "channels": [
            {"name": "server-rules", "type": "text", "restricted": False},
            {"name": "👋・welcome", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "team-news", "type": "text", "restricted": True},
            {"name": "🛡️・team-rules", "type": "text", "restricted": True},
            {"name": "💬・team-chat", "type": "text", "restricted": True},
            {"name": "⏰・bump", "type": "text", "restricted": True},
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
            {"name": "📢・level-announcements", "type": "text", "restricted": False},
            {"name": "🎫・tickets", "type": "text", "restricted": False},
            {"name": "🎨・colours", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "💼・bot-commands", "type": "text", "restricted": True},
            {"name": "🩸・bot-errors", "type": "text", "restricted": True}
        ]
    }
]

# ==============================================================================
# AUTO-PERMISSION & ABSOLUTE TEAM ACCESS ENFORCEMENT
# ==============================================================================
async def auto_configure_channel(channel):
    """Ensures Team roles are explicitly added to ALL channels, while members/everyone are restricted to public channels."""
    if isinstance(channel, discord.CategoryChannel):
        return
        
    guild = channel.guild
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]
    
    cat_name = channel.category.name.lower() if channel.category else ""
    ch_name = channel.name.lower()
    
    # Determine if the channel is restricted from general members
    is_restricted = False
    if "admin" in cat_name or "team" in cat_name or "admin" in ch_name or "staff" in ch_name or "bot" in ch_name or "ticket" in ch_name:
        is_restricted = True
        
    # Set public/restricted access for standard members & @everyone
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False if is_restricted else True)
    }
    
    # EXPLICITLY add every Team role to EVERY channel in the server
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
    try:
        await channel.edit(overwrites=overwrites, reason="Ironclad Team Access & Public Member Restriction Sync")
    except Exception:
        pass

# ==============================================================================
# UI COMPONENTS (MODALS, TICKETS & BUTTONS)
# ==============================================================================
class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(label="Why do you want to join?", style=discord.TextStyle.paragraph, placeholder="Tell us a bit about yourself...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild:
            role = discord.utils.get(guild.roles, name="Member")
            if role:
                await interaction.user.add_roles(role)
            
            log_channel = discord.utils.get(guild.text_channels, name="💼・bot-commands")
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
        try:
            await interaction.guild.ban(interaction.user, reason="Declined server terms and rules.")
            await interaction.response.send_message("You have been banned for declining the rules.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Error: Missing permission to ban.", ephemeral=True)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 This ticket will be deleted in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="User closed ticket.")

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, custom_id="open_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Team <3")
        
        if not category:
            return await interaction.response.send_message("Error: Team category not found. Run `.setup_channels` first.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        
        staff_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator"]
        for rname in staff_roles:
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_ch = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {interaction.user.name}"
        )
        
        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {interaction.user.mention}! Please describe your issue or application here. A staff member will be with you shortly.",
            color=discord.Color.blue()
        )
        
        await ticket_ch.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created successfully: {ticket_ch.mention}", ephemeral=True)

# ==============================================================================
# EVENTS & TASKS
# ==============================================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse operational.")
    
    bot.add_view(RulesView())
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    
    if not hourly_backup_task.is_running():
        hourly_backup_task.start()

@bot.event
async def on_guild_channel_create(channel):
    """Automatically secures newly created channels in real-time."""
    await auto_configure_channel(channel)

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"⚠️ **DEBUG ERROR:** {error}")
    print(f"Command Error: {error}")

@tasks.loop(hours=1.0)
async def hourly_backup_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        backup_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
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
        channel = discord.utils.get(member.guild.text_channels, name="👋・welcome")
        if channel:
            await channel.send(content=f"{member.mention} (Open your DMs!)", embed=embed, view=RulesView())

@bot.event
async def on_message(message):
    if message.author.bot or not is_allowed_channel(message.channel):
        return
    await bot.process_commands(message)

# ==============================================================================
# MODERATION & COMMUNITY COMMANDS
# ==============================================================================
@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** Bot is online. Latency: `{latency}ms`")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    if amount > 100:
        return await ctx.send("⚠️ You can only purge up to 100 messages at a time.", delete_after=5)
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Successfully cleared **{len(deleted)}** messages.", delete_after=4)

# ==============================================================================
# ADMINISTRATIVE ARCHITECTURE COMMANDS
# ==============================================================================
@bot.command(name="setup_help")
@commands.has_permissions(administrator=True)
async def setup_help(ctx):
    ch = discord.utils.get(ctx.guild.text_channels, name="💼・bot-commands")
    if not ch:
        return await ctx.send("⚠️ Cannot find `💼・bot-commands`. Please run `.setup_channels` first.")
        
    embed = discord.Embed(
        title="🤖 Chill-Verse Master Command List",
        description="Here is the complete operational suite for managing your server architecture and security.",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🛠️ Admin & Architecture Commands", 
        value=(
            "`.setup_roles` — Auto-generates the complete 31-role hierarchy.\n"
            "`.nuke_roles` — ☢️ Wipes all custom roles for a fresh start.\n"
            "`.setup_channels` — Deploys the blueprint with absolute team access & public restrictions.\n"
            "`.sync_and_permit` — 🛡️ Syncs auto-permissions and explicitly grants a role access to all channels.\n"
            "`.nuke_channels` — ☢️ Wipes every channel/category (except command room).\n"
            "`.add_channel <type> <name>` — Creates a text, voice, or forum channel on the fly.\n"
            "`.delete_channels <#tags>` — Deletes specific tagged channels.\n"
            "`.setup_tickets` — Drops the interactive support ticket panel.\n"
            "`.setup_help` — Posts this master command sheet.\n"
            "`.backup` — Forces an immediate server JSON backup."
        ), 
        inline=False
    )

    embed.add_field(
        name="🔐 Channel Permission & Security Commands", 
        value=(
            "`.lock` / `.unlock` — Freezes or unfreezes chat in the current room.\n"
            "`.hide` / `.show` — Makes the current channel invisible or visible to members.\n"
            "`.permit <role/user>` — Grants a specific role or user access to a room.\n"
            "`.revoke <role/user>` — Removes a specific role or user's access from a room.\n"
            "`.permit_all <role/user>` — Gives a role/user access to *every* channel at once.\n"
            "`.revoke_all <role/user>` — Locks a role/user out of *every* channel at once.\n"
            "`.edit_role <role> <permission> <True/False>` — Changes core server powers."
        ), 
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Moderation & General Commands", 
        value=(
            "`.purge <number>` — Instantly bulk-deletes up to 100 messages.\n"
            "`.ping` — Checks bot latency and server gateway connection."
        ), 
        inline=False
    )
    
    embed.set_footer(text="Chill-Verse System Architecture • Prefix: .")
    
    await ch.send(embed=embed)
    await ctx.send("✅ Master command sheet successfully updated and posted to `💼・bot-commands`!")

@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    ch = discord.utils.get(ctx.guild.text_channels, name="🎫・tickets")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🎫・tickets`. Please run `.setup_channels` first.")
        
    embed = discord.Embed(
        title="🎫 Chill-Verse Support & Applications",
        description="Need help from staff, want to report an issue, or apply for a team role?\n\nClick the button below to open a private ticket.",
        color=discord.Color.blue()
    )
    await ch.send(embed=embed, view=TicketView())
    await ctx.send("✅ Ticket system deployed to `🎫・tickets`!")

@bot.command(name="add_channel")
@commands.has_permissions(administrator=True)
async def add_channel(ctx, channel_type: str, *, channel_name: str):
    """Creates a new text, voice, or forum channel on the fly."""
    channel_type = channel_type.lower()
    category = ctx.channel.category
    
    try:
        if channel_type in ["text", "t"]:
            new_channel = await ctx.guild.create_text_channel(name=channel_name, category=category)
            await ctx.send(f"✅ Created text channel {new_channel.mention} in category **{category.name if category else 'None'}**!")
        elif channel_type in ["voice", "v"]:
            new_channel = await ctx.guild.create_voice_channel(name=channel_name, category=category)
            await ctx.send(f"✅ Created voice channel `{new_channel.name}` in category **{category.name if category else 'None'}**!")
        elif channel_type in ["forum", "f"]:
            try:
                new_channel = await ctx.guild.create_forum_channel(name=channel_name, category=category)
                await ctx.send(f"✅ Created forum channel {new_channel.mention} in category **{category.name if category else 'None'}**!")
            except Exception:
                await ctx.send("⚠️ Could not create a forum (ensure Community feature is enabled).")
        else:
            await ctx.send("⚠️ Invalid type! Use `text`, `voice`, or `forum`.\n**Example:** `.add_channel text announcements-2`")
    except Exception as e:
        await ctx.send(f"⚠️ **Error creating channel:** {e}")

# ==============================================================================
# PERMISSION & SECURITY SYSTEM COMMANDS
# ==============================================================================
@bot.command(name="sync_and_permit")
@commands.has_permissions(administrator=True)
async def sync_and_permit(ctx, target: discord.Role):
    """Auto-syncs channel security and explicitly grants a specified role access to all channels."""
    await ctx.send(f"🔄 **Master Sync:** Enforcing team access rules and granting {target.mention} access to all channels...")
    count = 0
    
    for channel in ctx.guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue
        await auto_configure_channel(channel)
        
        try:
            await channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
            count += 1
            await asyncio.sleep(0.2)
        except Exception:
            pass
            
    await ctx.send(f"✅ **Master Sync Complete:** Channels secured for members, and {target.mention} explicitly granted access to **{count}** channels!")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 **Channel Locked:** Standard members can no longer send messages here.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send("🔓 **Channel Unlocked:** Standard members can now send messages here.")

@bot.command(name="hide")
@commands.has_permissions(manage_channels=True)
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("👻 **Channel Hidden:** This channel is now invisible to standard members.")

@bot.command(name="show")
@commands.has_permissions(manage_channels=True)
async def show(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ **Channel Visible:** Standard members can now see this channel.")

@bot.command(name="permit")
@commands.has_permissions(manage_channels=True)
async def permit(ctx, target: discord.Role | discord.Member):
    await ctx.channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
    await ctx.send(f"✅ **Access Granted:** {target.mention} can now view and type in this channel.")

@bot.command(name="revoke")
@commands.has_permissions(manage_channels=True)
async def revoke(ctx, target: discord.Role | discord.Member):
    await ctx.channel.set_permissions(target, view_channel=False, send_messages=False)
    await ctx.send(f"❌ **Access Revoked:** {target.mention} has been removed from this channel.")

@bot.command(name="permit_all")
@commands.has_permissions(administrator=True)
async def permit_all(ctx, target: discord.Role | discord.Member):
    await ctx.send(f"🔄 **Global Sync:** Granting {target.mention} access to all channels... Please wait.")
    count = 0
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
            count += 1
            await asyncio.sleep(0.2)
        except Exception:
            pass
    await ctx.send(f"✅ **Global Access Granted:** {target.mention} can now view and type in **{count}** channels!")

@bot.command(name="revoke_all")
@commands.has_permissions(administrator=True)
async def revoke_all(ctx, target: discord.Role | discord.Member):
    await ctx.send(f"🔄 **Global Sync:** Revoking {target.mention}'s access from all channels... Please wait.")
    count = 0
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(target, view_channel=False, send_messages=False)
            count += 1
            await asyncio.sleep(0.2)
        except Exception:
            pass
    await ctx.send(f"❌ **Global Access Revoked:** {target.mention} has been completely locked out of **{count}** channels.")

@bot.command(name="edit_role")
@commands.has_permissions(administrator=True)
async def edit_role(ctx, role: discord.Role, permission_name: str, value: bool):
    if role >= ctx.guild.me.top_role:
        return await ctx.send("⚠️ **Error:** I cannot modify a role higher than my own bot role!")
    permission_name = permission_name.lower()
    if not hasattr(discord.Permissions, permission_name):
        return await ctx.send(f"⚠️ **Error:** `{permission_name}` is not a valid Discord permission name.")
    perms = role.permissions
    setattr(perms, permission_name, value)
    try:
        await role.edit(permissions=perms, reason=f"Permission changed by {ctx.author}")
        status = "🟢 ENABLED" if value else "🔴 DISABLED"
        await ctx.send(f"✅ Successfully updated **{role.name}**!\n{status}: `{permission_name}`")
    except Exception as e:
        await ctx.send(f"⚠️ **Error updating role:** {e}")

# ==============================================================================
# NUKE & REBUILD ROLES
# ==============================================================================
@bot.command(name="nuke_roles")
@commands.has_permissions(administrator=True)
async def nuke_roles(ctx):
    await ctx.send("☢️ **ROLE NUKE INITIATED:** Wiping all custom server roles. Please wait...")
    deleted_count = 0
    skipped_count = 0

    for role in list(ctx.guild.roles):
        if role.is_default() or role.managed or role >= ctx.guild.me.top_role:
            skipped_count += 1
            continue
        try:
            await role.delete(reason=f"Role Nuke initiated by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.35)
        except Exception as e:
            skipped_count += 1
            print(f"Skipped role {role.name}: {e}")

    await ctx.send(f"✅ **ROLE NUKE COMPLETE:** Wiped **{deleted_count}** roles. (Skipped/Protected: **{skipped_count}**)\n➡️ You can now run `.setup_roles` to build the fresh hierarchy!")

@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    guild = ctx.guild
    await ctx.send("⚙️ Setting up ALL Chill-Verse roles... This will take ~15 seconds to avoid Discord rate limits.")
    
    base_perms = discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)
    
    roles_to_create = [
        {"name": "Supreme Leader", "perms": discord.Permissions(administrator=True), "color": discord.Color.dark_red(), "hoist": True},
        {"name": "Highness", "perms": discord.Permissions(administrator=True), "color": discord.Color.gold(), "hoist": True},
        {"name": "Authority", "perms": discord.Permissions(ban_members=True, kick_members=True, manage_channels=True, manage_roles=True), "color": discord.Color.orange(), "hoist": True},
        {"name": "Head Moderator", "perms": discord.Permissions(ban_members=True, kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.red(), "hoist": True},
        {"name": "Moderator", "perms": discord.Permissions(kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.yellow(), "hoist": True},
        {"name": "Trial Mod", "perms": discord.Permissions(moderate_members=True, manage_messages=True), "color": discord.Color.blue(), "hoist": True},
        {"name": "Chill-Verse Team", "perms": discord.Permissions(view_channel=True, send_messages=True, read_message_history=True), "color": discord.Color.dark_theme(), "hoist": True},
        {"name": "Sovereign (Levels 60-70)", "perms": base_perms, "color": discord.Color.purple(), "hoist": True},
        {"name": "Legend (Levels 50-59)", "perms": base_perms, "color": discord.Color.dark_purple(), "hoist": False},
        {"name": "Champion (Levels 40-49)", "perms": base_perms, "color": discord.Color.brand_red(), "hoist": False},
        {"name": "Elite (Levels 30-39)", "perms": base_perms, "color": discord.Color.dark_green(), "hoist": False},
        {"name": "Vanguard (Levels 20-29)", "perms": base_perms, "color": discord.Color.green(), "hoist": False},
        {"name": "Explorer (Levels 10-19)", "perms": base_perms, "color": discord.Color.teal(), "hoist": False},
        {"name": "Newbie (Levels 1-9)", "perms": base_perms, "color": discord.Color.light_grey(), "hoist": False},
        {"name": "Member", "perms": base_perms, "color": discord.Color.default(), "hoist": False},
        {"name": "OG", "perms": base_perms, "color": discord.Color.dark_gold(), "hoist": False},
        {"name": "Veteran", "perms": base_perms, "color": discord.Color.dark_grey(), "hoist": False},
        {"name": "Vanity", "perms": base_perms, "color": discord.Color.magenta(), "hoist": False},
        {"name": "Bump Pings", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
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
    
    created_count = 0
    for role_data in roles_to_create:
        if not discord.utils.get(guild.roles, name=role_data["name"]):
            try:
                await guild.create_role(
                    name=role_data["name"], 
                    permissions=role_data["perms"], 
                    color=role_data["color"], 
                    hoist=role_data["hoist"],
                    reason="Chill-Verse bulk role setup"
                )
                created_count += 1
                await asyncio.sleep(0.4) 
            except Exception as e:
                print(f"Failed to create role {role_data['name']}: {e}")
                
    await ctx.send(f"✅ Full server role integration complete! Created **{created_count}** new roles.")

# ==============================================================================
# NUKE & REBUILD CHANNELS
# ==============================================================================
@bot.command(name="nuke_channels")
@commands.has_permissions(administrator=True)
async def nuke_channels(ctx):
    await ctx.send("☢️ **NUKE INITIATED:** Wiping all other channels and categories. Please wait...")
    deleted_count = 0
    skipped_count = 0
    
    for channel in ctx.guild.channels:
        if channel.id == ctx.channel.id:
            skipped_count += 1
            continue
        try:
            await channel.delete(reason=f"Server Nuke initiated by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            skipped_count += 1
            print(f"Failed to delete channel {channel.name}: {e}")
            
    await ctx.send(f"✅ **NUKE COMPLETE:** Wiped **{deleted_count}** channels/categories.\n➡️ You can now run `.setup_channels` to build the fresh blueprint!")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def setup_channels(ctx):
    guild = ctx.guild
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]

    await ctx.send("🏗️ Deploying server blueprint with absolute Team access and public member restrictions...")
    
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
            for rname in admin_roles:
                r = discord.utils.get(guild.roles, name=rname)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            if ch_type == "text":
                existing = discord.utils.get(category.text_channels, name=ch_name)
                if not existing:
                    await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites)
            elif ch_type == "voice":
                existing = discord.utils.get(category.voice_channels, name=ch_name)
                if not existing:
                    await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim, overwrites=overwrites)
            elif ch_type == "forum":
                existing = discord.utils.get(guild.forums, name=ch_name)
                if not existing:
                    try:
                        await guild.create_forum_channel(name=ch_name, category=category, overwrites=overwrites)
                    except Exception:
                        await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites)

            await asyncio.sleep(0.2)

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

    await ctx.send("✅ Chill-Verse channels deployed successfully! Team has access to every channel, while members/everyone are restricted to public areas.")

@bot.command(name="delete_channels")
@commands.has_permissions(administrator=True)
async def delete_channels(ctx, *channels: discord.abc.GuildChannel):
    if not channels:
        return await ctx.send("⚠️ Please mention the channels you want to delete. Example: `.delete_channels #channel1 #channel2`")

    deleted_count = 0
    failed_count = 0
    await ctx.send(f"🗑️ Attempting to delete {len(channels)} channel(s)...")

    for channel in channels:
        try:
            await channel.delete(reason=f"Batch manual deletion requested by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.35)
        except Exception:
            failed_count += 1

    await ctx.send(f"✅ Channel deletion complete! Successfully deleted **{deleted_count}** channel(s). Failed: **{failed_count}**.")

@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def backup(ctx):
    guild = ctx.guild
    ch = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🩸・bot-errors` to store the data.", delete_after=5)
        
    backup_data = {
        "server_name": guild.name,
        "roles": [{"name": role.name, "permissions": role.permissions.value} for role in guild.roles],
        "text_channels": [{"name": channel.name, "category": str(channel.category)} for channel in guild.text_channels]
    }
    
    file = discord.File(io.BytesIO(json.dumps(backup_data, indent=4).encode('utf-8')), filename="server_backup.json")
    try:
        await ch.send(content=f"🔒 **Manual Backup triggered by {ctx.author.mention}**", file=file)
        await ctx.send("✅ Backup completed successfully!", delete_after=5)
    except Exception:
        pass

# ==============================================================================
# RUN BOT
# ==============================================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("⚠️ CRITICAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is missing!")
    else:
        bot.run(TOKEN)
