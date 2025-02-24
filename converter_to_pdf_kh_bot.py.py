import logging
import os
import asyncio
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.error import TimedOut

# ➤ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8022472763:AAHsWU_1M7MREXWsrgckp7iuy8n8b531who"
IMAGE_FOLDER = "images"
PDF_FOLDER = "pdfs"
GROUP_ID = -4756090216  # ជំនួស Group ID របស់អ្នកនៅទីនេះ

# ➤ បង្កើតថតសម្រាប់រក្សារូបភាព និង PDF
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# ➤ ការប្រតិបត្តិបន្ថែមរូបភាព
async def handle_image(update: Update, context: CallbackContext):
    message_id = update.message.message_id  # ថត Message ID
    chat_id = update.message.chat_id  # Telegram User ID

    # ➤ ប្រសិនបើ message ID ម្តងហើយ កុំទៀត
    if "received_photos" not in context.user_data:
        context.user_data["received_photos"] = set()
    
    if message_id in context.user_data["received_photos"]:
        return  # មិនបញ្ជូនសារដដែលៗ

    context.user_data["received_photos"].add(message_id)  # រក្សាទុក Message ID

    # ➤ ទាញយក File ID (Resolution ខ្ពស់ជាងគេ)
    photo = update.message.photo[-1]
    file = await photo.get_file()

    file_path = os.path.join(IMAGE_FOLDER, f"{file.file_id}.jpg")
    await file.download_to_drive(file_path)

    await asyncio.sleep(1)  # ជៀសការបញ្ជូនលឿនពេក
    await update.message.reply_text("📥 រូបភាពត្រូវបានរក្សាទុក។ ប្រើ /convert ដើម្បីបម្លែងទៅ PDF។")

# ➤ បម្លែងរូបភាពទៅ PDF
async def convert_to_pdf(update: Update, context: CallbackContext):
    images = [os.path.join(IMAGE_FOLDER, f) for f in os.listdir(IMAGE_FOLDER) if f.endswith(".jpg")]

    if not images:
        await update.message.reply_text("⚠️ មិនមានរូបភាពសម្រាប់បម្លែងទេ។")
        return

    images.sort()
    pdf_path = os.path.join(PDF_FOLDER, f"{update.message.chat_id}.pdf")

    image_list = [Image.open(img).convert("RGB") for img in images]
    image_list[0].save(pdf_path, save_all=True, append_images=image_list[1:])

    for img in images:
        os.remove(img)

    await send_document_with_retry(update, context, pdf_path)

    # ➤ ផ្ញើឯកសារ PDF ទៅកាន់ Group
    await send_document_to_group(context, pdf_path)

# ➤ ការបញ្ជូនឯកសារជា PDF (មាន retry)
async def send_document_with_retry(update, context, pdf_file):
    for attempt in range(3):  # ព្យាយាមអោយបាន 3 ដង
        try:
            await update.message.reply_document(pdf_file, caption="📄 PDF របស់អ្នក!")
            return
        except TimedOut:
            if attempt < 2:
                await asyncio.sleep(5)  # រង់ចាំ 5 វិនាទី
            else:
                await update.message.reply_text("⏳ Server Telegram យឺត, សូមព្យាយាមម្ដងទៀត! 😓")

# ➤ ផ្ញើឯកសារ PDF ទៅកាន់ Group
async def send_document_to_group(context, pdf_file):
    for attempt in range(3):  # ព្យាយាមអោយបាន 3 ដង
        try:
            await context.bot.send_document(chat_id=GROUP_ID, document=open(pdf_file, "rb"), caption="📄 PDF ថ្មីត្រូវបានបង្កើត!")
            return
        except TimedOut:
            if attempt < 2:
                await asyncio.sleep(5)  # រង់ចាំ 5 វិនាទី
            else:
                logger.error("Failed to send PDF to group after 3 attempts.")

# ➤ ការចាប់ផ្តើម Bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 សួស្តី! ផ្ញើរូបភាព ហើយប្រើ /convert ដើម្បីបម្លែងទៅ PDF។")

# ➤ បង្កើត Application
app = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).build()

# ➤ បន្ថែម Handler
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(CommandHandler("convert", convert_to_pdf))

# ➤ ចាប់ផ្តើម Bot
print("🤖 Bot កំពុងដំណើរការ... ចុច Ctrl + C ដើម្បីបញ្ឈប់។")
app.run_polling()