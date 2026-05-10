import os, logging, json, re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8676953950:AAHCx8BFTgscveHUu7GNOVWktL8MDMT5JyI")
ADMIN_ID   = 7856585807
UPI_ID     = "9277322534@nyes"
UPI_NAME   = "Nitesh Kumar"
PERSONAL_PRICE = 49
BUSINESS_PRICE = 99
TRIAL_DAYS = 30

# ===== DB HELPERS =====
def load_json(f):
    try:
        with open(f, 'r', encoding='utf-8') as fp: return json.load(fp)
    except: return {}

def save_json(f, d):
    with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, indent=2, ensure_ascii=False)

def get_user(uid):   return load_json("users.json").get(str(uid))
def save_user(uid, d):
    db = load_json("users.json"); db[str(uid)] = d; save_json("users.json", db)
def get_expenses(uid): return load_json("expenses.json").get(str(uid), [])
def add_expense_db(uid, e):
    db = load_json("expenses.json"); k = str(uid)
    if k not in db: db[k] = []
    db[k].append(e); save_json("expenses.json", db)
def get_pending(uid):  return load_json("pending.json").get(str(uid))
def save_pending(uid, d):
    db = load_json("pending.json"); db[str(uid)] = d; save_json("pending.json", db)
def remove_pending(uid):
    db = load_json("pending.json"); db.pop(str(uid), None); save_json("pending.json", db)

# ===== HELPERS =====
def is_trial(u):  return u and datetime.now() < datetime.fromisoformat(u.get('trial_start','2000-01-01')) + timedelta(days=TRIAL_DAYS)
def is_paid(u):   return u and u.get('paid_until') and datetime.now() < datetime.fromisoformat(u['paid_until'])
def can_use(u):   return is_trial(u) or is_paid(u)
def days_left(u):
    d = (datetime.fromisoformat(u.get('trial_start','2000-01-01')) + timedelta(days=TRIAL_DAYS) - datetime.now()).days
    return max(0, d)

CATS = {
    'sabzi':'🥦 Sabzi','vegetable':'🥦 Sabzi','pyaj':'🥦 Sabzi','onion':'🥦 Sabzi',
    'fruit':'🍎 Fruit','aam':'🍎 Fruit','apple':'🍎 Fruit',
    'chai':'☕ Chai','tea':'☕ Chai','coffee':'☕ Coffee',
    'petrol':'⛽ Petrol','diesel':'⛽ Diesel','fuel':'⛽ Petrol',
    'dawa':'💊 Dawa','medicine':'💊 Dawa','tablet':'💊 Dawa',
    'milk':'🥛 Doodh','doodh':'🥛 Doodh',
    'roti':'🫓 Roti','bread':'🍞 Bread','atta':'🫓 Atta',
    'rice':'🍚 Chawal','chawal':'🍚 Chawal','dal':'🍲 Dal',
    'auto':'🛺 Auto','taxi':'🚕 Taxi','bus':'🚌 Bus','train':'🚆 Train',
    'bijli':'💡 Bijli','electricity':'💡 Bijli','bill':'📄 Bill',
    'recharge':'📱 Recharge','mobile':'📱 Mobile','internet':'🌐 Internet',
    'rent':'🏠 Rent','kiraya':'🏠 Kiraya',
    'salary':'👷 Salary','staff':'👷 Staff','worker':'👷 Staff',
    'client':'💼 Client','project':'💼 Project','freelance':'💼 Freelance',
    'invoice':'🧾 Invoice','payment':'💳 Payment',
    'udhar':'🤝 Udhar','loan':'🤝 Loan',
    'grocery':'🛒 Grocery','shop':'🛒 Shopping',
    'movie':'🎬 Movie','hotel':'🍽️ Hotel','restaurant':'🍽️ Restaurant','khana':'🍽️ Khana',
}

def get_cat(name):
    l = name.lower()
    for k, v in CATS.items():
        if k in l: return v
    return '💸 Other'

def parse_exp(text):
    t = text.strip()
    m1 = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?)$', t)
    m2 = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', t)
    if m1: return m1.group(1).strip(), float(m1.group(2))
    if m2: return m2.group(2).strip(), float(m2.group(1))
    return None, None

# ===== STATES =====
PHONE, EMAIL, MODE = range(3)

# ===== SIGNUP =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if user and can_use(user):
        mode = user.get('mode','personal')
        dl = days_left(user)
        trial = is_trial(user)
        await update.message.reply_text(
            f"🙏 *Wapas aaye MunimJi mein!*\n\n"
            f"{'👤 Personal' if mode=='personal' else '💼 Business'} Mode\n"
            f"{'🎁 Free trial: *'+str(dl)+' din baaki*' if trial else '✅ Paid Member'}\n\n"
            f"Kuch likhein jaise: *sabzi 50*\n"
            f"/help | /mode | /status | /upgrade",
            parse_mode='Markdown')
        return ConversationHandler.END
    await update.message.reply_text(
        "🙏 *Namaste! MunimJi mein Swagat!*\n\n"
        "💰 Personal + Business Expense Tracker\n"
        "🎁 Pehle *30 din bilkul FREE!*\n\n"
        "📱 Apna *mobile number* bhejein:\n_(jaise: 9876543210)_",
        parse_mode='Markdown')
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = update.message.text.strip()
    if not re.match(r'^[6-9]\d{9}$', p):
        await update.message.reply_text("❌ Sahi 10 digit number daalo"); return PHONE
    context.user_data['phone'] = p
    await update.message.reply_text(f"✅ *{p}* save!\n\n📧 Ab *email* bhejein:", parse_mode='Markdown')
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    e = update.message.text.strip().lower()
    if not re.match(r'^[\w._%+-]+@[\w.-]+\.[a-z]{2,}$', e):
        await update.message.reply_text("❌ Sahi email daalo _(jaise: name@gmail.com)_", parse_mode='Markdown')
        return EMAIL
    context.user_data['email'] = e
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("👤 Personal", callback_data='mode_personal'),
        InlineKeyboardButton("💼 Business", callback_data='mode_business')
    ]])
    await update.message.reply_text(
        "✅ Email save!\n\n*Mode choose karein:*\n\n"
        "👤 *Personal* — Ghar ka kharch, family budget\n"
        "💼 *Business* — Dukaan, freelance, client payments",
        reply_markup=kb, parse_mode='Markdown')
    return MODE

async def choose_mode_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    mode = q.data.replace('mode_','')
    uid = update.effective_user.id
    save_user(uid, {
        'phone': context.user_data.get('phone'),
        'email': context.user_data.get('email'),
        'mode': mode,
        'trial_start': datetime.now().isoformat(),
        'paid_until': None,
        'name': update.effective_user.first_name or 'User'
    })
    ex = "• *sabzi 50*\n• *total batao*\n• *budget set 5000*" if mode=='personal' else "• *client Ram 5000*\n• *staff salary 8000*\n• *total batao*"
    await q.edit_message_text(
        f"🎉 *Signup Complete!*\n\n"
        f"{'👤 Personal' if mode=='personal' else '💼 Business'} Mode\n"
        f"🎁 *30 din FREE trial shuru!*\n\n"
        f"Aise use karo:\n{ex}\n\n/help se poori list dekho",
        parse_mode='Markdown')
    return ConversationHandler.END

# ===== MODE =====
async def change_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; user = get_user(uid)
    if not user: await update.message.reply_text("Pehle /start karein!"); return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("👤 Personal", callback_data='sw_personal'),
        InlineKeyboardButton("💼 Business", callback_data='sw_business')
    ]])
    await update.message.reply_text(
        f"Current: {'👤 Personal' if user.get('mode')=='personal' else '💼 Business'}\n\nNaya mode:", reply_markup=kb)

async def switch_mode_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    mode = q.data.replace('sw_',''); uid = update.effective_user.id
    user = get_user(uid); user['mode'] = mode; save_user(uid, user)
    await q.edit_message_text(f"✅ Ab {'👤 Personal' if mode=='personal' else '💼 Business'} mode mein!")

# ===== UPGRADE + PAYMENT =====
async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; user = get_user(uid)
    if not user: await update.message.reply_text("Pehle /start karein!"); return
    mode = user.get('mode','personal')
    price = PERSONAL_PRICE if mode=='personal' else BUSINESS_PRICE
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"💳 ₹{price} Pay Karo", callback_data=f'pay_{price}')]])
    await update.message.reply_text(
        f"👑 *MunimJi Upgrade*\n\n"
        f"{'👤 Personal' if mode=='personal' else '💼 Business'} Plan: *₹{price}/month*\n\n"
        f"✅ Unlimited entries\n✅ Budget alerts\n✅ Monthly reports\n✅ Search & delete\n✅ Priority support\n\n"
        f"Button dabao:",
        reply_markup=kb, parse_mode='Markdown')

async def show_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = update.effective_user.id
    price = q.data.replace('pay_','')
    save_pending(uid, {'amount': price, 'requested_at': datetime.now().isoformat()})
    try:
        with open('qr.jpg','rb') as f:
            await q.message.reply_photo(photo=f,
                caption=(
                    f"📲 *UPI Payment*\n\n"
                    f"UPI ID: `{UPI_ID}`\n"
                    f"Name: *{UPI_NAME}*\n"
                    f"Amount: *₹{price}*\n\n"
                    f"*Steps:*\n"
                    f"1️⃣ GPay/PhonePe/Paytm open karo\n"
                    f"2️⃣ QR scan karo ya UPI ID daalo\n"
                    f"3️⃣ ₹{price} pay karo\n"
                    f"4️⃣ Payment ka *screenshot yahan bhejo*\n\n"
                    f"⏰ 24 ghante mein activate ho jaayega!"
                ), parse_mode='Markdown')
    except:
        await q.message.reply_text(
            f"📲 *UPI Payment*\n\n"
            f"UPI ID: `{UPI_ID}`\n"
            f"Name: *{UPI_NAME}*\n"
            f"Amount: *₹{price}*\n\n"
            f"GPay/PhonePe se pay karo aur *screenshot bhejo!*",
            parse_mode='Markdown')

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if not user: return
    pending = get_pending(uid)
    if not pending: return

    # Forward to admin
    try:
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=uid, message_id=update.message.message_id)
        await context.bot.send_message(chat_id=ADMIN_ID,
            text=(
                f"💰 *New Payment!*\n\n"
                f"👤 {user.get('name','?')}\n"
                f"📱 {user.get('phone','?')}\n"
                f"🆔 `{uid}`\n"
                f"💵 ₹{pending.get('amount','?')}\n"
                f"Mode: {'👤 Personal' if user.get('mode')=='personal' else '💼 Business'}\n\n"
                f"✅ Approve: `/approve {uid}`\n"
                f"❌ Reject: `/reject {uid}`"
            ), parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Admin forward error: {e}")

    await update.message.reply_text(
        "✅ *Screenshot mil gaya!*\n\n⏰ 24 ghante mein activate kar denge.\nShukriya! 🙏",
        parse_mode='Markdown')

# ===== ADMIN =====
async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try: target = int(context.args[0])
    except: await update.message.reply_text("Usage: /approve 123456"); return
    user = get_user(target)
    if not user: await update.message.reply_text("User nahi mila!"); return
    user['paid_until'] = (datetime.now() + timedelta(days=30)).isoformat()
    save_user(target, user); remove_pending(target)
    try:
        await context.bot.send_message(chat_id=target,
            text="🎉 *Payment Verify!*\n\n✅ 30 din ke liye activate ho gaya!\n\nShukriya! /help se sab features dekho",
            parse_mode='Markdown')
    except: pass
    await update.message.reply_text(f"✅ User {target} activate!")

async def reject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try: target = int(context.args[0])
    except: await update.message.reply_text("Usage: /reject 123456"); return
    remove_pending(target)
    try:
        await context.bot.send_message(chat_id=target,
            text="❌ Payment verify nahi ho saka.\nDobara try karein: /upgrade",
            parse_mode='Markdown')
    except: pass
    await update.message.reply_text(f"❌ User {target} reject kiya.")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users = load_json("users.json")
    expenses = load_json("expenses.json")
    pending = load_json("pending.json")
    total_u = len(users)
    paid_u = sum(1 for u in users.values() if is_paid(u))
    trial_u = sum(1 for u in users.values() if is_trial(u))
    total_e = sum(len(v) for v in expenses.values())
    await update.message.reply_text(
        f"📊 *MunimJi Stats*\n\n"
        f"👥 Total users: {total_u}\n"
        f"🎁 Trial: {trial_u}\n"
        f"✅ Paid: {paid_u}\n"
        f"📝 Entries: {total_e}\n"
        f"⏳ Pending payments: {len(pending)}\n\n"
        f"💰 Revenue: ~₹{paid_u*49}/month",
        parse_mode='Markdown')

# ===== MESSAGES =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    text = update.message.text.strip()
    lower = text.lower()

    if not user:
        await update.message.reply_text("Pehle /start karein!"); return

    if not can_use(user):
        await update.message.reply_text(
            "⏰ *Free trial khatam!*\n\nUpgrade karein: /upgrade", parse_mode='Markdown'); return

    mode = user.get('mode','personal')

    # Trial warning
    if is_trial(user) and days_left(user) <= 3:
        await update.message.reply_text(
            f"⚠️ Sirf *{days_left(user)} din* bacha trial mein!\n/upgrade karein", parse_mode='Markdown')

    # Commands
    if any(w in lower for w in ['total','kitna','summary','hisaab']):
        await cmd_total(update, uid, mode)
    elif any(w in lower for w in ['aaj','today']):
        await cmd_today(update, uid, mode)
    elif any(w in lower for w in ['list','dikhao','sab dikha']):
        await cmd_list(update, uid)
    elif lower.startswith('budget set'):
        await cmd_budget_set(update, uid, user, lower)
    elif lower in ['budget','budget check']:
        await cmd_budget_check(update, uid, user)
    elif any(w in lower for w in ['delete last','hatao','undo']):
        await cmd_delete_last(update, uid)
    elif lower.startswith('search ') or lower.startswith('dhundo '):
        q = lower.replace('search ','').replace('dhundo ','').strip()
        await cmd_search(update, uid, q)
    else:
        name, amount = parse_exp(lower)
        if name and amount and amount > 0:
            await do_add(update, uid, name, amount, mode, user)
        else:
            await update.message.reply_text(
                "❓ Samajh nahi aaya!\n\nTry: *sabzi 50*\n/help", parse_mode='Markdown')

async def do_add(update, uid, name, amount, mode, user):
    cat = get_cat(name)
    cap = name.capitalize()
    add_expense_db(uid, {'name':cap,'amount':amount,'category':cat,'mode':mode,'date':datetime.now().isoformat()})
    exps = [e for e in get_expenses(uid) if e.get('mode')==mode]
    total = sum(e['amount'] for e in exps)

    warn = ''
    budget = user.get('budget')
    if budget:
        now = datetime.now()
        spent = sum(e['amount'] for e in exps if datetime.fromisoformat(e['date']).month==now.month)
        pct = (spent/budget)*100
        if pct >= 100: warn = f"\n\n🔴 *Budget khatam!* ₹{budget:,.0f} se zyada!"
        elif pct >= 80: warn = f"\n\n⚠️ Budget ka *{pct:.0f}%* use ho gaya!"

    await update.message.reply_text(
        f"✅ *{cap}* add!\n{cat} — ₹{amount:,.0f}\n"
        f"{'👤' if mode=='personal' else '💼'} Total: *₹{total:,.0f}*{warn}",
        parse_mode='Markdown')

async def cmd_total(update, uid, mode):
    exps = [e for e in get_expenses(uid) if e.get('mode')==mode]
    if not exps:
        await update.message.reply_text("📊 Koi entry nahi!\nShuru karo: *sabzi 50*", parse_mode='Markdown'); return
    cat_map = {}
    for e in exps: cat_map[e['category']] = cat_map.get(e['category'],0) + e['amount']
    total = sum(e['amount'] for e in exps)
    lines = '\n'.join([f"{c}: ₹{a:,.0f}" for c,a in sorted(cat_map.items(),key=lambda x:-x[1])])
    await update.message.reply_text(
        f"📊 *{'👤 Personal' if mode=='personal' else '💼 Business'} Summary*\n\n{lines}\n\n"
        f"━━━━━━━━━━\n💰 *Total: ₹{total:,.0f}*\n📝 {len(exps)} entries", parse_mode='Markdown')

async def cmd_today(update, uid, mode):
    today = datetime.now().date()
    exps = [e for e in get_expenses(uid) if e.get('mode')==mode and datetime.fromisoformat(e['date']).date()==today]
    if not exps: await update.message.reply_text("📅 Aaj koi kharch nahi!"); return
    lines = '\n'.join([f"• {e['category']} *{e['name']}*: ₹{e['amount']:,.0f}" for e in exps])
    await update.message.reply_text(
        f"📅 *Aaj Ka Kharch*\n\n{lines}\n\n*Total: ₹{sum(e['amount'] for e in exps):,.0f}*",
        parse_mode='Markdown')

async def cmd_list(update, uid):
    all_exp = get_expenses(uid)
    if not all_exp: await update.message.reply_text("📋 Koi entry nahi!"); return
    recent = all_exp[-10:][::-1]
    lines = []
    for e in recent:
        d = datetime.fromisoformat(e['date']).strftime('%d %b')
        icon = '👤' if e.get('mode')=='personal' else '💼'
        lines.append(f"{icon} {e['category']} *{e['name']}*: ₹{e['amount']:,.0f} _{d}_")
    grand = sum(e['amount'] for e in all_exp)
    await update.message.reply_text(
        f"📋 *Last 10 Entries*\n\n"+'\n'.join(lines)+f"\n\n💰 *Grand Total: ₹{grand:,.0f}*",
        parse_mode='Markdown')

async def cmd_budget_set(update, uid, user, text):
    try:
        amt = float(text.split()[-1]); user['budget'] = amt; save_user(uid, user)
        await update.message.reply_text(f"✅ Budget: *₹{amt:,.0f}/month*\n80% hone pe alert!", parse_mode='Markdown')
    except: await update.message.reply_text("❌ Format: *budget set 5000*", parse_mode='Markdown')

async def cmd_budget_check(update, uid, user):
    budget = user.get('budget')
    if not budget: await update.message.reply_text("Budget nahi! Type: *budget set 5000*", parse_mode='Markdown'); return
    now = datetime.now()
    spent = sum(e['amount'] for e in get_expenses(uid) if datetime.fromisoformat(e['date']).month==now.month)
    pct = (spent/budget)*100
    emoji = '🟢' if pct<60 else '🟡' if pct<80 else '🔴'
    await update.message.reply_text(
        f"💰 *Budget Report*\n\nBudget: ₹{budget:,.0f}\nKharch: ₹{spent:,.0f}\nBacha: ₹{max(0,budget-spent):,.0f}\n\n{emoji} *{pct:.0f}%* use",
        parse_mode='Markdown')

async def cmd_delete_last(update, uid):
    db = load_json("expenses.json"); k = str(uid)
    if k in db and db[k]:
        d = db[k].pop(); save_json("expenses.json", db)
        await update.message.reply_text(f"🗑️ Delete: *{d['name']}* — ₹{d['amount']:,.0f}", parse_mode='Markdown')
    else: await update.message.reply_text("Koi entry nahi!")

async def cmd_search(update, uid, query):
    results = [e for e in get_expenses(uid) if query in e['name'].lower() or query in e['category'].lower()]
    if not results: await update.message.reply_text(f"❌ '{query}' nahi mila!"); return
    lines = [f"• {e['category']} *{e['name']}*: ₹{e['amount']:,.0f}" for e in results[-10:]]
    await update.message.reply_text(
        f"🔍 *'{query}'*\n\n"+'\n'.join(lines)+f"\n\nTotal: ₹{sum(e['amount'] for e in results):,.0f}",
        parse_mode='Markdown')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; user = get_user(uid)
    mode = user.get('mode','personal') if user else 'personal'
    if mode == 'personal':
        text = ("👤 *Personal Help*\n\n"
                "➕ Add: `sabzi 50` `chai 20` `petrol 200`\n"
                "📊 Report: `total batao` `aaj ka kharch` `list dikhao`\n"
                "💰 Budget: `budget set 5000` `budget check`\n"
                "🔍 Search: `search petrol`\n"
                "🗑️ Undo: `delete last`\n\n"
                "⚙️ /mode /upgrade /status")
    else:
        text = ("💼 *Business Help*\n\n"
                "➕ Kharch: `rent 15000` `staff salary 8000`\n"
                "💰 Income: `client Ram 5000`\n"
                "🤝 Udhar: `udhar Shyam 2000`\n"
                "📊 Report: `total batao` `aaj ka kharch` `list dikhao`\n"
                "🔍 Search: `search salary`\n"
                "🗑️ Undo: `delete last`\n\n"
                "⚙️ /mode /upgrade /status")
    await update.message.reply_text(text, parse_mode='Markdown')

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; user = get_user(uid)
    if not user: await update.message.reply_text("Pehle /start karein!"); return
    dl = days_left(user); trial = is_trial(user)
    all_exp = get_expenses(uid); total = sum(e['amount'] for e in all_exp)
    mode = user.get('mode','personal')
    await update.message.reply_text(
        f"👤 *Aapki Profile*\n\n"
        f"📱 {user.get('phone','N/A')}\n📧 {user.get('email','N/A')}\n"
        f"Mode: {'👤 Personal' if mode=='personal' else '💼 Business'}\n\n"
        f"{'🎁 Free trial: *'+str(dl)+' din baaki*' if trial else '✅ Paid Member'}\n\n"
        f"📝 Entries: {len(all_exp)}\n💰 Total: ₹{total:,.0f}",
        parse_mode='Markdown')

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            MODE:  [CallbackQueryHandler(choose_mode_cb, pattern='^mode_')],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler('mode', change_mode))
    app.add_handler(CommandHandler('upgrade', upgrade))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CommandHandler('approve', approve_cmd))
    app.add_handler(CommandHandler('reject', reject_cmd))
    app.add_handler(CommandHandler('stats', stats_cmd))
    app.add_handler(CallbackQueryHandler(switch_mode_cb, pattern='^sw_'))
    app.add_handler(CallbackQueryHandler(show_qr, pattern='^pay_'))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 MunimJi Bot Live!")
    app.run_polling()

if __name__ == '__main__':
    main()
