import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
import asyncio
import json
import os
import datetime

# ---------- تنظیمات پایه و متغیرها ----------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "god2_config.json"
WARN_FILE = "warns.json"

config = {}
warns = {}
protected_users = []  # لیست آیدی کاربرهای محافظت شده

OWNER_ID = 1271001203496587287  # آیدی خودت رو اینجا بگذار

# ---------- بارگذاری و ذخیره تنظیمات ----------
def load_config():
    global config
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f)
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def ensure_guild(gid):
    if str(gid) not in config:
        config[str(gid)] = {
            "verify_roles": {},
            "ticket_categories": [],
            "support_roles": [],
            "log_channel": None,
            "whitelist_roles": [],
            "security_mode": True
        }
        save_config()

# ---------- بارگذاری و ذخیره وارن‌ها ----------
def load_warns():
    global warns
    if os.path.exists(WARN_FILE):
        with open(WARN_FILE, "r") as f:
            warns = json.load(f)
    else:
        warns = {}

def save_warns():
    with open(WARN_FILE, "w") as f:
        json.dump(warns, f, indent=4)

# ---------- توابع کمکی ----------
def embed_msg(title, desc, user=None, color=discord.Color.blurple()):
    embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())
    if user:
        embed.set_footer(text=user.name, icon_url=user.display_avatar.url)
    return embed

def get_log_channel(guild):
    gid = str(guild.id)
    log_id = config.get(gid, {}).get("log_channel")
    if log_id:
        return guild.get_channel(log_id)
    return None

# ---------- رویداد آماده به کار ----------
@bot.event
async def on_ready():
    load_config()
    load_warns()
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# ---------- لاگ کامل ----------
@bot.event
async def on_member_join(member):
    ch = get_log_channel(member.guild)
    if ch:
        await ch.send(embed=embed_msg("📥 عضو جدید", f"{member.mention} وارد سرور شد!"))
    gid = str(member.guild.id)
    ensure_guild(gid)
    unverified_id = config[gid]["verify_roles"].get("unverified")
    if unverified_id:
        role = member.guild.get_role(unverified_id)
        if role:
            await member.add_roles(role, reason="Unverified user")

@bot.event
async def on_member_remove(member):
    ch = get_log_channel(member.guild)
    if ch:
        await ch.send(embed=embed_msg("📤 خروج عضو", f"{member.mention} سرور را ترک کرد."))

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    ch = get_log_channel(message.guild)
    if ch:
        await ch.send(embed=embed_msg("🗑️ پیام حذف شد", f"فرستنده: {message.author.mention}\nمحتوا: {message.content}"))

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if before.content != after.content:
        ch = get_log_channel(before.guild)
        if ch:
            await ch.send(embed=embed_msg("✏️ پیام ویرایش شد", f"فرستنده: {before.author.mention}\nقبل: {before.content}\nبعد: {after.content}"))

@bot.event
async def on_member_update(before, after):
    ch = get_log_channel(after.guild)
    if ch and before.roles != after.roles:
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added:
            await ch.send(embed=embed_msg("➕ رول اضافه شد", f"{after.mention} رول گرفت: {', '.join([r.name for r in added])}"))
        if removed:
            await ch.send(embed=embed_msg("➖ رول حذف شد", f"{after.mention} رول از دست داد: {', '.join([r.name for r in removed])}"))

@bot.event
async def on_guild_channel_update(before, after):
    ch = get_log_channel(after.guild)
    if ch and before.name != after.name:
        await ch.send(embed=embed_msg("🔧 تغییر نام چنل", f"قبل: {before.name}\nبعد: {after.name}"))

@bot.event
async def on_member_ban(guild, user):
    ch = get_log_channel(guild)
    if ch:
        await ch.send(embed=embed_msg("⛔ بن کاربر", f"{user} بن شد!"))

@bot.event
async def on_member_unban(guild, user):
    ch = get_log_channel(guild)
    if ch:
        await ch.send(embed=embed_msg("✅ آنبن کاربر", f"{user} آنبن شد!"))

# ---------- Anti-Nuke & Anti-Cheat with Whitelist ----------
@bot.tree.command(name="addwhitelist")
@app_commands.describe(role="رولی که باید تو لیست امن باشه (بن نشه)")
async def addwhitelist(interaction: Interaction, role: discord.Role):
    """اضافه کردن رول به لیست وایت‌لیست برای جلوگیری از بن اشتباهی"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    ensure_guild(gid)
    if role.id not in config[gid]["whitelist_roles"]:
        config[gid]["whitelist_roles"].append(role.id)
        save_config()
        await interaction.response.send_message(f"✅ رول {role.name} به وایت‌لیست اضافه شد!", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ این رول قبلاً اضافه شده.", ephemeral=True)

@bot.tree.command(name="removewhitelist")
@app_commands.describe(role="رولی که می‌خوای از وایت‌لیست حذف کنی")
async def removewhitelist(interaction: Interaction, role: discord.Role):
    """حذف رول از لیست وایت‌لیست"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    ensure_guild(gid)
    if role.id in config[gid]["whitelist_roles"]:
        config[gid]["whitelist_roles"].remove(role.id)
        save_config()
        await interaction.response.send_message(f"✅ رول {role.name} از وایت‌لیست حذف شد.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ این رول در وایت‌لیست نیست.", ephemeral=True)

async def nuke_check(action_user, guild, reason="فعالیت مشکوک"):
    """بررسی فعالیت‌های خطرناک و بن کردن در صورت نبودن در وایت‌لیست"""
    gid = str(guild.id)
    ensure_guild(gid)
    whitelist = config[gid]["whitelist_roles"]
    user_roles = [r.id for r in action_user.roles]
    if any(r in whitelist for r in user_roles):
        return
    try:
        await guild.ban(action_user, reason=reason)
    except:
        pass
    log_channel = guild.get_channel(config[gid].get("log_channel"))
    if log_channel:
        await log_channel.send(embed=embed_msg("🚨 Anti-Nuke", f"{action_user.mention} بن شد به دلیل {reason}"))

@bot.event
async def on_guild_role_create(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.target.id == role.id:
            await nuke_check(entry.user, role.guild, "ساخت رول")

@bot.event
async def on_guild_role_delete(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        if entry.target.id == role.id:
            await nuke_check(entry.user, role.guild, "حذف رول")

@bot.event
async def on_guild_role_update(before, after):
    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
        if entry.target.id == before.id:
            await nuke_check(entry.user, after.guild, "تغییر رول (اسم یا پرمیشن)")

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                await nuke_check(entry.user, channel.guild, "ساخت چنل")

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.target.id == channel.id:
            await nuke_check(entry.user, channel.guild, "حذف چنل")

@bot.event
async def on_guild_channel_update(before, after):
    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
        if entry.target.id == before.id:
            await nuke_check(entry.user, after.guild, "ویرایش چنل (اسم یا پرمیشن)")

@bot.event
async def on_guild_update(before, after):
    async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
        await nuke_check(entry.user, after, "تغییر تنظیمات سرور")

# ---------- Verify System with Button ----------
@bot.tree.command(name="setverifyroles")
@app_commands.describe(unverified="رول اولیه (مثلاً Unverified)", member="رول بعد از وریفای (مثلاً Member)")
async def setverifyroles(interaction: Interaction, unverified: discord.Role, member: discord.Role):
    """تنظیم رول‌های وریفای"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    ensure_guild(gid)
    config[gid]["verify_roles"]["unverified"] = unverified.id
    config[gid]["verify_roles"]["member"] = member.id
    save_config()
    await interaction.response.send_message(f"✅ رول‌های وریفای تنظیم شدند.\nUnverified: {unverified.name}\nMember: {member.name}", ephemeral=True)

class VerifyButton(ui.View):
    def __init__(self, unverified_role_id, member_role_id):
        super().__init__(timeout=None)
        self.unverified_role_id = unverified_role_id
        self.member_role_id = member_role_id

    @ui.button(label="Verify", style=discord.ButtonStyle.green, emoji="✅")
    async def verify_button(self, interaction: Interaction, button: ui.Button):
        user = interaction.user
        guild = interaction.guild
        unverified_role = guild.get_role(self.unverified_role_id)
        member_role = guild.get_role(self.member_role_id)
        if unverified_role in user.roles:
            try:
                await user.remove_roles(unverified_role, reason="Verified")
                await user.add_roles(member_role, reason="Verified")
                await interaction.response.send_message("✅ شما با موفقیت وریفای شدید!", ephemeral=True)
            except:
                await interaction.response.send_message("❌ مشکلی در اختصاص رول پیش آمد.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ شما قبلاً وریفای شده‌اید یا رول Unverified را ندارید.", ephemeral=True)

@bot.tree.command(name="sendverify")
async def sendverify(interaction: Interaction):
    """ارسال پیام وریفای با دکمه"""
    gid = str(interaction.guild.id)
    ensure_guild(gid)
    unverified_id = config[gid]["verify_roles"].get("unverified")
    member_id = config[gid]["verify_roles"].get("member")
    if not unverified_id or not member_id:
        await interaction.response.send_message("❌ ابتدا با دستور /setverifyroles رول‌ها را تنظیم کنید.", ephemeral=True)
        return
    view = VerifyButton(unverified_id, member_id)
    await interaction.response.send_message("برای وریفای روی دکمه زیر کلیک کنید:", view=view)

# ---------- Ticket System ----------
@bot.tree.command(name="setticketcategory")
@app_commands.describe(category="کتگوری که تیکت‌ها داخلش ساخته شوند")
async def setticketcategory(interaction: Interaction, category: discord.CategoryChannel):
    """تنظیم کتگوری تیکت‌ها"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    ensure_guild(gid)
    config[gid]["ticket_categories"] = [category.id]
    save_config()
    await interaction.response.send_message(f"✅ کتگوری تیکت‌ها تنظیم شد به {category.name}", ephemeral=True)

@bot.tree.command(name="setlogchannel")
@app_commands.describe(channel="چنل لاگ‌ها")
async def setlogchannel(interaction: Interaction, channel: discord.TextChannel):
    """تنظیم چنل لاگ‌ها"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    ensure_guild(gid)
    config[gid]["log_channel"] = channel.id
    save_config()
    await interaction.response.send_message(f"✅ چنل لاگ تنظیم شد به {channel.name}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="باز کردن تیکت", style=discord.ButtonStyle.blurple, emoji="🎫")
    async def open_ticket(self, interaction: Interaction, button: ui.Button):
        gid = str(interaction.guild.id)
        ensure_guild(gid)
        categories = config[gid]["ticket_categories"]
        if not categories:
            await interaction.response.send_message("❌ کتگوری تیکت تنظیم نشده است.", ephemeral=True)
            return
        category = interaction.guild.get_channel(categories[0])
        existing = discord.utils.get(interaction.guild.channels, name=f"ticket-{interaction.user.name.lower()}")
        if existing:
            await interaction.response.send_message("❌ شما یک تیکت باز دارید.", ephemeral=True)
            return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"✅ تیکت شما ساخته شد: {channel.mention}", ephemeral=True)
        await channel.send(f"{interaction.user.mention} خوش آمدید! مشکل خود را اینجا مطرح کنید.")

@bot.tree.command(name="sendticketbutton")
async def sendticketbutton(interaction: Interaction):
    """ارسال دکمه بازکردن تیکت"""
    view = TicketView()
    await interaction.response.send_message("برای باز کردن تیکت روی دکمه زیر کلیک کنید:", view=view)

# ---------- Warn System ----------
@bot.tree.command(name="warn")
@app_commands.describe(user="کاربری که می‌خواهید وارن بدهید", reason="دلیل وارن")
async def warn(interaction: Interaction, user: discord.Member, reason: str):
    """دادن وارن به کاربر"""
    if interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("⛔ شما دسترسی کافی ندارید.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    if gid not in warns:
        warns[gid] = {}
    if str(user.id) not in warns[gid]:
        warns[gid][str(user.id)] = []
    warns[gid][str(user.id)].append({"reason": reason, "time": datetime.datetime.utcnow().isoformat()})
    save_warns()
    await interaction.response.send_message(f"✅ به {user.mention} وارن داده شد به دلیل: {reason}")

    # چک تعداد وارن‌ها برای تایم‌اوت اگر کاربر محافظت شده بود
    if user.id in protected_users:
        user_warns = warns[gid][str(user.id)]
        if len(user_warns) >= 5:
            try:
                await user.timeout(datetime.timedelta(minutes=10), reason="تایم‌اوت خودکار بعد از 5 وارن")
                await interaction.channel.send(f"⏱️ {user.mention} به دلیل دریافت 5 وارن، 10 دقیقه تایم‌اوت شد.")
                warns[gid][str(user.id)] = []  # ریست وارن‌ها بعد از تایم‌اوت
                save_warns()
            except:
                pass

@bot.tree.command(name="warns")
@app_commands.describe(user="نمایش وارن‌های کاربر")
async def warns_cmd(interaction: Interaction, user: discord.Member):
    """نمایش وارن‌های یک کاربر"""
    gid = str(interaction.guild.id)
    if gid in warns and str(user.id) in warns[gid]:
        user_warns = warns[gid][str(user.id)]
        text = "\n".join([f"{i+1}. {w['reason']} - {w['time']}" for i,w in enumerate(user_warns)])
        await interaction.response.send_message(embed=embed_msg(f"🚨 وارن‌های {user}", text))
    else:
        await interaction.response.send_message(f"❌ {user.mention} وارن ندارد.")

@bot.tree.command(name="clearwarns")
@app_commands.describe(user="کاربری که می‌خواهید وارن‌هایش پاک شود")
async def clearwarns(interaction: Interaction, user: discord.Member):
    """پاک کردن وارن‌های کاربر"""
    if interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("⛔ شما دسترسی کافی ندارید.", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    if gid in warns and str(user.id) in warns[gid]:
        warns[gid][str(user.id)] = []
        save_warns()
        await interaction.response.send_message(f"✅ وارن‌های {user.mention} پاک شد.")
    else:
        await interaction.response.send_message(f"❌ {user.mention} وارن ندارد.")

# ---------- Protected Users Management ----------
@bot.tree.command(name="addprotected")
@app_commands.describe(user="کاربری که می‌خواهید محافظت کنید")
async def addprotected(interaction: Interaction, user: discord.Member):
    """اضافه کردن کاربر به لیست محافظت شده"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    if user.id not in protected_users:
        protected_users.append(user.id)
        await interaction.response.send_message(f"✅ {user.mention} به لیست محافظت شده اضافه شد.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {user.mention} قبلاً محافظت شده است.", ephemeral=True)

@bot.tree.command(name="removeprotected")
@app_commands.describe(user="کاربری که می‌خواهید از لیست محافظت خارج کنید")
async def removeprotected(interaction: Interaction, user: discord.Member):
    """حذف کاربر از لیست محافظت شده"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    if user.id in protected_users:
        protected_users.remove(user.id)
        await interaction.response.send_message(f"✅ {user.mention} از لیست محافظت شده حذف شد.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {user.mention} در لیست محافظت شده نیست.", ephemeral=True)

# ---------- رویت و اخطار هنگام تگ کردن کاربر محافظت شده ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.mentions:
        for user in message.mentions:
            if user.id in protected_users:
                # ارسال پیام به تگ کننده در دایرکت
                try:
                    await message.author.send(f"⚠️ شما کاربر {user} را تگ کردید که محافظت شده است. مراقب باشید!")
                except:
                    pass
                # ارسال پیام در چنل
                await message.channel.send(f"⚠️ {message.author.mention} کاربر {user.mention} را تگ کرد که محافظت شده است!")
                # ارسال لاگ
                ch = get_log_channel(message.guild)
                if ch:
                    await ch.send(embed=embed_msg("⚠️ تگ کاربر محافظت شده", f"{message.author.mention} کاربر {user.mention} را تگ کرد."))
                # اضافه کردن وارن
                gid = str(message.guild.id)
                if gid not in warns:
                    warns[gid] = {}
                if str(message.author.id) not in warns[gid]:
                    warns[gid][str(message.author.id)] = []
                warns[gid][str(message.author.id)].append({"reason": f"تگ کردن کاربر محافظت شده {user}", "time": datetime.datetime.utcnow().isoformat()})
                save_warns()
                # چک و تایم‌اوت بعد از 5 وارن
                user_warns = warns[gid][str(message.author.id)]
                if len(user_warns) >= 5:
                    try:
                        await message.author.timeout(datetime.timedelta(minutes=10), reason="تایم‌اوت خودکار بعد از 5 وارن برای تگ کردن محافظت شده")
                        await message.channel.send(f"⏱️ {message.author.mention} به دلیل 5 بار تگ کردن کاربر محافظت شده، 10 دقیقه تایم‌اوت شد.")
                        warns[gid][str(message.author.id)] = []
                        save_warns()
                    except:
                        pass

    await bot.process_commands(message)

# ---------- دستورات مدیریتی ساده ----------
@bot.tree.command(name="ping")
async def ping(interaction: Interaction):
    """بررسی سرعت پاسخ بات"""
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)}ms")

@bot.tree.command(name="say")
@app_commands.describe(text="متنی که می‌خواهید بات بگوید")
async def say(interaction: Interaction, text: str):
    """بات متنی که شما می‌دهید را ارسال می‌کند"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ فقط صاحب بات می‌تواند این دستور را اجرا کند.", ephemeral=True)
        return
    await interaction.response.send_message(text)

@bot.tree.command(name="userinfo")
@app_commands.describe(user="نمایش اطلاعات کاربر")
async def userinfo(interaction: Interaction, user: discord.Member):
    """نمایش اطلاعات کامل یک کاربر"""
    embed = discord.Embed(title=f"اطلاعات {user}", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="نام کامل", value=str(user), inline=True)
    embed.add_field(name="آیدی", value=user.id, inline=True)
    embed.add_field(name="سرور جوین شده از", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="اکانت ساخته شده در", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="رول‌ها", value=", ".join([r.name for r in user.roles if r.name != "@everyone"]), inline=False)
    await interaction.response.send_message(embed=embed)
TOKEN = "MTQwMzI3MDY5NjI3MjEzODM4MA.GJyJMm.vDwgGQosmVb3OSwXgwdmCqBv47Rv6ExJNG6RzM"
bot.run(TOKEN)

