import asyncio
import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web
from datetime import timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
CONFIG_PATH = Path(__file__).with_name("config.json")
cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
events = defaultdict(deque)
joins = defaultdict(deque)
messages = defaultdict(deque)
audit_seen = set()
lock = asyncio.Lock()

def save():
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
from dashboard import start_dashboard, dashboard_state, record_backup, restore_backup
group = app_commands.Group(name="guard", description="Quản lý Aegis Guard")

def admin(interaction):
    return interaction.guild is not None and interaction.user.guild_permissions.administrator

async def report(guild, text):
    for cid in set([cfg.get("log_channel_id"), cfg.get("alert_channel_id")]):
        channel = guild.get_channel(int(cid or 0))
        if channel:
            try:
                await channel.send(text[:1950], allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass

async def sanction(guild, actor, reason):
    member = guild.get_member(actor.id)
    if member is None:
        return "Không tìm thấy thành viên"
    if member.id == guild.owner_id or member.id == bot.user.id:
        return "Không thể xử lý chủ server/bot"
    me = guild.me
    if me is None or member.top_role >= me.top_role:
        return "Role mục tiêu cao hơn hoặc bằng bot"
    if cfg.get("punishment") == "none":
        return "Chỉ cảnh báo"
    removable = [r for r in member.roles if r != guild.default_role and not r.managed and r < me.top_role]
    try:
        for role in removable:
            await member.remove_roles(role, reason=reason)
        return f"Đã gỡ {len(removable)} role có thể quản lý"
    except discord.HTTPException as exc:
        return f"Xử lý thất bại: {exc}"

async def audit_check(guild, action, key, target_id=None):
    if not cfg.get("enabled"):
        return
    await asyncio.sleep(1.5)
    try:
        async for entry in guild.audit_logs(limit=12, action=action):
            if target_id is not None and getattr(entry.target, "id", None) != target_id:
                continue
            if entry.id in audit_seen:
                continue
            if (discord.utils.utcnow() - entry.created_at).total_seconds() > 30:
                continue
            audit_seen.add(entry.id)
            if len(audit_seen) > 5000:
                audit_seen.clear()
            actor = entry.user
            if not actor or actor.id in cfg["trusted_user_ids"] or actor.id == guild.owner_id or actor.id == bot.user.id:
                return
            k = (guild.id, actor.id, key)
            now = time.monotonic()
            async with lock:
                q = events[k]
                q.append(now)
                while q and now-q[0] > cfg["window_seconds"]:
                    q.popleft()
                count = len(q)
                threshold = int(cfg["thresholds"].get(key, 999999))
                if count >= threshold:
                    q.clear()
            if count >= threshold:
                outcome = await sanction(guild, actor, f"Aegis anti-nuke: {key} {count}/{threshold}")
                await report(guild, f"🚨 **ANTI-NUKE** {actor.mention} `{key}` ({count}/{threshold}). {outcome}")
            return
    except (discord.Forbidden, discord.HTTPException) as exc:
        await report(guild, f"⚠️ Không đọc được audit log: {exc}")


@bot.event
async def on_ready():
    if not getattr(bot, "_synced", False):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Da dong bo {len(synced)} lenh cho server {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"Da dong bo {len(synced)} lenh global")

        print("Danh sach lenh:", [cmd.name for cmd in synced])
        bot._synced = True


    if not getattr(bot, "_dashboard_started", False):
        await start_dashboard(bot, cfg, save)
        bot._dashboard_started = True

    print(f"Aegis Guard online: {bot.user}")
@bot.event
async def on_guild_channel_delete(channel):
    await audit_check(channel.guild, discord.AuditLogAction.channel_delete, "channel_delete", channel.id)

@bot.event
async def on_guild_channel_create(channel):
    await audit_check(channel.guild, discord.AuditLogAction.channel_create, "channel_create", channel.id)

@bot.event
async def on_guild_channel_update(before, after):
    await audit_check(after.guild, discord.AuditLogAction.channel_update, "channel_update", after.id)

@bot.event
async def on_guild_role_delete(role):
    await audit_check(role.guild, discord.AuditLogAction.role_delete, "role_delete", role.id)

@bot.event
async def on_guild_role_create(role):
    await audit_check(role.guild, discord.AuditLogAction.role_create, "role_create", role.id)

@bot.event
async def on_guild_role_update(before, after):
    await audit_check(after.guild, discord.AuditLogAction.role_update, "role_update", after.id)

@bot.event
async def on_member_ban(guild, user):
    await audit_check(guild, discord.AuditLogAction.ban, "ban", user.id)

@bot.event
async def on_member_remove(member):
    await audit_check(member.guild, discord.AuditLogAction.kick, "kick", member.id)

@bot.event
async def on_webhooks_update(channel):
    await audit_check(channel.guild, discord.AuditLogAction.webhook_create, "webhook_create")

@bot.event
async def on_member_join(member):
    if member.bot:
        await audit_check(member.guild, discord.AuditLogAction.bot_add, "bot_add", member.id)
    setting = cfg["anti_raid"]
    if not cfg["enabled"] or not setting["enabled"] or member.bot:
        return
    now = time.monotonic()
    q = joins[member.guild.id]
    q.append(now)
    while q and now-q[0] > setting["window_seconds"]:
        q.popleft()
    if len(q) >= setting["joins"]:
        try:
            await member.timeout(discord.utils.utcnow()+__import__("datetime").timedelta(minutes=setting["timeout_minutes"]), reason="Aegis anti-raid")
            await report(member.guild, f"⚠️ Anti-raid: timeout thành viên mới {member.mention}")
        except discord.HTTPException:
            pass

@bot.event
async def on_message(message):
    if message.guild is None or message.author.bot or not cfg["enabled"]:
        return
    setting = cfg["anti_spam"]
    if not setting["enabled"] or message.author.guild_permissions.manage_messages:
        return
    key = (message.guild.id, message.author.id)
    now = time.monotonic()
    q = messages[key]
    q.append(now)
    while q and now-q[0] > setting["window_seconds"]:
        q.popleft()
    if len(q) >= setting["messages"]:
        q.clear()
        try:
            await message.author.timeout(discord.utils.utcnow()+__import__("datetime").timedelta(minutes=setting["timeout_minutes"]), reason="Aegis anti-spam")
            await report(message.guild, f"⚠️ Anti-spam: timeout {message.author.mention}")
        except discord.HTTPException:
            pass

@group.command(name="setup", description="Thiết lập kênh nhật ký")
@app_commands.check(admin)
async def setup(interaction: discord.Interaction, log_channel: discord.TextChannel, alert_channel: discord.TextChannel | None = None):
    cfg["log_channel_id"] = log_channel.id
    cfg["alert_channel_id"] = (alert_channel or log_channel).id
    save()
    await interaction.response.send_message("Đã thiết lập kênh log/cảnh báo.", ephemeral=True)

@group.command(name="config", description="Xem cấu hình")
@app_commands.check(admin)
async def config(interaction: discord.Interaction):
    safe = dict(cfg)
    await interaction.response.send_message("```json\n"+json.dumps(safe, ensure_ascii=False, indent=2)[:1750]+"\n```", ephemeral=True)

@group.command(name="enable", description="Bật hoặc tắt bảo vệ")
@app_commands.check(admin)
async def enable(interaction: discord.Interaction, enabled: bool):
    cfg["enabled"] = enabled
    save()
    await interaction.response.send_message(f"Bảo vệ: {'BẬT' if enabled else 'TẮT'}", ephemeral=True)

trust = app_commands.Group(name="trust", description="Danh sách tin cậy", parent=group)

@trust.command(name="add", description="Thêm người tin cậy")
@app_commands.check(admin)
async def trust_add(interaction: discord.Interaction, member: discord.Member):
    if member.id not in cfg["trusted_user_ids"]:
        cfg["trusted_user_ids"].append(member.id)
        save()
    await interaction.response.send_message(f"Đã tin cậy {member.mention}", ephemeral=True)

@trust.command(name="remove", description="Xóa người tin cậy")
@app_commands.check(admin)
async def trust_remove(interaction: discord.Interaction, member: discord.Member):
    if member.id in cfg["trusted_user_ids"]:
        cfg["trusted_user_ids"].remove(member.id)
        save()
    await interaction.response.send_message(f"Đã xóa tin cậy {member.mention}", ephemeral=True)

@group.command(name="threshold", description="Đặt ngưỡng hành vi trong cửa sổ thời gian")
@app_commands.check(admin)
@app_commands.choices(action=[app_commands.Choice(name=k, value=k) for k in cfg["thresholds"]])
async def threshold(interaction: discord.Interaction, action: app_commands.Choice[str], count: app_commands.Range[int, 1, 100]):
    cfg["thresholds"][action.value] = count
    save()
    await interaction.response.send_message(f"Đã đặt `{action.value}` = {count}", ephemeral=True)

@group.command(name="punishment", description="Chọn hình thức xử lý")
@app_commands.check(admin)
@app_commands.choices(mode=[app_commands.Choice(name="Gỡ role", value="strip_roles"), app_commands.Choice(name="Chỉ cảnh báo", value="none")])
async def punishment(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    cfg["punishment"] = mode.value
    save()
    await interaction.response.send_message(f"Chế độ: {mode.name}", ephemeral=True)


@group.command(name="backup", description="Lưu snapshot role và kênh")
@app_commands.check(admin)
async def backup_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result = await record_backup(interaction.guild)
    await interaction.followup.send(f"Đã sao lưu {result['roles']} role và {result['channels']} kênh (cấu trúc, không có tin nhắn).", ephemeral=True)

@group.command(name="restore", description="Khôi phục cấu trúc thiếu từ bản sao lưu")
@app_commands.check(admin)
async def restore_command(interaction: discord.Interaction, confirm: bool = False):
    if not confirm:
        await interaction.response.send_message("Lệnh có thể tạo lại role/kênh bị thiếu. Chạy `/guard restore confirm:true` để xác nhận. Không xóa hoặc ghi đè tài nguyên hiện tại.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    result = await restore_backup(interaction.guild)
    await interaction.followup.send(result[:1900], ephemeral=True)

@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if not interaction.response.is_done():
        await interaction.response.send_message(f"Lỗi hoặc không đủ quyền: {error}", ephemeral=True)
if not TOKEN:
    raise RuntimeError("Thiếu DISCORD_TOKEN")

bot.tree.add_command(group)

print("Lenh global:", [cmd.name for cmd in bot.tree.get_commands()])

bot.run(TOKEN)
