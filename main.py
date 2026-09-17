import os
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
import discord
from discord.ext import commands

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=["C", "c", "C ", "c "],
    intents=intents,
    help_command=None,
)

# --- DATABASE INITIALIZATION ---
conn = sqlite3.connect("choco_economy.db")
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    cotes INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    last_daily TEXT,
    last_work TEXT,
    last_pray TEXT,
    zoo_animals TEXT DEFAULT '',
    inventory TEXT DEFAULT '',
    married_to INTEGER DEFAULT 0
)
"""
)
conn.commit()


def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, cotes, streak, level, xp, last_daily, last_work, last_pray, zoo_animals, inventory, married_to) VALUES (?, 0, 0, 1, 0, NULL, NULL, NULL, '', '', 0)",
            (user_id,),
        )
        conn.commit()
        return (user_id, 0, 0, 1, 0, None, None, None, "", "", 0)
    return user


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} | Cotes Economy Engine Active")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
    _, _, _, level, xp, _, _, _, _, _, _ = get_user(user_id)
    xp += 5
    if xp >= level * 100:
        level += 1
        xp = 0
        cursor.execute(
            "UPDATE users SET level = ?, xp = ? WHERE user_id = ?",
            (level, xp, user_id),
        )
    else:
        cursor.execute(
            "UPDATE users SET xp = ? WHERE user_id = ?", (xp, user_id)
        )
    conn.commit()

    await bot.process_commands(message)


# --- 🎖️ RANKINGS ---


@bot.command(aliases=["top"])
async def leaderboard(ctx):
    cursor.execute(
        "SELECT user_id, cotes FROM users ORDER BY cotes DESC LIMIT 5"
    )
    top_users = cursor.fetchall()
    embed = discord.Embed(
        title="🏆 Top Cotes Holders", color=discord.Color.gold()
    )
    for idx, (uid, amt) in enumerate(top_users, start=1):
        u = bot.get_user(uid)
        name = u.name if u else f"User {uid}"
        embed.add_field(
            name=f"#{idx} {name}", value=f"**{amt:,} Cotes**", inline=False
        )
    await ctx.send(embed=embed)


@bot.command(aliases=["my"])
async def profile(ctx, target: discord.Member = None):
    t = target or ctx.author
    uid, cotes, streak, level, xp, _, _, _, zoo, inv, married = get_user(t.id)
    spouse = bot.get_user(married) if married else "None"

    embed = discord.Embed(
        title=f"👤 {t.display_name}'s Profile", color=discord.Color.blue()
    )
    embed.add_field(name="🪙 Cotes Balance", value=f"{cotes:,}", inline=True)
    embed.add_field(
        name="⭐ Level", value=f"Lvl {level} ({xp}/{level*100} XP)", inline=True
    )
    embed.add_field(name="🔥 Daily Streak", value=f"{streak} Days", inline=True)
    embed.add_field(
        name="💍 Married To",
        value=spouse.display_name if spouse != "None" else "Single",
        inline=True,
    )
    await ctx.send(embed=embed)


# --- 💰 ECONOMY ---


@bot.command(aliases=["cowoncy", "cote"])
async def cotes(ctx, target: discord.Member = None):
    t = target or ctx.author
    _, cotes, _, _, _, _, _, _, _, _, _ = get_user(t.id)
    await ctx.send(f"🪙 **{t.display_name}** has **{cotes:,} Cotes**!")


@bot.command(aliases=["give", "pay", "send"])
async def transfer(ctx, target: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("Enter a valid amount.")
    _, sender_cotes, _, _, _, _, _, _, _, _, _ = get_user(ctx.author.id)
    if sender_cotes < amount:
        return await ctx.send("Not enough Cotes!")

    cursor.execute(
        "UPDATE users SET cotes = cotes - ? WHERE user_id = ?",
        (amount, ctx.author.id),
    )
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (amount, target.id),
    )
    conn.commit()
    await ctx.send(
        f"💸 Transferred **{amount:,} Cotes** to **{target.display_name}**!"
    )


@bot.command()
async def daily(ctx):
    uid, cotes, streak, _, _, last_d_str, _, _, _, _, _ = get_user(ctx.author.id)
    now = datetime.utcnow()
    if last_d_str:
        last_d = datetime.fromisoformat(last_d_str)
        if now - last_d < timedelta(hours=24):
            rem = timedelta(hours=24) - (now - last_d)
            h, r = divmod(int(rem.total_seconds()), 3600)
            m, _ = divmod(r, 60)
            return await ctx.send(
                f"⌛ Wait **{h}h {m}m** before claiming daily Cotes."
            )

    new_streak = streak + 1
    reward = 500 + (new_streak * 50)
    cursor.execute(
        "UPDATE users SET cotes = cotes + ?, streak = ?, last_daily = ? WHERE user_id = ?",
        (reward, new_streak, now.isoformat(), ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"🎁 **Daily Claimed!** Received **{reward:,} Cotes** | Streak: **{new_streak} Days**"
    )


@bot.command()
async def vote(ctx):
    reward = 250
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (reward, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"🗳️ Thanks for voting for CHOCO! Received **{reward} Cotes**."
    )


@bot.command()
async def quest(ctx):
    quests = [
        "Hunt 3 animals",
        "Win 1 coinflip",
        "Pray for a server member",
        "Play 1 game of Hammer Hamster",
    ]
    await ctx.send(
        f"📜 **Daily Quest:** {random.choice(quests)} (Reward: **400 Cotes**)"
    )


@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Cotes Shop", color=discord.Color.green())
    embed.add_field(
        name="📦 Items Available",
        value="`1. Lootbox` - 500 Cotes\n`2. Crate` - 1,200 Cotes\n`3. Weapon` - 2,500 Cotes",
        inline=False,
    )
    embed.add_field(
        name="How to buy", value="Use `Cbuy [item_name]`", inline=False
    )
    await ctx.send(embed=embed)


@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    shop_prices = {"lootbox": 500, "crate": 1200, "weapon": 2500}
    if item not in shop_prices:
        return await ctx.send("Item not found in shop. Use `Cshop` to view.")

    price = shop_prices[item]
    _, cotes, _, _, _, _, _, _, _, inv, _ = get_user(ctx.author.id)

    if cotes < price:
        return await ctx.send("You don't have enough Cotes!")

    inv_list = [i for i in inv.split(",") if i]
    inv_list.append(item)
    updated_inv = ",".join(inv_list)

    cursor.execute(
        "UPDATE users SET cotes = cotes - ?, inventory = ? WHERE user_id = ?",
        (price, updated_inv, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"🛍️ Purchased **{item.capitalize()}** for **{price:,} Cotes**!"
    )


# --- 🌱 ANIMALS & COMBAT ---


@bot.command(aliases=["h"])
async def hunt(ctx):
    _, _, _, _, _, _, _, _, zoo, _, _ = get_user(ctx.author.id)
    animals = ["🐶 Dog", "🐱 Cat", "🐰 Rabbit", "🦊 Fox", "🐻 Bear", "🦁 Lion"]
    caught = random.choice(animals)

    z_list = [a for a in zoo.split(",") if a]
    z_list.append(caught)
    cursor.execute(
        "UPDATE users SET zoo_animals = ? WHERE user_id = ?",
        (",".join(z_list), ctx.author.id),
    )
    conn.commit()
    await ctx.send(f"🏹 You hunted down a **{caught}**! Saved to zoo.")


@bot.command(aliases=["z"])
async def zoo(ctx):
    _, _, _, _, _, _, _, _, zoo, _, _ = get_user(ctx.author.id)
    if not zoo:
        return await ctx.send("⛺ Your zoo is empty!")
    counts = {}
    for a in zoo.split(","):
        if a:
            counts[a] = counts.get(a, 0) + 1
    fmt = "\n".join([f"• {a}: {c}" for a, c in counts.items()])
    await ctx.send(f"🐾 **Your Zoo Collection:**\n{fmt}")


@bot.command()
async def sell(ctx, target_animal: str = "all"):
    _, _, _, _, _, _, _, _, zoo, _, _ = get_user(ctx.author.id)
    if not zoo:
        return await ctx.send("Zoo is empty.")

    z_list = [a for a in zoo.split(",") if a]
    earned = len(z_list) * 80
    cursor.execute(
        "UPDATE users SET cotes = cotes + ?, zoo_animals = '' WHERE user_id = ?",
        (earned, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"💰 Sold **{len(z_list)} animals** for **{earned:,} Cotes**!"
    )


@bot.command()
async def sacrifice(ctx):
    _, _, _, _, _, _, _, _, zoo, _, _ = get_user(ctx.author.id)
    if not zoo:
        return await ctx.send("No animals to sacrifice.")
    z_list = [a for a in zoo.split(",") if a]
    sacrificed = z_list.pop(0)
    reward = random.randint(150, 350)
    cursor.execute(
        "UPDATE users SET cotes = cotes + ?, zoo_animals = ? WHERE user_id = ?",
        (reward, ",".join(z_list), ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"🔥 Sacrificed **{sacrificed}** for **{reward} Cotes**!"
    )


@bot.command()
async def battle(ctx, opponent: discord.Member):
    p1_score = random.randint(10, 100)
    p2_score = random.randint(10, 100)
    winner = ctx.author if p1_score > p2_score else opponent
    await ctx.send(
        f"⚔️ **Battle:** {ctx.author.display_name} ({p1_score} ATK) vs {opponent.display_name} ({p2_score} ATK)!\n🏆 **{winner.display_name}** wins!"
    )


@bot.command(aliases=["inv"])
async def inventory(ctx):
    _, _, _, _, _, _, _, _, _, inv, _ = get_user(ctx.author.id)
    if not inv:
        return await ctx.send("🎒 Your inventory is empty!")
    counts = {}
    for i in inv.split(","):
        if i:
            counts[i] = counts.get(i, 0) + 1
    fmt = "\n".join([f"• {item.capitalize()}: {c}" for item, c in counts.items()])
    await ctx.send(f"🎒 **Your Inventory:**\n{fmt}")


@bot.command()
async def equip(ctx, item: str):
    await ctx.send(f"⚔️ Equipped **{item.capitalize()}**!")


@bot.command()
async def lootbox(ctx):
    reward = random.randint(300, 1000)
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (reward, ctx.author.id),
    )
    conn.commit()
    await ctx.send(f"📦 Unlocked Lootbox and found **{reward:,} Cotes**!")


@bot.command()
async def crate(ctx):
    reward = random.randint(800, 2500)
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (reward, ctx.author.id),
    )
    conn.commit()
    await ctx.send(f"🧰 Opened Crate and found **{reward:,} Cotes**!")


@bot.command()
async def team(ctx):
    await ctx.send("🛡️ **Team:** [ Slot 1: Bear ] | [ Slot 2: Lion ]")


@bot.command()
async def weapon(ctx):
    await ctx.send("🗡️ **Weapon:** Iron Sword (+15 ATK)")


@bot.command()
async def rename(ctx, *, new_name: str):
    await ctx.send(f"🏷️ Renamed pet to **{new_name}**!")


@bot.command(aliases=["salvage"])
async def dismantle(ctx):
    _, _, _, _, _, _, _, _, zoo, _, _ = get_user(ctx.author.id)
    if not zoo:
        return await ctx.send("No animals to salvage.")
    z_list = [a for a in zoo.split(",") if a]
    salvaged = z_list.pop(0)
    earned = random.randint(100, 300)
    cursor.execute(
        "UPDATE users SET cotes = cotes + ?, zoo_animals = ? WHERE user_id = ?",
        (earned, ",".join(z_list), ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"⚙️ Salvaged **{salvaged}** for **{earned} Cotes**!"
    )


@bot.command(aliases=["raid"])
async def boss(ctx):
    damage = random.randint(500, 2500)
    reward = random.randint(200, 600)
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (reward, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"⚔️ **Raid Boss!** Dealt **{damage:,} DMG** and earned **{reward:,} Cotes**!"
    )


# --- 🎲 GAMBLING & MINI-GAMES ---


@bot.command(aliases=["s"])
async def slots(ctx, amount: int = 10):
    _, cotes, _, _, _, _, _, _, _, _, _ = get_user(ctx.author.id)
    if amount <= 0 or cotes < amount:
        return await ctx.send("Invalid bet!")

    emojis = ["🍫", "🪙", "🍒", "💎"]
    s1, s2, s3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    if s1 == s2 == s3:
        winnings = amount * 4
        new_cotes = cotes + winnings
        msg = f"🎉 **JACKPOT!** Won **{winnings:,} Cotes**!"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        winnings = amount * 2
        new_cotes = cotes + winnings
        msg = f"✨ **Matched 2!** Won **{winnings:,} Cotes**!"
    else:
        new_cotes = cotes - amount
        msg = f"❌ Lost **{amount:,} Cotes**."

    cursor.execute(
        "UPDATE users SET cotes = ? WHERE user_id = ?",
        (new_cotes, ctx.author.id),
    )
    conn.commit()
    await ctx.send(f"🎰 [ {s1} | {s2} | {s3} ]\n{msg}")


@bot.command(aliases=["cf", "coinflip"])
async def flip(ctx, amount: int = 10, choice: str = "heads"):
    choice = choice.lower()
    _, cotes, _, _, _, _, _, _, _, _, _ = get_user(ctx.author.id)
    if amount <= 0 or cotes < amount:
        return await ctx.send("Invalid bet!")

    result = random.choice(["heads", "tails"])
    if choice in result:
        new_cotes = cotes + amount
        msg = f"🪙 Landed on **{result.upper()}**! Won **{amount:,} Cotes**!"
    else:
        new_cotes = cotes - amount
        msg = f"🪙 Landed on **{result.upper()}**! Lost **{amount:,} Cotes**."

    cursor.execute(
        "UPDATE users SET cotes = ? WHERE user_id = ?",
        (new_cotes, ctx.author.id),
    )
    conn.commit()
    await ctx.send(msg)


@bot.command()
async def lottery(ctx):
    pot = random.randint(5000, 20000)
    await ctx.send(f"🎟️ Current Lottery Pot: **{pot:,} Cotes**!")


@bot.command(aliases=["bj"])
async def blackjack(ctx, amount: int = 10):
    _, cotes, _, _, _, _, _, _, _, _, _ = get_user(ctx.author.id)
    if amount <= 0 or cotes < amount:
        return await ctx.send("Invalid bet!")

    p_score = random.randint(12, 21)
    d_score = random.randint(12, 21)
    if p_score > d_score:
        new_cotes = cotes + amount
        msg = f"🃏 You: **{p_score}** vs Dealer: **{d_score}**. Won **{amount:,} Cotes**!"
    elif p_score < d_score:
        new_cotes = cotes - amount
        msg = f"🃏 You: **{p_score}** vs Dealer: **{d_score}**. Lost **{amount:,} Cotes**."
    else:
        new_cotes = cotes
        msg = f"🃏 Push (**{p_score}**). Refunded!"

    cursor.execute(
        "UPDATE users SET cotes = ? WHERE user_id = ?",
        (new_cotes, ctx.author.id),
    )
    conn.commit()
    await ctx.send(msg)


@bot.command(aliases=["garden", "osnailgarden"])
async def snake(ctx):
    apples = random.randint(2, 8)
    reward = apples * 60
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (reward, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"🐍 **Snake Game!** Ate **{apples} apples** for **{reward} Cotes**!"
    )


@bot.command(aliases=["mines"])
async def hamster(ctx):
    whacked = random.randint(1, 5)
    reward = whacked * 75
    cursor.execute(
        "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
        (reward, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"🔨 **Hammer Hamster!** Whacked **{whacked} hamsters** for **{reward} Cotes**!"
    )


@bot.command()
async def highlow(ctx, choice: str = "high"):
    num = random.randint(1, 100)
    win = (choice.lower() == "high" and num > 50) or (
        choice.lower() == "low" and num <= 50
    )
    reward = 150 if win else 0
    if win:
        cursor.execute(
            "UPDATE users SET cotes = cotes + ? WHERE user_id = ?",
            (reward, ctx.author.id),
        )
        conn.commit()
        await ctx.send(f"🎲 Rolled **{num}**! Won **150 Cotes**!")
    else:
        await ctx.send(f"🎲 Rolled **{num}**! Incorrect guess.")


# --- 🎱 FUN & SOCIAL ---


@bot.command(name="8b")
async def eightball(ctx, *, question: str):
    responses = [
        "Yes, definitely!",
        "Most likely.",
        "Reply hazy, try again.",
        "Don't count on it.",
        "Outlook not so good.",
    ]
    await ctx.send(
        f"🎱 **Question:** {question}\n**Answer:** {random.choice(responses)}"
    )


@bot.command()
async def translate(ctx, *, text: str):
    await ctx.send(f"🌐 **Translated:** {text[::-1]}")


@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    u2 = user2 or ctx.author
    score = random.randint(0, 100)
    await ctx.send(
        f"💘 Matchmaking **{user1.display_name}** x **{u2.display_name}**: **{score}% Compatibility**!"
    )


@bot.command()
async def pray(ctx, target: discord.Member = None):
    now = datetime.utcnow()
    cursor.execute(
        "UPDATE users SET last_pray = ? WHERE user_id = ?",
        (now.isoformat(), ctx.author.id),
    )
    conn.commit()
    if target:
        await ctx.send(
            f"🙏 **{ctx.author.display_name}** prayed for **{target.display_name}**!"
        )
    else:
        await ctx.send(
            f"🙏 **{ctx.author.display_name}** prayed to the Cotes shrine!"
        )


@bot.command()
async def marry(ctx, target: discord.Member):
    cursor.execute(
        "UPDATE users SET married_to = ? WHERE user_id = ?",
        (target.id, ctx.author.id),
    )
    conn.commit()
    await ctx.send(
        f"💍 **{ctx.author.display_name}** married **{target.display_name}**!"
    )


@bot.command()
async def avatar(ctx, target: discord.Member = None):
    t = target or ctx.author
    await ctx.send(t.display_avatar.url)


# --- 🔧 UTILITY & SYSTEM ---


@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")


@bot.command()
async def stats(ctx):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    await ctx.send(
        f"📊 **CHOCO Stats:** Tracking **{total_users} registered users**."
    )


@bot.command()
async def link(ctx):
    await ctx.send(
        "🔗 Invite link: https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot"
    )


@bot.command()
async def guildlink(ctx):
    await ctx.send("🏰 Official support guild link: https://discord.gg/example")


@bot.command()
async def disable(ctx, cmd_name: str):
    await ctx.send(f"🚫 Command `{cmd_name}` disabled in this channel.")


@bot.command()
async def rules(ctx):
    await ctx.send(
        "📜 **Server Rules:** Be respectful, no spamming bot commands!"
    )


@bot.command()
async def color(ctx, hex_code: str):
    await ctx.send(f"🎨 Profile color updated to `#{hex_code}`!")


# --- 🍫 ULTRA-AESTHETIC OWOS-STYLE HELP MENU ---


@bot.command(name="help")
async def help(ctx, category: str = None):
    prefix = "C"

    categories = {
        "rankings": {
            "title": "🏆 ─── 『 RANKINGS & LEADERBOARD 』 ─── 🏆",
            "commands": "• `top` ── View top Cotes holders\n• `my` ── View personal statistics & profile",
        },
        "economy": {
            "title": "🪙 ─── 『 COTES TREASURY 』 ─── 🪙",
            "commands": "• `cotes` • `give` • `daily` • `vote`\n• `quest` • `shop` • `buy`",
        },
        "animals": {
            "title": "🐾 ─── 『 WILDLIFE & SAFARI 』 ─── 🐾",
            "commands": "• `zoo` • `hunt` • `sell` • `sacrifice`\n• `battle` • `inv` • `equip` • `lootbox`\n• `crate` • `team` • `weapon` • `rename`\n• `salvage` • `raid`",
        },
        "gambling": {
            "title": "🔥 ─── 『 HIGH-STAKES CASINO 』 ─── 🔥",
            "commands": "• `slots` • `coinflip` • `lottery` • `blackjack`\n• `snake` • `hamster` • `highlow`",
        },
        "fun": {
            "title": "✨ ─── 『 SOCIAL & MINI-GAMES 』 ─── ✨",
            "commands": "• `8b` • `translate` • `ship` • `pray`\n• `marry` • `profile` • `avatar`",
        },
        "utility": {
            "title": "⚙️ ─── 『 CORE UTILITIES 』 ─── ⚙️",
            "commands": "• `ping` • `stats` • `link` • `guildlink`\n• `disable` • `rules` • `color`",
        },
    }

    if category:
        cat_key = category.lower()
        if cat_key in categories:
            cat_data = categories[cat_key]
            embed = discord.Embed(
                title=f"⭐ ── 『 CHOCO » {category.upper()} 』 ── ⭐",
                description=(
                    f"```ansi\n\u001b[36m╭━━━ COMMAND MODULE ━━━╮\u001b[0m\n```\n"
                    f"{cat_data['commands']}\n\n"
                    f"╚════════════════════════════════╝"
                ),
                color=0x9B59B6,  # Sleek Purple Aesthetic
            )
            embed.set_footer(
                text=f"✨ Type {prefix}help for main menu | Prefix: {prefix}"
            )
            return await ctx.send(embed=embed)
        else:
            return await ctx.send(
                f"❌ **Category `{category}` not found!** Type `{prefix}help` to view all valid modules."
            )

    embed = discord.Embed(
        title="🍫 ── 『 CHOCO BOT SYSTEM MENU 』 ── 🍫",
        description=(
            f"✨ **Prefix:** `{prefix}` *(Case-Insensitive)*\n"
            f"🪙 **Currency:** `Cotes`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Use `{prefix}help [category]` to view specific modules!*\n"
            f"*Example:* `{prefix}help economy`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x2B2D31,  # Dark Mode Embed Theme
    )

    for cat, data in categories.items():
        embed.add_field(
            name=data["title"],
            value=f"{data['commands']}\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            inline=False,
        )

    embed.set_footer(
        text=f"🌸 Requested by {ctx.author.display_name} • Powered by CHOCO Engine",
        icon_url=ctx.author.display_avatar.url,
    )

    await ctx.send(embed=embed)


bot.run(os.environ.get("BOT_TOKEN"))
