import os
import discord
from discord.ext import commands
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# --- 1. RENDER KEEP-ALIVE SERVER (Prevents Port Timeout Crashes) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CHOCO Bot is alive and running!")

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="C", intents=intents)
bot.remove_command("help")

EMBED_COLOR = 0xFF69B4  # Hot Pink & Golden Theme

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} successfully!")

# --- 3. BASIC PING COMMAND ---
@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

# --- 4. INTERACTIVE HELP MENU UI ---
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moderation", description="Complete suite of 20+ moderation tools", emoji="🛡️", value="mod"),
            discord.SelectOption(label="Economy & Animals", description="Cotes currency, hunting, zoo, and pet battles", emoji="🪙", value="economy"),
            discord.SelectOption(label="Gambling & Minigames", description="Slots, blackjack, coinflip, and high-stakes games", emoji="🔥", value="gambling"),
            discord.SelectOption(label="Social & Fun", description="Marriage, profiles, ship, actions, and OwO-speak", emoji="✨", value="social"),
            discord.SelectOption(label="Pokémon Cards", description="Catch, collect, trade, and battle cards", emoji="📦", value="pokemon"),
            discord.SelectOption(label="Utilities & Self-Roles", description="Hex colors, ping, stats, ticket setups, and self-roles", emoji="⚙️", value="utility"),
        ]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        categories = {
            "mod": {
                "title": "🛡️ ─── 『 MODERATION SUITE 』 ─── 🛡️",
                "commands": "`Cwarn` `Ctimeout` `Cunmute` `Ckick` `Cban` `Cunban` `Ctempban` `Csoftban` `Cpurge` `Cslowmode` `Clock` `Cunlock` `Chistory` `Cwhois` `Cmodlogs` `Creason` `Cnote` `Cnotes` `Cnick` `Cantiraid`"
            },
            "economy": {
                "title": "🪙 ─── 『 ECONOMY & WILDLIFE 』 ─── 🪙",
                "commands": "`Chunt` `Cauto` `Czoo` `Codex` `Csell` `Cinv` `Csacrifice` `Cfight` `Cteam` `Cpets` `Ceq` `Cweap` `Cupgrade` `Crename` `Ccowoncy` `Cday` `Cshop` `Cbuy` `Csend` `Clb` `Cq` `Cvote`"
            },
            "gambling": {
                "title": "🔥 ─── 『 HIGH-STAKES CASINO 』 ─── 🔥",
                "commands": "`Cslot` `Ccf` `Cbj` `Chl` `Cmine` `Clotto` `Csnail`"
            },
            "social": {
                "title": "✨ ─── 『 SOCIAL & FUN 』 ─── ✨",
                "commands": "`Cmarry` `Cdivorce` `Ccookie` `Cprofile` `Cship` `Cowoify` `Cpray` `Ctop` `Cmy` `Cchecklist` `Cpat` `Ckiss` `Chug` `Cslap` `Ccuddle` `Cpoke` `Ctruth` `Cdare`"
            },
            "pokemon": {
                "title": "📦 ─── 『 POKEMON CARDS GAME 』 ─── 📦",
                "commands": "`Cpoke-drop` `Cpoke-catch` `Cdeck` `Cpoke-trade` `Cpoke-shop` `Cpoke-open`"
            },
            "utility": {
                "title": "⚙️ ─── 『 UTILITIES & ROLES 』 ─── ⚙️",
                "commands": "`Cselfrole-setup` `Cselfrole-add` `Cselfrole-remove` `Crole` `Chex` `Chex-remove` `Chex-setup` `Cticket-setup` `Cclose` `Capply-setup` `Capply` `Creview` `Caccept` `Creject` `Cverification-setup` `Crank` `CLeaderboard` `Clevel-role` `Cwelcome-channel` `Cgiveaway-start` `Cping`"
            }
        }
        
        cat_data = categories[self.values[0]]
        embed = discord.Embed(
            title=cat_data["title"],
            description=f"Here are the commands for **{self.values[0].capitalize()}**!\nFor more details, use `Chelp [command]`.\n\n{cat_data['commands']}",
            color=0xFFD700
        )
        embed.set_footer(text=f"🌸 Requested by {interaction.user.display_name} • CHOCO Engine", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())

@bot.command(name="help", aliases=["helppanel"])
async def help(ctx):
    embed = discord.Embed(
        title="🍫 ── 『 CHOCO BOT MASTER HELP PANEL 』 ── 🍫",
        description=(
            "Hey there! My prefix in this guild is `C`\n"
            "Here is your command center. Use the dropdown menu below to navigate through "
            "categories or click the external action links!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=EMBED_COLOR
    )
    
    embed.add_field(name="🛡️ Moderation", value="`Cwarn` `Ctimeout` `Cban` `Cpurge`", inline=False)
    embed.add_field(name="🪙 Economy & Animals", value="`Chunt` `Czoo` `Cshop` `Ccowoncy`", inline=False)
    embed.add_field(name="🔥 Gambling", value="`Cslot` `Ccf` `Cbj` `Chl` `Cmine`", inline=False)
    embed.add_field(name="✨ Social & Fun", value="`Cmarry` `Cprofile` `Cship` `Cowoify`", inline=False)
    embed.add_field(name="📦 Pokémon & Minigames", value="`Cpoke-catch` `Cdeck` `Ctruth` `Cdare`", inline=False)
    embed.add_field(name="⚙️ Utility & Roles", value="`Chex` `Crole` `Cticket-setup` `Crank`", inline=False)
    
    # Optional: replace with your raw GitHub link for standard.gif if desired
    # embed.set_image(url="YOUR_RAW_GITHUB_LINK_FOR_STANDARD_GIF")
    
    embed.set_footer(
        text=f"Requested by {ctx.author.display_name} • Powered by CHOCO Engine",
        icon_url=ctx.author.display_avatar.url
    )
    
    view = HelpView()
    view.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url="https://discord.gg/3FpFFxagXP", emoji="🛟"))
    view.add_item(discord.ui.Button(label="Vote Bot", style=discord.ButtonStyle.link, url="https://top.gg", emoji="⭐"))
    
    await ctx.send(embed=embed, view=view)

# --- 5. RUN BOT ---
bot.run(os.getenv("DISCORD_TOKEN"))
