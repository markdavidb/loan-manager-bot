from datetime import timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


from app.keyboards import *
from app.database import requests as rq
from security import rate_limit, auth_required, check_password

router = Router()


class AuthStates(StatesGroup):
    awaiting_password = State()


class LoanStates(StatesGroup):
    getting_name = State()
    getting_amount = State()
    getting_frequency = State()
    getting_payments = State()
    confirming_loan = State()


class SearchStates(StatesGroup):
    awaiting_name = State()
    awaiting_min_amount = State()
    awaiting_max_amount = State()
    awaiting_start_date = State()
    awaiting_end_date = State()
    awaiting_status = State()


# Start command
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id

    if await rq.is_user_authorized(user_id):
        await message.answer(
            "Welcome to Loan Manager Bot!\nUse the buttons below to manage loans:",
            reply_markup=main()
        )
    else:
        await message.answer(
            "Welcome! You are not authorized to use this bot.\n"
            "Please use /auth [password] to get access.",
            reply_markup=ReplyKeyboardRemove()
        )


@router.message(Command("auth"))
@rate_limit(max_attempts=5, window=timedelta(minutes=15))
async def cmd_auth(message: Message):
    user_id = message.from_user.id
    print(f"\nAuth attempt by user {user_id}")

    current_auth = await rq.is_user_authorized(user_id)
    print(f"Current authorization status: {current_auth}")

    if current_auth:
        await message.answer("You are already authorized!")
        return True

    try:
        password = message.text.split()[1]
        print("Password provided by user")
    except IndexError:
        await message.answer("Please provide a password: /auth [password]")
        return False

    if await check_password(password):
        print("Password correct, attempting to authorize...")
        success = await rq.authorize_user(user_id)
        if success:
            print("Authorization successful")
            await message.answer(
                "✅ You have been authorized!\n"
                "Use the buttons below to manage loans:",
                reply_markup=main()
            )
            return True
        else:
            print("Authorization failed")
            await message.answer("There was an error authorizing you. Please try again.")
            return False
    else:
        print("Invalid password provided")
        await message.answer("❌ Invalid password. Please try again.")
        return False


@router.message(F.text == "❌ Cancel")
@auth_required
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Operation cancelled.", reply_markup=main())


# New Loan Flow
@router.message(F.text == "New Loan")
@auth_required
async def start_new_loan(message: Message, state: FSMContext):
    await state.set_state(LoanStates.getting_name)
    await message.answer(
        "Please enter the person's name:",
        reply_markup=cancel_kb()  # Use cancel_kb() directly
    )


# Handle name input
@router.message(LoanStates.getting_name)
@auth_required
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(LoanStates.getting_amount)
    await message.answer(
        "Please enter the loan amount:",
        reply_markup=cancel_kb()
    )


# Handle amount input
@router.message(LoanStates.getting_amount)
@auth_required
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("Please enter a valid positive number.")
            return
    except ValueError:
        await message.answer("Please enter a valid number.")
        return

    await state.update_data(amount=amount)
    await state.set_state(LoanStates.getting_frequency)
    await message.answer(
        "Choose payment frequency:",
        reply_markup=frequency_kb()
    )


@router.callback_query(lambda c: c.data.startswith('freq_'))
@auth_required
async def process_frequency(callback: CallbackQuery, state: FSMContext):
    frequency = callback.data.split('_')[1]

    await state.update_data(frequency=frequency)

    await callback.message.delete()

    await state.set_state(LoanStates.getting_payments)
    await callback.message.answer(
        f"You selected {frequency} payments.\nPlease enter the number of payments:",
        reply_markup=cancel_kb()
    )

    await callback.answer()


# Add handler for number of payments
@router.message(LoanStates.getting_payments)
@auth_required
async def process_payments(message: Message, state: FSMContext):
    try:
        num_payments = int(message.text)
        if num_payments <= 0:
            await message.answer("Please enter a valid positive number.")
            return
    except ValueError:
        await message.answer("Please enter a valid number.")
        return

    data = await state.get_data()

    total_amount = data['amount']
    payment_amount = round(total_amount / num_payments, 2)

    await state.update_data(number_of_payments=num_payments, payment_amount=payment_amount)

    summary = (
        f"Loan Summary:\n"
        f"Name: {data['name']}\n"
        f"Total Amount: ${total_amount:,.2f}\n"
        f"Frequency: {data['frequency']}\n"
        f"Number of Payments: {num_payments}\n"
        f"Payment Amount: ${payment_amount:,.2f}\n\n"
        f"Would you like to confirm this loan?"
    )

    await state.set_state(LoanStates.confirming_loan)
    await message.answer(text=summary, reply_markup=confirm_keyboard())


@router.callback_query(lambda c: c.data in ["confirm_loan", "cancel_loan"])
@auth_required
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "confirm_loan":
        data = await state.get_data()

        try:
            person_result = await rq.create_person(data['name'])

            loan_result = await rq.create_loan(
                person_id=person_result['id'],
                total_amount=data['amount'],
                payment_frequency=data['frequency'],
                number_of_payments=data['number_of_payments'],
                payment_amount=data['payment_amount']
            )

            await callback.message.edit_text(
                "✅ Loan has been successfully created!\n\n"
                f"Loan ID: {loan_result['id']}\n"
                f"Person ID: {person_result['id']}",
                reply_markup=None
            )

            # Show main menu
            await callback.message.answer(
                "What would you like to do next?",
                reply_markup=main()
            )

        except Exception as e:
            error_message = f"Error creating loan: {str(e)}"
            print(error_message)
            await callback.message.answer(
                "❌ There was an error creating the loan. Please try again.",
                reply_markup=main()
            )

    else:
        await callback.message.edit_text(
            "Loan creation cancelled.",
            reply_markup=None
        )
        await callback.message.answer(
            "What would you like to do next?",
            reply_markup=main()
        )

    await state.clear()
    await callback.answer()


@router.message(F.text == "Search Loans")
@auth_required
async def search_loans(message: Message):
    await message.answer(
        "Select how you would like to search loans:",
        reply_markup=search_filters_keyboard()
    )


@router.message(F.text == "View All Loans")
@auth_required
async def view_all_loans(message: Message):
    loans = await rq.get_all_loans()

    if not loans:
        await message.answer(
            "No active loans found.",
            reply_markup=main()
        )
        return

    total_loans = len(loans)
    await message.answer(
        f"📊 Total Active Loans: {total_loans}\n\nSelect a loan to manage:",
        reply_markup=loans_list_keyboard(loans, current_page=0)
    )


@router.callback_query(lambda c: c.data.startswith(('decrease_', 'increase_')))
@auth_required
async def adjust_payments(callback: CallbackQuery):
    action, loan_id = callback.data.split('_')
    loan_id = int(loan_id)

    loan = await rq.get_loan_details(loan_id)

    if not loan:
        await callback.answer("Loan not found!")
        return

    current_payments = loan['payments_left']
    new_payments = current_payments + 1 if action == 'increase' else max(0, current_payments - 1)

    success = await rq.update_loan_payment_details(loan_id, new_payments)

    if success:
        updated_loan = await rq.get_loan_details(loan_id)
        if updated_loan:
            details = (
                f"💰 Loan Details for {updated_loan['person_name']}\n\n"
                f"📅 Created: {updated_loan['created_at']}\n"
                f"💵 Total Amount: ${updated_loan['total_amount']:,.2f}\n"
                f"🏷️ Remaining: ${updated_loan['remaining_amount']:,.2f}\n"
                f"💸 Payment Amount: ${updated_loan['payment_amount']:,.2f}\n"
                f"🔄 Frequency: {updated_loan['frequency'].title()}\n"
                f"📊 Payments Left: {updated_loan['payments_left']}\n"
                f"📌 Status: {updated_loan['status'].title()}"
            )

            await callback.message.edit_text(
                details,
                reply_markup=loan_details_keyboard(loan_id)
            )

            action_text = "Added a payment" if action == 'increase' else "Removed a payment"
            await callback.answer(f"{action_text}")
    else:
        await callback.answer("Failed to update payments")


@router.callback_query(lambda c: c.data == "back_to_loans")
@auth_required
async def back_to_loans_list(callback: CallbackQuery):
    loans = await rq.get_all_loans()
    if not loans:
        await callback.message.edit_text(
            "No active loans found.",
            reply_markup=main()
        )
        return

    await callback.message.edit_text(
        "Select a loan to manage:",
        reply_markup=loans_list_keyboard(loans)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith('view_loan_'))
@auth_required
async def view_loan_details(callback: CallbackQuery):
    loan_id = int(callback.data.split('_')[2])
    loan = await rq.get_loan_details(loan_id)

    if not loan:
        await callback.answer("Loan not found!")
        await callback.message.edit_text(
            "Loan not found. Please try again.",
            reply_markup=main()
        )
        return

    details = (
        f"💰 Loan Details for {loan['person_name']}\n\n"
        f"📅 Created: {loan['created_at']}\n"
        f"💵 Total Amount: ${loan['total_amount']:,.2f}\n"
        f"🏷️ Remaining: ${loan['remaining_amount']:,.2f}\n"
        f"💸 Payment Amount: ${loan['payment_amount']:,.2f}\n"
        f"🔄 Frequency: {loan['frequency'].title()}\n"
        f"📊 Payments Left: {loan['payments_left']}\n"
        f"📌 Status: {loan['status'].title()}"
    )

    await callback.message.edit_text(
        details,
        reply_markup=loan_details_keyboard(loan_id)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith('page_'))
@auth_required
async def handle_pagination(callback: CallbackQuery):
    if callback.data == "page_info":
        await callback.answer()
        return

    page = int(callback.data.split('_')[1])
    loans = await rq.get_all_loans()

    if not loans:
        await callback.message.edit_text(
            "No active loans found.",
            reply_markup=main()
        )
        return

    total_loans = len(loans)
    await callback.message.edit_text(
        f"📊 Total Active Loans: {total_loans}\n\nSelect a loan to manage:",
        reply_markup=loans_list_keyboard(loans, current_page=page)
    )
    await callback.answer()


@router.message(Command("search"))
@auth_required
async def cmd_search(message: Message):
    """Handler for /search command"""
    await message.answer(
        "Select how you would like to search loans:",
        reply_markup=search_filters_keyboard()
    )


@router.callback_query(lambda c: c.data == "search_name")
@auth_required
async def search_by_name(callback: CallbackQuery, state: FSMContext):
    """Handle name search initiation"""
    await state.set_state(SearchStates.awaiting_name)
    await callback.message.edit_text(
        "Please enter the name to search for:",
        reply_markup=inline_cancel_kb()  # Use inline keyboard instead of reply keyboard
    )
    await callback.message.answer(
        "Type the name or press Cancel:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(SearchStates.awaiting_name)
@auth_required
async def process_name_search(message: Message, state: FSMContext):
    """Process the name search"""
    search_name = message.text.strip()

    if search_name == "❌ Cancel":
        await state.clear()
        await message.answer(
            "Search cancelled.",
            reply_markup=main()
        )
        return

    loans = await rq.search_loans_by_name(search_name)

    if not loans:
        await message.answer(
            f"No loans found with name '{search_name}'.\n\n"
            "Please try another name or press Cancel:",
            reply_markup=cancel_kb()
        )
        return

    else:
        total_loans = len(loans)
        await message.answer(
            f"Found {total_loans} loan(s) matching '{search_name}':",
            reply_markup=main()  # First show main keyboard
        )
        await message.answer(
            "Select a loan to view details:",
            reply_markup=loans_list_keyboard(loans)
        )

    await state.clear()


@router.callback_query(lambda c: c.data == "cancel_search")
@auth_required
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    """Handle search cancellation"""
    await state.clear()
    await callback.message.edit_text(
        "Search cancelled.",
        reply_markup=None
    )
    await callback.message.answer(
        "What would you like to do?",
        reply_markup=main()
    )
    await callback.answer()


@router.message(Command("ban"))
@auth_required
async def ban_user(message: Message):
    if not await rq.is_admin(message.from_user.id):
        await message.answer("❌ Only authorized users can use this command.")
        return

    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer("Usage: /ban user_id [reason]")
            return

        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else "Banned by admin"

        if await rq.is_admin(user_id):
            await message.answer("❌ Cannot ban authorized users.")
            return

        success = await rq.add_banned_user(user_id, reason)
        if success:
            await message.answer(f"User {user_id} has been banned.")
        else:
            await message.answer(f"User {user_id} is already banned.")

    except ValueError:
        await message.answer("Invalid user ID format.")
    except Exception as e:
        await message.answer(f"Error banning user: {str(e)}")


@router.message(Command("unban"))
@auth_required
async def unban_user(message: Message):
    if not await rq.is_admin(message.from_user.id):
        await message.answer("❌ Only authorized users can use this command.")
        return

    try:
        user_id = int(message.text.split()[1])
        success = await rq.unban_user(user_id)

        if success:
            await message.answer(f"User {user_id} has been unbanned.")
        else:
            await message.answer(f"User {user_id} is not banned.")

    except (ValueError, IndexError):
        await message.answer("Usage: /unban user_id")
    except Exception as e:
        await message.answer(f"Error unbanning user: {str(e)}")


@router.message(Command("listbanned"))
@auth_required
async def list_banned(message: Message):
    if not await rq.is_admin(message.from_user.id):
        await message.answer("❌ Only authorized users can use this command.")
        return

    banned_users = await rq.get_all_banned_users()

    if not banned_users:
        await message.answer("No banned users.")
        return

    text = "Banned Users:\n\n"
    for user in banned_users:
        banned_date = user.banned_at.strftime("%Y-%m-%d %H:%M")
        text += f"ID: {user.tg_id}\n"
        text += f"Banned at: {banned_date}\n"
        text += f"Reason: {user.reason}\n\n"

    await message.answer(text)
