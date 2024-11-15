from app.database.models import Person, Loan, async_session, User, BannedUser
from sqlalchemy import select


async def create_person(name: str, phone: str = None):
    async with async_session() as session:
        async with session.begin():
            existing_person = await session.scalar(
                select(Person).where(Person.name.ilike(name))
            )

            if existing_person:
                return {'id': existing_person.id}

            new_person = Person(name=name, phone=phone)
            session.add(new_person)
            await session.flush()
            return {'id': new_person.id}


async def create_loan(person_id: int, total_amount: float, payment_frequency: str,
                      number_of_payments: int, payment_amount: float):
    async with async_session() as session:
        async with session.begin():
            person = await session.scalar(
                select(Person).where(Person.id == person_id)
            )

            if not person:
                raise ValueError("Person not found")

            new_loan = Loan(
                person_id=person_id,
                total_amount=total_amount,
                remaining_amount=total_amount,
                payment_frequency=payment_frequency,
                number_of_payments=number_of_payments,
                payment_amount=payment_amount,
                status='active'
            )
            session.add(new_loan)
            await session.flush()
            return {'id': new_loan.id}


async def get_all_loans():
    async with async_session() as session:
        query = select(Loan, Person).join(Person, Loan.person_id == Person.id) \
            .where(Loan.status == 'active') \
            .order_by(Loan.created_at.desc())

        result = await session.execute(query)
        loans = []
        rows = result.all()
        for loan, person in rows:
            loans.append({
                'id': loan.id,
                'person_name': person.name,
                'total_amount': loan.total_amount,
                'remaining_amount': loan.remaining_amount,
                'payment_amount': loan.payment_amount,
                'frequency': loan.payment_frequency,
                'payments_left': loan.number_of_payments,
                'status': loan.status
            })
        return loans


async def get_loan_details(loan_id: int):
    async with async_session() as session:
        query = select(Loan, Person).join(Person, Loan.person_id == Person.id) \
            .where(Loan.id == loan_id)

        result = await session.execute(query)
        row = result.first()

        if row:
            loan, person = row
            return {
                'id': loan.id,
                'person_name': person.name,
                'total_amount': loan.total_amount,
                'remaining_amount': loan.remaining_amount,
                'payment_amount': loan.payment_amount,
                'frequency': loan.payment_frequency,
                'payments_left': loan.number_of_payments,
                'status': loan.status,
                'created_at': loan.created_at.strftime("%Y-%m-%d")
            }
        return None


async def update_loan_payment_details(loan_id: int, new_payments_count: int):
    async with async_session() as session:
        async with session.begin():
            # Get the loan
            loan = await session.get(Loan, loan_id)
            if loan and new_payments_count >= 0:

                new_remaining_amount = loan.payment_amount * new_payments_count
                loan.number_of_payments = new_payments_count
                loan.remaining_amount = new_remaining_amount

                if new_payments_count == 0:
                    loan.status = 'completed'
                    loan.remaining_amount = 0  # Ensure remaining amount is 0 when completed

                await session.commit()
                return True
            return False


async def is_user_authorized(tg_id: int) -> bool:
    async with async_session() as session:
        try:
            query = select(User).where(User.tg_id == tg_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if user is None:
                print(f"User {tg_id} not found in database")
                return False

            print(f"User {tg_id} found, authorized status: {user.is_authorized}")
            return user.is_authorized

        except Exception as e:
            print(f"Error checking authorization: {e}")
            return False


async def authorize_user(tg_id: int) -> bool:
    async with async_session() as session:
        try:
            async with session.begin():
                query = select(User).where(User.tg_id == tg_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    print(f"Updating existing user {tg_id}")
                    user.is_authorized = True
                else:
                    print(f"Creating new user {tg_id}")
                    new_user = User(tg_id=tg_id, is_authorized=True)
                    session.add(new_user)


            verify_query = select(User).where(User.tg_id == tg_id)
            verify_result = await session.execute(verify_query)
            verified_user = verify_result.scalar_one_or_none()

            if verified_user and verified_user.is_authorized:
                print(f"Successfully verified user {tg_id} is authorized")
                return True

            return False

        except Exception as e:
            print(f"Error in authorize_user: {e}")
            return False


async def search_loans_by_name(name: str):
    """Search loans by borrower name"""
    async with async_session() as session:
        query = select(Loan, Person).join(Person, Loan.person_id == Person.id) \
            .where(Person.name.ilike(f"%{name}%")) \
            .order_by(Loan.created_at.desc())

        result = await session.execute(query)
        loans = []

        for loan, person in result:
            loans.append({
                'id': loan.id,
                'person_name': person.name,
                'total_amount': loan.total_amount,
                'remaining_amount': loan.remaining_amount,
                'payment_amount': loan.payment_amount,
                'frequency': loan.payment_frequency,
                'payments_left': loan.number_of_payments,
                'status': loan.status
            })

        return loans


async def get_banned_users(tg_id: int):
    async with async_session() as session:
        query = select(BannedUser).where(BannedUser.tg_id == tg_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user


async def add_banned_user(tg_id: int, reason: str = "Rate limit exceeded too many times"):
    async with async_session() as session:
        async with session.begin():
            existing_user = await get_banned_users(tg_id)

            if existing_user:
                return False

            banned_user = BannedUser(tg_id=tg_id, reason=reason)
            session.add(banned_user)
            return True


async def get_authorized_users():
    async with async_session() as session:
        query = select(User).where(User.is_authorized == True)
        result = await session.execute(query)
        return result.scalars().all()


async def is_admin(tg_id: int) -> bool:
    async with async_session() as session:
        query = select(User).where(User.tg_id == tg_id, User.is_authorized == True)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None


async def unban_user(tg_id: int) -> bool:
    async with async_session() as session:
        async with session.begin():
            banned_user = await get_banned_users(tg_id)
            if banned_user:
                await session.delete(banned_user)
                return True
            return False

async def get_all_banned_users():
    async with async_session() as session:
        query = select(BannedUser).order_by(BannedUser.banned_at.desc())
        result = await session.execute(query)
        return result.scalars().all()