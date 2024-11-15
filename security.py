import logging
import hashlib
import os
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from typing import Union
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardRemove
from app.database import requests as rq


class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(list)
        self.rate_limit_violations = defaultdict(int)

    def _clean_old_attemps(self, user_id: int, window: timedelta):
        """Remove attempts older than window"""
        current_time = datetime.now()
        self.attempts[user_id] = [
            attempt_time
            for attempt_time in self.attempts[user_id]
            if current_time - attempt_time < window
        ]

    def is_rate_limited(self, user_id: int, max_attempts: int, window: timedelta):
        """Check if user is rate limited"""
        self._clean_old_attemps(user_id, window)
        return len(self.attempts[user_id]) >= max_attempts

    def add_attempt(self, user_id: int):
        """Record new attempt"""
        self.attempts[user_id].append(datetime.now())

    async def check_and_ban_if_needed(self, user_id: int) -> bool:
        """Check if user should be banned based on repeated violations"""
        if await rq.is_admin(user_id):
            return False

        self.rate_limit_violations[user_id] += 1
        print(f"User {user_id} violations: {self.rate_limit_violations[user_id]}")

        if self.rate_limit_violations[user_id] >= 2:
            await rq.add_banned_user(
                user_id,
                f"Rate limit exceeded {self.rate_limit_violations[user_id]} times"
            )
            return True
        return False

    def reset_violations(self, user_id: int):
        """Reset violation count for user"""
        if user_id in self.rate_limit_violations:
            del self.rate_limit_violations[user_id]


rate_limiter = RateLimiter()


def rate_limit(max_attempts: int = 5, window: timedelta = timedelta(minutes=15)):
    def decorator(func):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id

            banned = await rq.get_banned_users(user_id)
            if banned:
                await message.answer(
                    "❌ You have been banned from using this bot due to multiple violations."
                )
                return

            rate_limiter.add_attempt(user_id)

            if rate_limiter.is_rate_limited(user_id, max_attempts, window): # If is_rate_limited is True
                should_ban = await rate_limiter.check_and_ban_if_needed(user_id)

                if should_ban:
                    await message.answer(
                        "❌ You have been banned from using this bot due to multiple rate limit violations."
                    )
                    logging.warning(f"User {user_id} has been banned due to multiple violations")
                    return

                time_left = window - (datetime.now() - rate_limiter.attempts[user_id][0])
                minutes_left = int(time_left.total_seconds() // 60)

                await message.answer(
                    f"⚠️ Too many attempts. Please try again in {minutes_left} minutes.\n"
                    f"Warning: Multiple violations will result in a ban.\n"
                    f"Violations: {rate_limiter.rate_limit_violations[user_id]}/2"
                )
                logging.warning(f"Rate limit exceeded for user {user_id}")
                return

            try:
                result = await func(message, *args, **kwargs)
                if result is not False:
                    rate_limiter.reset_violations(user_id)
                return result
            except Exception as e:
                logging.error(f"Error in rate-limited function: {e}")
                raise

        return wrapper

    return decorator


def auth_required(func):
    @wraps(func)
    async def wrapper(event: Union[Message, CallbackQuery], *args, **kwargs):
        if isinstance(event, Message):
            user_id = event.from_user.id
            message = event
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            message = event.message
        else:
            return await func(event, *args, **kwargs)

        if not await rq.is_user_authorized(user_id):
            await message.answer(
                "⚠️ You are not authorized to use this bot.\n"
                "Please use /auth [password] to get access.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        return await func(event, *args, **kwargs)

    return wrapper


async def check_password(user_input):
    hashed_input = hashlib.sha256(user_input.encode()).hexdigest()
    print(f"Hashed input: {hashed_input}")
    stored_hash = os.getenv("BOT_PASSWORD")
    return hashed_input == stored_hash
