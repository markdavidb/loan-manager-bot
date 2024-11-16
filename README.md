# Loan Manager Bot 🤖

A Telegram bot for managing personal loans with secure authentication and payment tracking.  
Built as a practical project to enhance my knowledge in database management and async programming.
<div align="center">
  





https://github.com/user-attachments/assets/0b98158b-1d82-4799-8d84-81e672b58518





</div>

## Features ✨

- **Security** 🔐
  - Admin password authentication
  - Auto-ban system for multiple failed attempts

- **Loans** 💵
  - Create and track loans
  - Weekly/Monthly payments
  - Payment progress tracking

- **Management** 👤
  - Monitor payment history
  - Add/remove payments
  - Track borrower details

- **Search** 🔍
  - Search by borrower name
  - View all active loans
  - Paginated loan list

## Tech Stack 🛠
- Python 3.8+
- aiogram - Telegram Bot framework
- SQLAlchemy - Database ORM with async support
- PostgreSQL - Database
- asyncio - For asynchronous operations

## Setup 🚀

1. **Clone & Install**
```bash
git clone https://github.com/yourusername/loan-manager-bot.git
cd loan-manager-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure**
Create `.env` file:
```env
TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
BOT_PASSWORD=your_hashed_admin_password
```

3. **Run**
```bash
python run.py
```

## Commands 📱
- `/start` - Start bot
- `/auth [password]` - Admin authentication
- `/search` - Search loans
- `/ban`, `/unban` - User management (admin only)

## License 📝
MIT License
