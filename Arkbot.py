import discord
from discord.ext import commands
from discord.ui import Button, View

# Set up bot intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
NEW_MEMBER_ROLE = "Newbie"
DISBOARD_BOT_ID = 302050872383242240  # Standard Disboard Bot ID
afk_users = {}

# List of managed "Pro Hex" color roles
PRO_HEX_COLORS = [
    "Pro Hex Red",
    "Pro Hex Green",
    "Pro Hex Blue",
    "Pro Hex Pink",
    "Pro Hex Yellow",
    "Pro Hex Orange",
]

# 1. Automatic Role Assignment on Join
@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name=NEW_MEMBER_ROLE)
    if role:
        await member.add_roles(role)
        print(f"Assigned {NEW_MEMBER_ROLE} to {member.display_name}")

# 2. AFK Feature and Disboard Bump Tracker
@bot.event
async def on_message(message):
    if message.author.bot and message.author.id == DISBOARD_BOT_ID:
        # Detect Disboard Bump success message
        if message.embeds:
            embed_desc = message.embeds[0].description or ""
            if "Bump done" in embed_desc or "Bumped" in embed_desc:
                bumper = message.interaction.user if message.interaction else "a member"
                await message.channel.send(f"Thank you {bumper.mention} for bumping the server!")

    # AFK removal upon typing
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back {message.author.mention}, I have removed your AFK status.")

    # AFK mention notification
    for mention in message.mentions:
        if mention.id in afk_users:
            reason = afk_users[mention.id]
            await message.channel.send(f"{mention.display_name} is currently AFK: {reason}")

    await bot.process_commands(message)

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention}, your AFK status is set: {reason}")

# 3. Self-Assignable "Pro Hex" Color Roles
class ColorRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def assign_color(self, interaction: discord.Interaction, color_name: str):
        guild = interaction.guild
        member = interaction.user
        
        # Remove any existing Pro Hex color roles from the member
        roles_to_remove = [r for r in member.roles if r.name in PRO_HEX_COLORS]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        # Add requested Pro Hex color role
        new_role = discord.utils.get(guild.roles, name=color_name)
        if new_role:
            await member.add_roles(new_role)
            await interaction.response.send_message(f"Updated your color role to **{color_name}**!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Role '{color_name}' does not exist on this server.", ephemeral=True)

    @discord.ui.button(label="Pro Hex Red", style=discord.ButtonStyle.danger)
    async def red_button(self, interaction: discord.Interaction, button: Button):
        await self.assign_color(interaction, "Pro Hex Red")

    @discord.ui.button(label="Pro Hex Green", style=discord.ButtonStyle.success)
    async def green_button(self, interaction: discord.Interaction, button: Button):
        await self.assign_color(interaction, "Pro Hex Green")

    @discord.ui.button(label="Pro Hex Blue", style=discord.ButtonStyle.primary)
    async def blue_button(self, interaction: discord.Interaction, button: Button):
        await self.assign_color(interaction, "Pro Hex Blue")

    @discord.ui.button(label="Pro Hex Pink", style=discord.ButtonStyle.secondary)
    async def pink_button(self, interaction: discord.Interaction, button: Button):
        await self.assign_color(interaction, "Pro Hex Pink")

    @discord.ui.button(label="Pro Hex Yellow", style=discord.ButtonStyle.secondary)
    async def yellow_button(self, interaction: discord.Interaction, button: Button):
        await self.assign_color(interaction, "Pro Hex Yellow")

    @discord.ui.button(label="Pro Hex Orange", style=discord.ButtonStyle.secondary)
    async def orange_button(self, interaction: discord.Interaction, button: Button):
        await self.assign_color(interaction, "Pro Hex Orange")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_colors(ctx):
    view = ColorRoleView()
    await ctx.send("Pick a **Pro Hex** color role for your profile:", view=view)

# Run Bot
bot.run("YOUR_BOT_TOKEN_HERE")
