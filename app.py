#!/usr/bin/env python3
import os
import sys
import logging
import requests
import asyncio
from typing import Dict, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    error_msg = "TELEGRAM_TOKEN environment variable is not set"
    logger.error(error_msg)
    raise ValueError(error_msg)

# GitHub RAW JSON URL - Replace with your actual URL
PRODUCTS_URL = os.getenv('PRODUCTS_URL', 'https://raw.githubusercontent.com/karthimathi/Boo_Boo_Product_Bot/main/products.json')

class ProductBot:
    """Main bot class to handle all commands and product fetching"""
    
    def __init__(self):
        self.products_cache: Optional[Dict] = None
        
    def fetch_products(self) -> Dict:
        """Fetch product data from GitHub JSON file"""
        try:
            logger.info(f"Fetching products from {PRODUCTS_URL}")
            response = requests.get(PRODUCTS_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Validate JSON structure
            if 'phones' not in data or 'laptops' not in data:
                raise ValueError("Invalid JSON structure: missing 'phones' or 'laptops' keys")
                
            logger.info(f"Successfully fetched {len(data.get('phones', []))} phones and {len(data.get('laptops', []))} laptops")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching products: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def format_product_caption(self, product: Dict, category: str) -> str:
        """Format product caption with emojis for better conversion"""
        name = product.get('name', 'N/A')
        price = product.get('price', 'N/A')
        link = product.get('link', '#')
        
        # Category-specific emojis
        category_emoji = "📱" if category == "phone" else "💻"
        
        caption = f"""
{category_emoji} *{name}*

💰 *Price:* {price}

🔗 [Click Here to Buy]({link})

⚡ *Limited Stock Available!*
✨ Shop now and get best deals! 

👉 *Tap the link above to purchase*
        """
        return caption.strip()
    
    async def send_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product: Dict, category: str):
        """Send a single product with photo and caption"""
        try:
            image_url = product.get('image')
            if not image_url:
                logger.warning(f"No image URL for product: {product.get('name')}")
                await update.message.reply_text(f"⚠️ {product.get('name')} - Image not available")
                return False
                
            caption = self.format_product_caption(product, category)
            
            await update.message.reply_photo(
                photo=image_url,
                caption=caption,
                parse_mode='Markdown'
            )
            return True
            
        except Exception as e:
            logger.error(f"Error sending product {product.get('name')}: {e}")
            await update.message.reply_text(f"❌ Error displaying product: {product.get('name')}")
            return False

# Bot instance
bot_instance = ProductBot()

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with instructions"""
    welcome_text = """
🎉 *Welcome to Products Bot!* 🎉

Your one-stop shop for best deals on phones and laptops!

📌 *Available Commands:*

/phones - 📱 Browse all mobile phones
/laptops - 💻 Browse all laptops

🌟 *Features:*
• Direct purchase links
• Best price guarantee
• Daily updated products

💡 *Tip:* Click on the product link to buy directly!

*Happy Shopping!* 🛍️
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    logger.info(f"User {update.effective_user.id} started the bot")

async def show_phones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all phone products"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested phones")
    
    # Send typing action
    await update.message.chat.send_action(action="typing")
    
    # Fetch products
    products_data = bot_instance.fetch_products()
    
    if not products_data:
        await update.message.reply_text(
            "❌ *Sorry!* Unable to fetch products right now.\n"
            "Please try again later. 🔄",
            parse_mode='Markdown'
        )
        return
    
    phones = products_data.get('phones', [])
    
    if not phones:
        await update.message.reply_text(
            "📱 *No phones available at the moment!*\n"
            "Please check back later. 🔄",
            parse_mode='Markdown'
        )
        return
    
    # Send count message
    await update.message.reply_text(
        f"📱 *Found {len(phones)} phones for you!*\n"
        f"⬇️ Scroll down to see all deals ⬇️\n",
        parse_mode='Markdown'
    )
    
    # Send each product
    for product in phones:
        await bot_instance.send_product(update, context, product, "phone")
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    await update.message.reply_text(
        "✅ *All products displayed!*\n"
        "Click on any link to buy now! 🎯",
        parse_mode='Markdown'
    )

async def show_laptops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all laptop products"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested laptops")
    
    # Send typing action
    await update.message.chat.send_action(action="typing")
    
    # Fetch products
    products_data = bot_instance.fetch_products()
    
    if not products_data:
        await update.message.reply_text(
            "❌ *Sorry!* Unable to fetch products right now.\n"
            "Please try again later. 🔄",
            parse_mode='Markdown'
        )
        return
    
    laptops = products_data.get('laptops', [])
    
    if not laptops:
        await update.message.reply_text(
            "💻 *No laptops available at the moment!*\n"
            "Please check back later. 🔄",
            parse_mode='Markdown'
        )
        return
    
    # Send count message
    await update.message.reply_text(
        f"💻 *Found {len(laptops)} laptops for you!*\n"
        f"⬇️ Scroll down to see all deals ⬇️\n",
        parse_mode='Markdown'
    )
    
    # Send each product
    for product in laptops:
        await bot_instance.send_product(update, context, product, "laptop")
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    await update.message.reply_text(
        "✅ *All products displayed!*\n"
        "Click on any link to buy now! 🎯",
        parse_mode='Markdown'
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ *Something went wrong!*\n"
            "Please try again later or contact support.\n"
            "🔄 Use /start to reset the bot.",
            parse_mode='Markdown'
        )

def main():
    """Start the bot"""
    try:
        logger.info("Initializing bot application...")
        
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("phones", show_phones))
        application.add_handler(CommandHandler("laptops", show_laptops))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        logger.info("Bot is starting and polling for updates...")
        
        # Start polling (this will run until interrupted)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    logger.info("Starting bot process...")
    main()
