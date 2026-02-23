import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- CONFIG ----------------

GAMEMODES = ["nethop","pot","sword","axe","vanilla","mace","uhc","smp"]

VALID_TIERS = ["LT5","LT4","LT3","LT2","LT1","HT5","HT4","HT3","HT2","HT1"]

waitlists = {mode: [] for mode in GAMEMODES}

# ----------------------------------------

@bot.event
async def on_ready():
    print("Tier Testing System Online")
    await bot.tree.sync()

# ---------- TIER LOGIC ----------

def should_get_ticket(tier: str) -> bool:
    tier = tier.upper().strip()
    return tier in ["HT1", "LT1", "HT2", "LT2", "HT3"]

# ---------- UTIL ----------

async def get_or_create_waitlist_channel(guild, gamemode):
    name = f"waitlist-{gamemode}"
    channel = discord.utils.get(guild.text_channels, name=name)

    if not channel:
        channel = await guild.create_text_channel(name)

    return channel

# ---------- APPLICATION MODAL ----------

class TierModal(discord.ui.Modal, title="Tier Test Application"):

    server = discord.ui.TextInput(
        label="Server you want to tier test on",
        placeholder="e.g. minemen.club",
        required=True
    )

    tier = discord.ui.TextInput(
        label="Your Current Tier",
        placeholder="Example: HT3",
        required=True,
        max_length=4
    )

    gamemode = discord.ui.TextInput(
        label="Gamemode",
        placeholder="NethOP / Pot / Sword / Axe / Vanilla / Mace / UHC / SMP",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        tier_value = self.tier.value.upper().strip()
        gamemode = self.gamemode.value.lower().strip()

        if tier_value not in VALID_TIERS:
            return await interaction.response.send_message(
                "❌ Invalid tier format. Example: `HT3`, `LT2`",
                ephemeral=True
            )

        if gamemode not in GAMEMODES:
            return await interaction.response.send_message(
                "❌ Invalid gamemode.",
                ephemeral=True
            )

        await process_application(interaction, self.server.value, tier_value, gamemode)

# ---------- APPLICATION HANDLER ----------

async def process_application(interaction, server, tier, gamemode):

    guild = interaction.guild
    user = interaction.user

    # WAITLIST TIERS
    if not should_get_ticket(tier):
        waitlists[gamemode].append(user.id)

        channel = await get_or_create_waitlist_channel(guild, gamemode)
        await channel.send(f"➕ **{user.mention}** joined the **{gamemode.upper()}** waitlist.")

        return await interaction.response.send_message(
            f"✅ You were added to the **{gamemode.upper()}** waitlist.",
            ephemeral=True
        )

    # STAFF TICKET TIERS
    category = discord.utils.get(guild.categories, name="Staff Tickets")
    if not category:
        category = await guild.create_category("Staff Tickets")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    ticket = await guild.create_text_channel(
        f"ticket-{user.name}",
        category=category,
        overwrites=overwrites
    )

    await ticket.send(
        f"🎫 **Tier Test Ticket**\n\n"
        f"User: {user.mention}\n"
        f"Server: `{server}`\n"
        f"Tier: `{tier}`\n"
        f"Gamemode: `{gamemode.upper()}`\n\n"
        f"Staff will assist shortly."
    )

    await interaction.response.send_message(
        "🎟 Your private staff ticket has been created.",
        ephemeral=True
    )

# ---------- PANEL ----------

class Panel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply For Tier Test", style=discord.ButtonStyle.green)
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TierModal())

# ---------- COMMANDS ----------

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="Tier Testing System",
        description="Click below to apply for a tier test.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=Panel())

@bot.command()
async def queue(ctx, gamemode: str):
    gamemode = gamemode.lower()

    if gamemode not in GAMEMODES:
        return await ctx.send("❌ Invalid gamemode.")

    queue_list = waitlists[gamemode]

    if not queue_list:
        return await ctx.send("Queue is empty.")

    msg = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(queue_list)])
    await ctx.send(f"**{gamemode.upper()} Queue:**\n{msg}")

@bot.command()
async def next(ctx, gamemode: str):
    gamemode = gamemode.lower()

    if gamemode not in GAMEMODES:
        return await ctx.send("❌ Invalid gamemode.")

    if not waitlists[gamemode]:
        return await ctx.send("Queue is empty.")

    user_id = waitlists[gamemode].pop(0)
    await ctx.send(f"🎯 Next player: <@{user_id}>")

# ---------- RUN ----------

bot.run(TOKEN)