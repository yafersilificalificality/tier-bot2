import discord
from discord.ext import commands
from discord import app_commands
import os

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")

# Gamemode queues
queues = {
    "nethop": [],
    "pot": [],
    "sword": [],
    "axe": [],
    "vanilla": [],
    "mace": [],
    "uhc": [],
    "smp": []
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online as {bot.user}")

# ---------------- JOIN QUEUE ----------------

@bot.tree.command(name="join", description="Join tier test queue")
@app_commands.choices(gamemode=[
    app_commands.Choice(name="NethOP", value="nethop"),
    app_commands.Choice(name="Pot", value="pot"),
    app_commands.Choice(name="Sword", value="sword"),
    app_commands.Choice(name="Axe", value="axe"),
    app_commands.Choice(name="Vanilla", value="vanilla"),
    app_commands.Choice(name="Mace", value="mace"),
    app_commands.Choice(name="UHC", value="uhc"),
    app_commands.Choice(name="SMP", value="smp")
])
async def join(interaction: discord.Interaction, gamemode: app_commands.Choice[str]):
    await join_queue(interaction, gamemode.value)

async def join_queue(interaction, gamemode):
    user = interaction.user
    queue = queues[gamemode]

    if user.id in queue:
        await interaction.response.send_message("You are already in this queue.", ephemeral=True)
        return

    queue.append(user.id)
    pos = len(queue)

    await interaction.response.send_message(
        f"You joined **{gamemode.upper()}** queue at position **#{pos}**",
        ephemeral=True
    )

    if pos == 1:
        await open_ticket(interaction.guild, user, gamemode)

# ---------------- OPEN TICKET ----------------

async def open_ticket(guild, user, gamemode):
    staff_role = discord.utils.get(guild.roles, name="Staff")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True)
    }

    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name.lower()}",
        overwrites=overwrites,
        topic=f"{gamemode}|{user.id}"
    )

    await channel.send(
        f"🎫 **Tier Test Ticket**\n\n"
        f"User: {user.mention}\n"
        f"Gamemode: **{gamemode.upper()}**\n\n"
        f"Press **Close Ticket** when finished.",
        view=CloseTicketView()
    )

# ---------------- CLOSE BUTTON ----------------

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel

        try:
            gamemode, user_id = channel.topic.split("|")
            user_id = int(user_id)
        except:
            await interaction.response.send_message("Invalid ticket channel.", ephemeral=True)
            return

        queue = queues[gamemode]

        if user_id in queue:
            queue.remove(user_id)

        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await channel.delete()

        await open_next(interaction.guild, gamemode)

# ---------------- AUTO NEXT ----------------

async def open_next(guild, gamemode):
    queue = queues[gamemode]

    if not queue:
        return

    user = guild.get_member(queue[0])

    if user:
        await open_ticket(guild, user, gamemode)

# ---------------- REMOVE FROM QUEUE ----------------

@bot.tree.command(name="remove", description="Remove a user from a queue (staff only)")
@app_commands.describe(gamemode="Gamemode", user="User to remove")
@app_commands.choices(gamemode=[
    app_commands.Choice(name="NethOP", value="nethop"),
    app_commands.Choice(name="Pot", value="pot"),
    app_commands.Choice(name="Sword", value="sword"),
    app_commands.Choice(name="Axe", value="axe"),
    app_commands.Choice(name="Vanilla", value="vanilla"),
    app_commands.Choice(name="Mace", value="mace"),
    app_commands.Choice(name="UHC", value="uhc"),
    app_commands.Choice(name="SMP", value="smp")
])
async def remove(interaction: discord.Interaction, gamemode: app_commands.Choice[str], user: discord.Member):

    staff_role = discord.utils.get(interaction.guild.roles, name="Staff")

    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    queue = queues[gamemode.value]

    if user.id not in queue:
        await interaction.response.send_message("User is not in that queue.", ephemeral=True)
        return

    pos = queue.index(user.id) + 1
    queue.remove(user.id)

    await interaction.response.send_message(
        f"✅ Removed **{user.name}** from **{gamemode.value.upper()} queue** (was #{pos})",
        ephemeral=True
    )

    if pos == 1:
        await open_next(interaction.guild, gamemode.value)

# ---------------- QUEUE VIEW ----------------

@bot.tree.command(name="queue", description="View queue")
async def queue_view(interaction: discord.Interaction, gamemode: str):
    if gamemode not in queues:
        await interaction.response.send_message("Invalid gamemode.", ephemeral=True)
        return

    q = queues[gamemode]

    if not q:
        await interaction.response.send_message("Queue is empty.", ephemeral=True)
        return

    text = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(q)])

    await interaction.response.send_message(
        f"**{gamemode.upper()} Queue:**\n{text}",
        ephemeral=True
    )

# ---------------- RUN ----------------

bot.run(TOKEN)