"""Minimal local dashboard and structural backup helpers for Aegis Guard.
This is a new companion implementation, not the user's original dashboard.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from aiohttp import web

ROOT = Path(__file__).parent
BACKUP_DIR = ROOT / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)


def dashboard_state(bot, cfg):
    return {'bot': str(bot.user) if bot.user else 'offline',
            'guilds': len(bot.guilds), 'protection': bool(cfg.get('enabled')),
            'anti_raid': bool(cfg.get('anti_raid', {}).get('enabled')),
            'anti_spam': bool(cfg.get('anti_spam', {}).get('enabled'))}


async def start_dashboard(bot, cfg, save):
    async def home(request):
        data = dashboard_state(bot, cfg)
        # All dynamic values are escaped by JSON serialization and inserted into textContent.
        return web.Response(text='''<!doctype html><html lang="vi"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PEARL OF HEAVEN | Aegis Guard</title>
<style>body{font:16px system-ui;background:#101724;color:#eaf0ff;max-width:760px;margin:8vh auto;padding:24px}
main{background:#1b2738;padding:26px;border-radius:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere}
a{color:#a4c9ff}</style><main><h1>PEARL OF HEAVEN</h1><p>Aegis Guard — trạng thái nội bộ</p>
<pre id="status">Đang tải...</pre><p>Cấu hình và sao lưu: sử dụng lệnh <b>/guard</b> trong Discord.</p>
<p>Dashboard này chỉ truy cập trên chính PC đang chạy bot.</p></main>
<script>async function update(){try{const r=await fetch('/api/status',{cache:'no-store'});
if(!r.ok)throw Error(r.status);document.querySelector('#status').textContent=JSON.stringify(await r.json(),null,2)}
catch(e){document.querySelector('#status').textContent='Không kết nối được: '+e.message}}
update();setInterval(update,10000)</script></html>''', content_type='text/html')

    async def status(request):
        return web.json_response(dashboard_state(bot, cfg))

    app = web.Application()
    app.router.add_get('/', home)
    app.router.add_get('/api/status', status)
    runner = web.AppRunner(app)
    await runner.setup()
    # Fixed loopback binding: never expose status publicly without authentication.
    site = web.TCPSite(runner, '127.0.0.1', int(os.getenv('DASHBOARD_PORT', '8080')))
    await site.start()
    print('Dashboard: http://127.0.0.1:' + os.getenv('DASHBOARD_PORT', '8080'))
    return runner


async def record_backup(guild):
    roles = [{'name': r.name, 'color': r.color.value, 'hoist': r.hoist,
              'mentionable': r.mentionable, 'permissions': r.permissions.value}
             for r in guild.roles if not r.is_default() and not r.managed]
    channels = []
    for c in guild.channels:
        if c.type.name not in ('text', 'voice', 'category'):
            continue
        channels.append({'name': c.name, 'type': c.type.name,
                         'category': c.category.name if c.category else None,
                         'position': c.position})
    payload = {'created_at': datetime.now(timezone.utc).isoformat(), 'guild_id': guild.id,
               'roles': roles, 'channels': channels}
    path = BACKUP_DIR / f'{guild.id}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'roles': len(roles), 'channels': len(channels)}


async def restore_backup(guild):
    path = BACKUP_DIR / f'{guild.id}.json'
    if not path.exists():
        return 'Chưa có bản sao lưu. Chạy /guard backup trước.'
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('guild_id') != guild.id:
        return 'Sai ID server trong bản sao lưu.'
    made_roles = made_channels = 0
    errors = []
    for r in data.get('roles', []):
        if any(x.name == r['name'] for x in guild.roles):
            continue
        try:
            import discord
            await guild.create_role(name=r['name'], color=discord.Color(r['color']),
                permissions=discord.Permissions(r['permissions']), hoist=r['hoist'],
                mentionable=r['mentionable'], reason='Aegis structural restore')
            made_roles += 1
        except Exception as exc:
            errors.append(f"role {r['name']}: {type(exc).__name__}")
    ordered = sorted(data.get('channels', []), key=lambda c: (c['type'] != 'category', c['position']))
    for c in ordered:
        if any(x.name == c['name'] and x.type.name == c['type'] for x in guild.channels):
            continue
        try:
            category = next((x for x in guild.categories if x.name == c['category']), None)
            if c['type'] == 'category':
                await guild.create_category(c['name'], reason='Aegis structural restore')
            elif c['type'] == 'text':
                await guild.create_text_channel(c['name'], category=category, reason='Aegis structural restore')
            elif c['type'] == 'voice':
                await guild.create_voice_channel(c['name'], category=category, reason='Aegis structural restore')
            made_channels += 1
        except Exception as exc:
            errors.append(f"channel {c['name']}: {type(exc).__name__}")
    return f'Đã tạo {made_roles} role, {made_channels} kênh. Không khôi phục tin nhắn, permission overrides hoặc cấu trúc đầy đủ. Lỗi: '+('; '.join(errors[:8]) if errors else 'không có')
