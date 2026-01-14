"""
Telegram Bot untuk SheerID Student Verification
Mendukung auto-select dari daftar universitas top atau manual input
"""
import os
import sys
import logging
import asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Handle imports for both direct execution and module execution
try:
    from . import config
    from .sheerid_verifier import SheerIDVerifier
    from .name_generator import NameGenerator, generate_birth_date
except ImportError:
    # Running as direct script, use absolute imports
    import config
    from sheerid_verifier import SheerIDVerifier
    from name_generator import NameGenerator, generate_birth_date

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSE_MODE,
    AUTO_SELECT_SCHOOL,
    MANUAL_SCHOOL,
    MANUAL_FIRST_NAME,
    MANUAL_LAST_NAME,
    MANUAL_EMAIL,
    MANUAL_BIRTH_DATE,
    CONFIRM_DATA,
    ENTER_URL,
) = range(9)

# Pagination settings
SCHOOLS_PER_PAGE = 7


def get_schools_by_state() -> Dict[str, list]:
    """Group schools by state for organized display"""
    schools_by_state = {}
    for school_id, school in config.SCHOOLS.items():
        state = school['state']
        if state not in schools_by_state:
            schools_by_state[state] = []
        schools_by_state[state].append({
            'id': school_id,
            'name': school['name'],
            'city': school['city'],
            'state': state
        })
    return schools_by_state


def create_school_keyboard(page: int = 0):
    """Create paginated keyboard for school selection"""
    all_schools = []
    for school_id, school in config.SCHOOLS.items():
        all_schools.append({
            'id': school_id,
            'name': school['name'],
            'city': school['city'],
            'state': school['state']
        })
    
    # Sort by state then name
    all_schools.sort(key=lambda x: (x['state'], x['name']))
    
    # Calculate pagination
    total_schools = len(all_schools)
    total_pages = (total_schools + SCHOOLS_PER_PAGE - 1) // SCHOOLS_PER_PAGE
    start_idx = page * SCHOOLS_PER_PAGE
    end_idx = min(start_idx + SCHOOLS_PER_PAGE, total_schools)
    
    schools_page = all_schools[start_idx:end_idx]
    
    keyboard = []
    for school in schools_page:
        button_text = f"🏫 {school['name']} ({school['city']}, {school['state']})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"school_{school['id']}")])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command - show mode selection"""
    keyboard = [
        [InlineKeyboardButton("🤖 Auto-Select School", callback_data="mode_auto")],
        [InlineKeyboardButton("✏️ Manual Input", callback_data="mode_manual")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎓 *SheerID Student Verification Bot*\n\n"
        "Pilih mode verifikasi:\n\n"
        "🤖 *Auto-Select School*\n"
        "Pilih universitas dari daftar 35 top US universities\n"
        "Bot akan otomatis generate nama, email, dan tanggal lahir\n\n"
        "✏️ *Manual Input*\n"
        "Masukkan semua data secara manual\n"
        "(nama, email, tanggal lahir, dan universitas)"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return CHOOSE_MODE


async def mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle mode selection"""
    query = update.callback_query
    await query.answer()
    
    mode = query.data.split("_")[1]
    context.user_data['mode'] = mode
    
    if mode == 'auto':
        # Show school selection
        keyboard = create_school_keyboard(page=0)
        await query.message.edit_text(
            "🏫 *Pilih Universitas*\n\n"
            "Pilih salah satu universitas dari daftar di bawah ini:\n"
            "(Sorted by state)",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return AUTO_SELECT_SCHOOL
    else:
        # Start manual input flow
        await query.message.edit_text(
            "✏️ *Manual Input Mode*\n\n"
            "Silakan masukkan nama universitas:"
        )
        return MANUAL_SCHOOL


async def handle_school_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle school selection in auto mode"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("page_"):
        if query.data == "page_info":
            return AUTO_SELECT_SCHOOL
        page = int(query.data.split("_")[1])
        keyboard = create_school_keyboard(page=page)
        await query.message.edit_reply_markup(reply_markup=keyboard)
        return AUTO_SELECT_SCHOOL
    
    elif query.data.startswith("school_"):
        school_id = query.data.split("_")[1]
        context.user_data['school_id'] = school_id
        
        school = config.SCHOOLS[school_id]
        
        # Auto-generate student data
        name = NameGenerator.generate()
        context.user_data['first_name'] = name['first_name']
        context.user_data['last_name'] = name['last_name']
        
        # Generate email based on school domain
        email = f"{name['first_name'].lower()}.{name['last_name'].lower()}@{school['domain']}"
        context.user_data['email'] = email
        
        birth_date = generate_birth_date()
        context.user_data['birth_date'] = birth_date
        
        summary = (
            f"✅ *Data Verifikasi*\n\n"
            f"🏫 *Universitas:* {school['name']}\n"
            f"📍 *Lokasi:* {school['city']}, {school['state']}\n\n"
            f"👤 *Nama:* {name['first_name']} {name['last_name']}\n"
            f"📧 *Email:* {email}\n"
            f"🎂 *Tanggal Lahir:* {birth_date}\n\n"
            f"Silakan kirim SheerID verification URL sekarang:"
        )
        
        await query.message.edit_text(summary, parse_mode='Markdown')
        return ENTER_URL
    
    elif query.data == "cancel":
        return await cancel(update, context)


async def manual_school(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual school name input"""
    school_name = update.message.text.strip()
    context.user_data['manual_school_name'] = school_name
    
    await update.message.reply_text(
        f"✅ Universitas: {school_name}\n\n"
        "Silakan masukkan *First Name* / Nama Depan:"
    )
    return MANUAL_FIRST_NAME


async def manual_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual first name input"""
    first_name = update.message.text.strip()
    context.user_data['first_name'] = first_name
    
    await update.message.reply_text(
        f"✅ First Name: {first_name}\n\n"
        "Silakan masukkan *Last Name* / Nama Belakang:",
        parse_mode='Markdown'
    )
    return MANUAL_LAST_NAME


async def manual_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual last name input"""
    last_name = update.message.text.strip()
    context.user_data['last_name'] = last_name
    
    await update.message.reply_text(
        f"✅ Last Name: {last_name}\n\n"
        "Silakan masukkan *Email Address*:\n"
        "(Format: name@university.edu)",
        parse_mode='Markdown'
    )
    return MANUAL_EMAIL


async def manual_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual email input"""
    email = update.message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        await update.message.reply_text(
            "❌ Format email tidak valid!\n\n"
            "Silakan masukkan email yang valid (contoh: john.doe@university.edu):"
        )
        return MANUAL_EMAIL
    
    context.user_data['email'] = email
    
    await update.message.reply_text(
        f"✅ Email: {email}\n\n"
        "Silakan masukkan *Tanggal Lahir*:\n"
        "(Format: YYYY-MM-DD, contoh: 2000-01-15)",
        parse_mode='Markdown'
    )
    return MANUAL_BIRTH_DATE


async def manual_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual birth date input"""
    birth_date = update.message.text.strip()
    
    # Basic date validation
    if len(birth_date) != 10 or birth_date.count('-') != 2:
        await update.message.reply_text(
            "❌ Format tanggal tidak valid!\n\n"
            "Silakan masukkan tanggal dengan format YYYY-MM-DD (contoh: 2000-01-15):"
        )
        return MANUAL_BIRTH_DATE
    
    context.user_data['birth_date'] = birth_date
    
    # Show summary and ask for URL
    summary = (
        f"✅ *Data Verifikasi Lengkap*\n\n"
        f"🏫 *Universitas:* {context.user_data['manual_school_name']}\n"
        f"👤 *Nama:* {context.user_data['first_name']} {context.user_data['last_name']}\n"
        f"📧 *Email:* {context.user_data['email']}\n"
        f"🎂 *Tanggal Lahir:* {birth_date}\n\n"
        f"Silakan kirim SheerID verification URL sekarang:"
    )
    
    await update.message.reply_text(summary, parse_mode='Markdown')
    return ENTER_URL


async def enter_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle SheerID URL input and start verification"""
    url = update.message.text.strip()
    
    # Parse verification ID
    verification_id = SheerIDVerifier.parse_verification_id(url)
    
    if not verification_id:
        await update.message.reply_text(
            "❌ *Invalid URL!*\n\n"
            "URL harus mengandung verificationId parameter.\n"
            "Contoh format:\n"
            "`https://services.sheerid.com/verify/...?verificationId=abc123`\n\n"
            "Silakan kirim URL yang valid:",
            parse_mode='Markdown'
        )
        return ENTER_URL
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "⏳ *Memproses verifikasi...*\n\n"
        "Mohon tunggu, bot sedang:\n"
        "▪️ Mengenerate student ID card\n"
        "▪️ Mengirim data ke SheerID\n"
        "▪️ Mengupload dokumen",
        parse_mode='Markdown'
    )
    
    try:
        # Create verifier instance
        verifier = SheerIDVerifier(verification_id)
        
        # Run verification in a separate thread to avoid Playwright sync API conflict
        # with asyncio event loop
        if context.user_data['mode'] == 'auto':
            result = await asyncio.to_thread(
                verifier.verify,
                first_name=context.user_data['first_name'],
                last_name=context.user_data['last_name'],
                email=context.user_data['email'],
                birth_date=context.user_data['birth_date'],
                school_id=context.user_data['school_id']
            )
        else:
            # Manual mode - need to find matching school or use a default
            # For manual mode, we'll use a random school from the list
            # User provided school name is just for reference
            import random
            random_school_id = random.choice(list(config.SCHOOLS.keys()))
            
            result = await asyncio.to_thread(
                verifier.verify,
                first_name=context.user_data['first_name'],
                last_name=context.user_data['last_name'],
                email=context.user_data['email'],
                birth_date=context.user_data['birth_date'],
                school_id=random_school_id
            )
        
        # Update message with result
        if result['success']:
            status_emoji = "✅" if not result.get('pending') else "⏳"
            status_text = "Pending Review" if result.get('pending') else "Verified"
            
            result_text = (
                f"{status_emoji} *Verification {status_text}*\n\n"
                f"📋 *Verification ID:* `{verification_id}`\n"
                f"💬 *Message:* {result['message']}\n\n"
            )
            
            if result.get('redirect_url'):
                result_text += f"🔗 *Redirect URL:*\n{result['redirect_url']}\n\n"
            
            result_text += "Gunakan /start untuk verifikasi baru"
            
            await processing_msg.edit_text(result_text, parse_mode='Markdown')
        else:
            error_text = (
                f"❌ *Verification Failed*\n\n"
                f"📋 *Verification ID:* `{verification_id}`\n"
                f"❗ *Error:* {result['message']}\n\n"
                f"Silakan coba lagi dengan /start"
            )
            await processing_msg.edit_text(error_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        await processing_msg.edit_text(
            f"❌ *Error*\n\n"
            f"Terjadi kesalahan: {str(e)}\n\n"
            f"Silakan coba lagi dengan /start",
            parse_mode='Markdown'
        )
    
    # Clear user data and end conversation
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation"""
    if update.callback_query:
        await update.callback_query.message.edit_text(
            "❌ Operasi dibatalkan.\n\n"
            "Gunakan /start untuk memulai lagi."
        )
    else:
        await update.message.reply_text(
            "❌ Operasi dibatalkan.\n\n"
            "Gunakan /start untuk memulai lagi."
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = (
        "🤖 *SheerID Student Verification Bot*\n\n"
        "*Commands:*\n"
        "/start - Mulai verifikasi baru\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "*How to use:*\n"
        "1. Send /start command\n"
        "2. Choose Auto-Select or Manual Input mode\n"
        "3. Follow the prompts\n"
        "4. Paste your SheerID verification URL\n"
        "5. Wait for verification result\n\n"
        "*Supported Universities:*\n"
        "35 top US universities including:\n"
        "▪️ Stanford, MIT, Harvard\n"
        "▪️ Yale, Princeton, Columbia\n"
        "▪️ UC Berkeley, UCLA, Caltech\n"
        "▪️ And many more!\n\n"
        "For issues, contact support."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


def main():
    """Start the bot"""
    # Get bot token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with your bot token.")
        logger.error("Example: TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Setup conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_MODE: [
                CallbackQueryHandler(mode_selected, pattern='^mode_')
            ],
            AUTO_SELECT_SCHOOL: [
                CallbackQueryHandler(handle_school_selection)
            ],
            MANUAL_SCHOOL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_school)
            ],
            MANUAL_FIRST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_first_name)
            ],
            MANUAL_LAST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_last_name)
            ],
            MANUAL_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_email)
            ],
            MANUAL_BIRTH_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_birth_date)
            ],
            ENTER_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_url)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^cancel$')
        ],
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    # Start bot
    logger.info("🤖 Bot started successfully. Polling for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
