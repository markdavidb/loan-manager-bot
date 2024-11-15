from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# Main menu keyboard
def main():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(
        KeyboardButton(text="New Loan"),
        KeyboardButton(text="Search Loans"),
        KeyboardButton(text="View All Loans")
    )
    return keyboard.adjust(2).as_markup(resize_keyboard=True)


def cancel_kb():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="❌ Cancel"))
    return keyboard.adjust(1).as_markup(resize_keyboard=True)


def frequency_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="Weekly", callback_data="freq_weekly"),
        InlineKeyboardButton(text="Monthly", callback_data="freq_monthly")
    )
    return keyboard.adjust(2).as_markup()


# Add this to keyboards.py
def confirm_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_loan"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_loan")
    )
    return keyboard.adjust(2).as_markup()


def loan_details_keyboard(loan_id: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(
            text="➖ Remove Payment",
            callback_data=f"decrease_{loan_id}"
        ),
        InlineKeyboardButton(
            text="➕ Add Payment",
            callback_data=f"increase_{loan_id}"
        ),
    )
    keyboard.add(
        InlineKeyboardButton(
            text="🔙 Back to Loans",
            callback_data="back_to_loans"
        )
    )
    return keyboard.adjust(2).as_markup()


def loans_list_keyboard(loans, current_page=0, loans_per_page=5):
    keyboard = InlineKeyboardBuilder()

    start_idx = current_page * loans_per_page
    end_idx = start_idx + loans_per_page
    page_loans = loans[start_idx:end_idx]
    total_pages = (len(loans) + loans_per_page - 1) // loans_per_page

    for loan in page_loans:
        button_text = f"{loan['person_name']} - ${loan['remaining_amount']:,.2f}"
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"view_loan_{loan['id']}"
        ))

    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Previous",
            callback_data=f"page_{current_page - 1}"
        ))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Next ▶️",
            callback_data=f"page_{current_page + 1}"
        ))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    keyboard.row(InlineKeyboardButton(
        text=f"Page {current_page + 1} of {total_pages}",
        callback_data="page_info"
    ))

    return keyboard.adjust(1).as_markup()


def search_filters_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🔍 Search by Name", callback_data="search_name")
        # InlineKeyboardButton(text="💰 Search by Amount", callback_data="search_amount"),
        # InlineKeyboardButton(text="📅 Search by Date", callback_data="search_date"),
        # InlineKeyboardButton(text="📊 Status", callback_data="search_status")
    )

    return keyboard.adjust(2).as_markup()


def inline_cancel_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_search")
    )
    return keyboard.adjust(1).as_markup()
