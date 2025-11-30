# app/services/settlement_service.py

from decimal import Decimal, ROUND_HALF_UP
from app import db
from app.models import Product, ShoppingList, Settlement, User  # Ensure User and Friend are imported


def check_and_update_list_settlement_status(shopping_list_id):
    """
    Check whether all settlements for a given shopping list are settled.
    If so, set `is_fully_settled` to True for the ShoppingList.
    """
    shopping_list = ShoppingList.query.get(shopping_list_id)
    if not shopping_list:
        print(
            f"DEBUG: _check_and_update_list_settlement_status: Error: Shopping list with ID {shopping_list_id} does not exist.")
        return

    all_list_settlements = Settlement.query.filter_by(shopping_list_id=shopping_list_id).all()
    all_settled = all(s.is_settled for s in all_list_settlements) if all_list_settlements else True

    if all_settled and not shopping_list.is_fully_settled:
        shopping_list.is_fully_settled = True
        print(
            f"DEBUG: _check_and_update_list_settlement_status: List '{shopping_list.name}' (ID: {shopping_list_id}) has been fully settled.")
    elif not all_settled and shopping_list.is_fully_settled:
        shopping_list.is_fully_settled = False
        print(
            f"DEBUG: _check_and_update_list_settlement_status: List '{shopping_list.name}' (ID: {shopping_list_id}) is NOT fully settled. Status changed.")

    db.session.commit()
    print(f"DEBUG: _check_and_update_list_settlement_status: Committed status changes for list {shopping_list_id}.")


def calculate_settlements(shopping_list_id):
    """
    Calculate and persist settlements for a given shopping list, minimizing the
    number of transactions. Settlements can be between Users and Friends.
    """
    shopping_list = ShoppingList.query.get(shopping_list_id)
    if not shopping_list:
        print(f"DEBUG: calculate_settlements: ERROR: Shopping list with ID {shopping_list_id} not found.")
        return []

    products = Product.query.filter_by(shopping_list_id=shopping_list_id).all()
    print(f"DEBUG: calculate_settlements: Products for list {shopping_list_id}: {[p.name for p in products]}")

    participants = shopping_list.participants.all()
    print(f"DEBUG: calculate_settlements: Participants for list {shopping_list_id}: {[p.username for p in participants]}")

    all_entities = set()
    for participant in participants:
        all_entities.add(('user', participant.id))

    for product in products:
        if product.paid_by:
            all_entities.add(('user', product.paid_by))
        for friend in product.assigned_friends_for_product:
            all_entities.add(('friend', friend.id))

    print(f"DEBUG: calculate_settlements: All involved entities: {all_entities}")

    if not products or not all_entities:
        print(
            f"DEBUG: calculate_settlements: No products or entities to settle for list {shopping_list_id}. No settlements generated.")
        shopping_list.is_fully_settled = True
        db.session.commit()
        return []

    balances = {entity: Decimal('0.00') for entity in all_entities}
    print(f"DEBUG: calculate_settlements: Initial balances: {balances}")

    # Sum payments (who paid for each product)
    for product in products:
        if product.paid_by:
            balances[('user', product.paid_by)] += product.price
            print(
                f"DEBUG: calculate_settlements: User {User.query.get(product.paid_by).username if User.query.get(product.paid_by) else product.paid_by} paid {product.price} for {product.name}. New balance: {balances[('user', product.paid_by)]}")
    print(f"DEBUG: calculate_settlements: Balances after summing payments: {balances}")

    # Settle product costs
    for product in products:
        item_price = product.price
        assigned_friends = product.assigned_friends_for_product

        if assigned_friends:
            share_per_friend = item_price / Decimal(len(assigned_friends))
            for friend in assigned_friends:
                if ('friend', friend.id) in balances:
                    balances[('friend', friend.id)] -= share_per_friend
                    print(
                        f"DEBUG: calculate_settlements: Friend {friend.name} assigned to {product.name}. Balance: {balances[('friend', friend.id)]}")
                else:
                    print(
                        f"DEBUG: calculate_settlements: WARNING: Friend {friend.name} (ID {friend.id}) not present in balances. Logic error.")
        else:
            if product.paid_by:
                if ('user', product.paid_by) in balances:
                    balances[('user', product.paid_by)] -= item_price
                    print(
                        f"DEBUG: calculate_settlements: User {User.query.get(product.paid_by).username if User.query.get(product.paid_by) else product.paid_by} bears cost {item_price} for {product.name}. Balance: {balances[('user', product.paid_by)]}")
                else:
                    print(
                        f"DEBUG: calculate_settlements: WARNING: Product {product.name} (ID {product.id}) is unassigned and was paid by user {product.paid_by}, who is not in balances. Cost will not be settled.")
            else:
                print(
                    f"DEBUG: calculate_settlements: WARNING: Product {product.name} (ID {product.id}) is unassigned and has no payer. Cost will not be settled.")

    print(f"DEBUG: calculate_settlements: Balances after settling costs: {balances}")

    balances = {entity: balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                for entity, balance in balances.items() if balance != Decimal('0.00')}
    print(f"DEBUG: calculate_settlements: Balances after rounding and filtering zeros: {balances}")

    debtors = {entity: abs(balance) for entity, balance in balances.items() if balance < 0}
    creditors = {entity: balance for entity, balance in balances.items() if balance > 0}

    debtors_list = sorted([{'entity': entity, 'amount': amount} for entity, amount in debtors.items()],
                          key=lambda x: x['amount'], reverse=True)
    creditors_list = sorted([{'entity': entity, 'amount': amount} for entity, amount in creditors.items()],
                            key=lambda x: x['amount'], reverse=True)

    print(f"DEBUG: calculate_settlements: Debtors list: {debtors_list}")
    print(f"DEBUG: calculate_settlements: Creditors list: {creditors_list}")

    generated_settlements = []

    while debtors_list and creditors_list:
        debtor_item = debtors_list[0]
        creditor_item = creditors_list[0]

        amount_to_settle = min(debtor_item['amount'], creditor_item['amount'])

        new_settlement = Settlement(
            shopping_list_id=shopping_list_id,
            amount=amount_to_settle,
            is_settled=False
        )

        if debtor_item['entity'][0] == 'user':
            new_settlement.debtor_user_id = debtor_item['entity'][1]
        else:  # 'friend'
            new_settlement.debtor_friend_id = debtor_item['entity'][1]

        if creditor_item['entity'][0] == 'user':
            new_settlement.creditor_user_id = creditor_item['entity'][1]
        else:  # 'friend'
            new_settlement.creditor_friend_id = creditor_item['entity'][1]

        generated_settlements.append(new_settlement)
        db.session.add(new_settlement)

        print(f"DEBUG: calculate_settlements: Added settlement: {new_settlement}")

        debtor_item['amount'] -= amount_to_settle
        creditor_item['amount'] -= amount_to_settle

        if debtor_item['amount'] == Decimal('0.00'):
            debtors_list.pop(0)
        if creditor_item['amount'] == Decimal('0.00'):
            creditors_list.pop(0)

    try:
        db.session.commit()
        print(
            f"DEBUG: calculate_settlements: Generated {len(generated_settlements)} settlements for list {shopping_list_id}.")
        check_and_update_list_settlement_status(shopping_list_id)
        return generated_settlements
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: calculate_settlements: Error while saving settlements for list {shopping_list_id}: {e}")
        return []
