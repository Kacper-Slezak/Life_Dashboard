import re
from decimal import Decimal, InvalidOperation  # Added InvalidOperation


def normalize_text(text):
    """Normalizes text for comparisons (lowercase, remove special characters)."""
    if not isinstance(text, str):
        return ""
    # Remove dots, commas, percent signs, parentheses etc., but keep spaces to avoid joining words
    text = re.sub(r'[^a-z0-9\s]', '', text.lower())
    return ' '.join(text.split())


def generate_trigrams(text):
    """Generate trigrams (3-character sequences) from the given text."""
    text = normalize_text(text).replace(" ", "")  # Remove spaces for trigrams
    if len(text) < 3:
        return {text}  # Return the whole text as a "trigram" if it's too short
    return {text[i:i + 3] for i in range(len(text) - 2)}


def fuzzy_matching(item_name_list, ocr_candidate_name):
    """
    Check match between a product name from the list and a candidate OCR name
    using trigrams and substring checks. Returns a similarity score.
    """
    if not item_name_list or not ocr_candidate_name:
        return 0.0
    normalized_item_name = normalize_text(item_name_list)
    normalized_ocr_name = normalize_text(ocr_candidate_name)

    # 1. Exact substring match (priority)
    if normalized_item_name in normalized_ocr_name or normalized_ocr_name in normalized_item_name:
        return 1.0  # Perfect match

    # 2. Trigram matching (for partial/shortened names)
    item_trigrams = generate_trigrams(normalized_item_name)
    ocr_trigrams = generate_trigrams(normalized_ocr_name)

    if not item_trigrams or not ocr_trigrams:
        return 0.0

    # Compute Jaccard similarity on trigrams
    intersection = len(item_trigrams.intersection(ocr_trigrams))
    union = len(item_trigrams.union(ocr_trigrams))

    jaccard_similarity = intersection / union if union > 0 else 0.0
    return jaccard_similarity


def match_ocr_to_shopping_list(shopping_list_items, parsed_ocr_items):
    """
    Merge parsed OCR results with existing shopping list items
    and add new items found only in OCR.

    Args:
        shopping_list_items (list): List of item dicts from the shopping list,
                                    e.g. [{'name': 'Bread', 'price': Decimal('0.00'), 'assigned_friends': [], 'paid_by': 1, 'db_id': 1}, ...].
                                    Prices are Decimal objects.
        parsed_ocr_items (list): List of item dicts obtained from OCR parsing,
                                 e.g. [{'name': 'Wheat bread', 'total_price': '3.49'}, ...].
                                 'total_price' is a string.

    Returns:
        list: Updated list of items including prices from OCR
              and new items found only in OCR. Items maintain a structure
              similar to `shopping_list_items`.
    """

    # Create a copy of the OCR list so we can mark matched items
    ocr_items_with_status = []
    for item in parsed_ocr_items:
        if 'name' in item and 'total_price' in item:
            try:
                # Convert total_price to Decimal here
                ocr_items_with_status.append({
                    'name': item['name'],
                    'price': Decimal(item['total_price']),
                    'matched': False
                })
            except InvalidOperation:
                print(
                    f"WARNING: Could not convert OCR price '{item['total_price']}' for '{item['name']}' to Decimal. Setting price to 0.00.")
                ocr_items_with_status.append({
                    'name': item['name'],
                    'price': Decimal('0.00'),  # Set price to 0.00 if conversion fails
                    'matched': False
                })

    final_shopping_list = []
    threshold = 0.45  # Trigram similarity threshold (adjustable)

    # 1. Match shopping list items to OCR items
    for s_item in shopping_list_items:
        s_item_name_normalized = normalize_text(s_item['name'])
        best_match_ocr_idx = -1
        highest_similarity = -1.0

        for i, ocr_item in enumerate(ocr_items_with_status):
            if ocr_item['matched']:  # Skip already matched OCR items
                continue

            similarity = fuzzy_matching(s_item_name_normalized, ocr_item['name'])

            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match_ocr_idx = i

        if best_match_ocr_idx != -1 and highest_similarity >= threshold:
            # Matched shopping list item to an OCR item
            matched_ocr_item = ocr_items_with_status[best_match_ocr_idx]

            # Update the shopping list item's price if OCR found a price
            # and it is non-zero (or if original price was 0.00 and OCR found non-zero)
            if matched_ocr_item['price'] is not None and \
                    (matched_ocr_item['price'] != Decimal('0.00') or s_item['price'] == Decimal('0.00')):
                s_item['price'] = matched_ocr_item['price']

            final_shopping_list.append(s_item)
            matched_ocr_item['matched'] = True  # Mark as matched to avoid reuse
        else:
            # No sufficiently good match found in OCR for the shopping list item
            final_shopping_list.append(s_item)  # Keep it with its original price (or 0.00)

    # 2. Add unmatched OCR items to the final list
    for ocr_item in ocr_items_with_status:
        if not ocr_item['matched']:
            # Add only if it has a name and a sensible price, or a sufficiently long name
            if ocr_item['name'] and (ocr_item['price'] is not None and ocr_item['price'] != Decimal('0.00')) or \
                    (ocr_item['name'] and len(ocr_item['name'].split()) > 1) or \
                    (ocr_item['name'] and len(ocr_item['name']) >= 4):  # Heurystyka dla sensownej nazwy
                # Create a new entry, preserving the structure used in shopping_list_items
                final_shopping_list.append({
                    'name': ocr_item['name'],
                    'price': ocr_item['price'],
                    'assigned_friends': [],  # Default empty friends list for new items
                    'paid_by': None,  # Will be set to current_user.id in the route
                    'db_id': None  # New item, no DB id
                })
            else:
                print(f"DEBUG: Skipping OCR item '{ocr_item.get('name', 'N/A')}' due to lack of sensible data.")

    return final_shopping_list
