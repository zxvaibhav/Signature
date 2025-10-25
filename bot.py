#!/usr/bin/env python3
"""
APK Signing Certificate Generator - MT Manager Style
Telegram Bot Version
Creates: .jks, .keystore for APK signing
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bot Configuration
BOT_TOKEN = ""  # Replace with your bot token
API_ID = "20088778"        # Replace with your API ID
API_HASH = "331f2d7782d1eb9ecf4c6ff0ac0ddcda"    # Replace with your API Hash
ADMIN_IDS = [5827445104]            # Replace with your admin user IDs

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class APKSigningBot:
    def __init__(self):
        self.cert_dir = "APK_Signing_Keys"
        self.current_user_data = {}

    def check_keytool(self):
        """Check if keytool is available"""
        try:
            subprocess.run(["keytool", "-help"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def install_java(self):
        """Install Java if not available"""
        try:
            logger.info("Installing Java...")
            subprocess.run(["pkg", "update", "-y"], check=True)
            subprocess.run(["pkg", "install", "-y", "openjdk-17"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Java: {e}")
            return False

    def generate_keystore(self, user_data):
        """Generate JKS keystore and related files"""
        try:
            # Create working directory
            os.makedirs(self.cert_dir, exist_ok=True)
            os.chdir(self.cert_dir)

            # Prepare variables
            alias_name = user_data.get('alias_name', 'mykey')
            org_name = user_data.get('org_name', 'MyCompany')
            org_unit = user_data.get('org_unit', 'IT')
            city = user_data.get('city', 'Mumbai')
            state = user_data.get('state', 'Maharashtra')
            country = user_data.get('country', 'IN')
            store_pass = user_data.get('store_pass', 'android')
            key_pass = user_data.get('key_pass', store_pass)
            validity_years = int(user_data.get('validity_years', 25))
            validity_days = validity_years * 365

            dname = f"CN={alias_name}, OU={org_unit}, O={org_name}, L={city}, ST={state}, C={country}"

            # Generate JKS Keystore
            cmd = [
                "keytool", "-genkey", "-v",
                "-keystore", "android.jks",
                "-alias", alias_name,
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", str(validity_days),
                "-storepass", store_pass,
                "-keypass", key_pass,
                "-dname", dname
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"Failed to create JKS: {result.stderr}"

            # Export certificate
            export_cmd = [
                "keytool", "-export", "-rfc",
                "-alias", alias_name,
                "-keystore", "android.jks",
                "-storepass", store_pass,
                "-file", "certificate.cer"
            ]
            subprocess.run(export_cmd, capture_output=True)

            # Create PKCS12
            pkcs12_cmd = [
                "keytool", "-importkeystore",
                "-srckeystore", "android.jks",
                "-destkeystore", "android.p12",
                "-deststoretype", "PKCS12",
                "-srcstorepass", store_pass,
                "-deststorepass", store_pass
            ]
            subprocess.run(pkcs12_cmd, capture_output=True)

            # Create scripts
            self.create_scripts(alias_name, store_pass, key_pass, validity_years)

            return True, "Keystore generated successfully!"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def create_scripts(self, alias_name, store_pass, key_pass, validity_years):
        """Create signing and verification scripts"""
        
        # sign_apk.sh
        sign_apk_script = f'''#!/bin/bash
echo "🤖 APK Signing Tool - MT Manager Style"
echo "======================================"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <app.apk>"
    echo "Example: $0 myapp.apk"
    exit 1
fi

APK_FILE="$1"
SIGNED_APK="signed_$APK_FILE"

if [ ! -f "$APK_FILE" ]; then
    echo "❌ APK file not found: $APK_FILE"
    exit 1
fi

if [ ! -f "android.jks" ]; then
    echo "❌ Keystore not found: android.jks"
    exit 1
fi

echo "📦 Signing APK: $APK_FILE"

# Remove existing signature (if any)
zip -d "$APK_FILE" "META-INF/*" 2>/dev/null

# Sign the APK
jarsigner -verbose \\
    -keystore "android.jks" \\
    -storepass "{store_pass}" \\
    -keypass "{key_pass}" \\
    -sigalg SHA256withRSA \\
    -digestalg SHA-256 \\
    "$APK_FILE" \\
    "{alias_name}"

if [ $? -eq 0 ]; then
    echo "✅ APK signed successfully!"
    echo "📁 Signed APK: $APK_FILE"
    
    # Verify signature
    echo "🔍 Verifying signature..."
    jarsigner -verify -verbose "$APK_FILE"
else
    echo "❌ APK signing failed!"
fi
'''

        with open("sign_apk.sh", "w") as f:
            f.write(sign_apk_script)
        os.chmod("sign_apk.sh", 0o755)

        # Create README
        readme_content = f'''APK SIGNING CERTIFICATE - MT MANAGER STYLE
==========================================

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📁 FILES CREATED:
----------------
1. android.jks       - Java Keystore (Main file for APK signing)
2. android.p12       - PKCS12 Keystore (Alternative format)
3. certificate.cer   - Public Certificate
4. sign_apk.sh       - APK signing script

🔑 PASSWORDS:
------------
Keystore Password: {store_pass}
Key Password: {key_pass}
Alias: {alias_name}

🚀 HOW TO SIGN APK:
------------------
1. Copy your APK to this folder
2. Run: ./sign_apk.sh your_app.apk

📱 USING IN MT MANAGER:
----------------------
1. Copy 'android.jks' to your phone
2. In MT Manager, open APK file
3. Go to: Function -> APK Signature
4. Choose: Signature Scheme v1/v2/v3
5. Select your .jks file and enter password

⚠️  IMPORTANT:
-------------
- Keep 'android.jks' file safe and secure
- Don't lose the password - it cannot be recovered
- Backup your keystore files

Validity: {validity_years} years
Generated for: {alias_name}
'''

        with open("README_APK_SIGNING.txt", "w") as f:
            f.write(readme_content)

# Telegram Bot Handlers
bot = APKSigningBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when command /start is issued."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    welcome_text = """
🤖 *APK Signing Certificate Generator Bot* 🤖

I can generate APK signing certificates compatible with MT Manager!

*Available Commands:*
/start - Show this welcome message
/generate - Generate new APK signing certificate
/cancel - Cancel current operation

*How to use:*
1. Send /generate to start
2. Follow the prompts to enter certificate details
3. I'll create your keystore files!

*Supported Formats:*
• JKS (Java Keystore)
• PKCS12
• CER Certificate
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def generate_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the certificate generation process."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    # Initialize user data
    bot.current_user_data[user_id] = {}
    
    await update.message.reply_text(
        "🔐 *Let's create your APK signing certificate!*\n\n"
        "Please enter your *Name/Alias* for the certificate:",
        parse_mode='Markdown'
    )
    
    # Set next expected input
    context.user_data['expecting'] = 'alias_name'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages during certificate generation."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    if user_id not in bot.current_user_data:
        await update.message.reply_text("Please use /generate to start creating a certificate.")
        return

    expecting = context.user_data.get('expecting', 'alias_name')
    user_data = bot.current_user_data[user_id]

    if expecting == 'alias_name':
        user_data['alias_name'] = text or 'mykey'
        context.user_data['expecting'] = 'org_name'
        await update.message.reply_text("🏢 Enter *Organization Name*:", parse_mode='Markdown')
        
    elif expecting == 'org_name':
        user_data['org_name'] = text or 'MyCompany'
        context.user_data['expecting'] = 'org_unit'
        await update.message.reply_text("🏢 Enter *Organizational Unit*:", parse_mode='Markdown')
        
    elif expecting == 'org_unit':
        user_data['org_unit'] = text or 'IT'
        context.user_data['expecting'] = 'city'
        await update.message.reply_text("🏙️ Enter *City*:", parse_mode='Markdown')
        
    elif expecting == 'city':
        user_data['city'] = text or 'Mumbai'
        context.user_data['expecting'] = 'state'
        await update.message.reply_text("🏛️ Enter *State*:", parse_mode='Markdown')
        
    elif expecting == 'state':
        user_data['state'] = text or 'Maharashtra'
        context.user_data['expecting'] = 'country'
        await update.message.reply_text("🇮🇳 Enter *Country Code* (e.g., IN):", parse_mode='Markdown')
        
    elif expecting == 'country':
        user_data['country'] = text or 'IN'
        context.user_data['expecting'] = 'store_pass'
        await update.message.reply_text("🔑 Enter *Keystore Password*:", parse_mode='Markdown')
        
    elif expecting == 'store_pass':
        user_data['store_pass'] = text or 'android'
        context.user_data['expecting'] = 'key_pass'
        await update.message.reply_text("🔐 Enter *Key Password* (or press Enter to use same as keystore):", parse_mode='Markdown')
        
    elif expecting == 'key_pass':
        user_data['key_pass'] = text or user_data.get('store_pass', 'android')
        context.user_data['expecting'] = 'validity_years'
        await update.message.reply_text("⏰ Enter *Validity in years* (default: 25):", parse_mode='Markdown')
        
    elif expecting == 'validity_years':
        user_data['validity_years'] = text or '25'
        
        # All data collected, generate certificate
        await update.message.reply_text("⏳ Generating your APK signing certificate...")
        
        # Check for keytool
        if not bot.check_keytool():
            await update.message.reply_text("🔧 keytool not found! Installing Java...")
            if not bot.install_java():
                await update.message.reply_text("❌ Failed to install Java. Please install manually.")
                del bot.current_user_data[user_id]
                return
        
        # Generate keystore
        success, message = bot.generate_keystore(user_data)
        
        if success:
            # Send success message and files
            await update.message.reply_text(
                f"✅ *Certificate Generated Successfully!*\n\n"
                f"📁 Files created in: `{bot.cert_dir}`\n"
                f"🔑 Alias: `{user_data['alias_name']}`\n"
                f"🏢 Organization: `{user_data['org_name']}`\n"
                f"⏰ Validity: `{user_data['validity_years']} years`\n\n"
                f"*Important:* Keep your keystore file safe!",
                parse_mode='Markdown'
            )
            
            # Send files (in a real implementation, you'd send the actual files)
            await update.message.reply_text(
                "📦 *Generated Files:*\n"
                "• `android.jks` - Main keystore file\n"
                "• `android.p12` - PKCS12 format\n"
                "• `certificate.cer` - Public certificate\n"
                "• `sign_apk.sh` - Signing script\n"
                "• `README_APK_SIGNING.txt` - Instructions",
                parse_mode='Markdown'
            )
            
        else:
            await update.message.reply_text(f"❌ *Error generating certificate:*\n`{message}`", parse_mode='Markdown')
        
        # Clean up
        del bot.current_user_data[user_id]
        context.user_data.clear()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation."""
    user_id = update.effective_user.id
    if user_id in bot.current_user_data:
        del bot.current_user_data[user_id]
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and handle them gracefully."""
    logger.error(f"Update {update} caused error {context.error}")
    await update.message.reply_text("❌ An error occurred. Please try again.")

def main():
    """Start the bot."""
    # Check for required configuration
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your BOT_TOKEN in the script!")
        sys.exit(1)
    
    if API_ID == "YOUR_API_ID_HERE":
        print("❌ Please set your API_ID in the script!")
        sys.exit(1)
    
    if API_HASH == "YOUR_API_HASH_HERE":
        print("❌ Please set your API_HASH in the script!")
        sys.exit(1)

    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_certificate))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Start the Bot
    print("🤖 APK Signing Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()