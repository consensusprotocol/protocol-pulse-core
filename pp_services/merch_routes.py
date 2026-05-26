"""
Protocol Pulse — Merch Routes
Extract these routes into your Flask app.

Required imports at the top of your app:
    import os, json, logging
    from flask import Flask, render_template, request, jsonify, redirect, flash
    from pp_services.printful_service import PrintfulService

Required initialization:
    printful_service = PrintfulService()
"""

import os
import json
import logging
from flask import render_template, request, jsonify, flash


# --- MERCH STORE PAGE ---

@app.route('/merch')
def merch_store():
    """Merch store page - fetches products from Printful API"""
    try:
        products = printful_service.get_store_products()
        formatted_products = []

        for product in products:
            formatted_product = printful_service.format_product_for_display(product)
            if not formatted_product.get('is_ignored', True):
                formatted_products.append(formatted_product)

        rtsa_hot = []
        rtsa_approved = []
        rtsa_foundational = []
        try:
            from pp_services.rtsa_service import rtsa_service
            rtsa_hot = rtsa_service.get_hot_products()
            rtsa_approved = rtsa_service.get_approved_products(limit=6)
            rtsa_foundational = rtsa_service.get_foundational_statements()
        except Exception as rtsa_error:
            logging.warning(f"RTSA products unavailable: {rtsa_error}")

        return render_template('merch.html',
                             products=formatted_products,
                             rtsa_hot=rtsa_hot,
                             rtsa_approved=rtsa_approved,
                             rtsa_foundational=rtsa_foundational)
    except Exception as e:
        logging.error(f"Error loading merch store: {e}")
        flash('Error loading merchandise. Please try again later.')
        return render_template('merch.html', products=[], rtsa_hot=[], rtsa_approved=[], rtsa_foundational=[])


# --- PRODUCT DETAILS API ---

@app.route('/api/merch/product/<int:product_id>')
def get_product_details(product_id):
    """Get detailed product information"""
    try:
        product = printful_service.get_product_details(product_id)
        if product:
            formatted_product = printful_service.format_product_for_display(product)
            return jsonify(formatted_product)
        else:
            return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        logging.error(f"Error getting product details: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# --- STRIPE CHECKOUT ---

@app.route('/api/merch/checkout', methods=['POST'])
def merch_checkout():
    """Create Stripe checkout session for merch purchase, fulfills via Printful"""
    try:
        import stripe

        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({'error': 'No items provided'}), 400

        items = data.get('items', [])
        customer_email = data.get('email', '')

        if not items:
            return jsonify({'error': 'Cart is empty'}), 400

        stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe_key:
            return jsonify({'error': 'Payment system not configured'}), 500

        stripe.api_key = stripe_key

        line_items = []
        printful_items = []

        for item in items:
            variant_id = item.get('variant_id')
            quantity = item.get('quantity', 1)
            name = item.get('name', 'Product')
            price = float(item.get('price', 0))
            size = item.get('size', '')

            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{name} - {size}" if size else name,
                        'description': f'Protocol Pulse Merchandise'
                    },
                    'unit_amount': int(price * 100)
                },
                'quantity': quantity
            })

            printful_items.append({
                'sync_variant_id': variant_id,
                'quantity': quantity
            })

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=customer_email if customer_email else None,
            success_url=request.url_root + 'merch/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.url_root + 'merch',
            shipping_address_collection={
                'allowed_countries': ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'NL', 'ES', 'IT', 'JP']
            },
            metadata={
                'type': 'merch_order',
                'printful_items': json.dumps(printful_items)
            }
        )

        return jsonify({
            'success': True,
            'checkout_url': session.url,
            'session_id': session.id
        })

    except Exception as e:
        logging.error(f"Merch checkout error: {e}")
        return jsonify({'error': str(e)}), 500


# --- SUCCESS PAGE ---

@app.route('/merch/success')
def merch_success():
    """Merch purchase success page"""
    session_id = request.args.get('session_id', '')
    return render_template('merch_success.html', session_id=session_id)


# --- PRINTFUL WEBHOOK ---

@app.route('/webhook/printful', methods=['POST'])
def printful_webhook():
    """Handle Printful webhook for order status updates"""
    try:
        data = request.get_json()
        event_type = data.get('type')
        order_data = data.get('data', {}).get('order', {})

        logging.info(f"Printful webhook: {event_type} - Order {order_data.get('id')}")

        return jsonify({'received': True}), 200
    except Exception as e:
        logging.error(f"Printful webhook error: {e}")
        return jsonify({'error': str(e)}), 500


# --- STRIPE WEBHOOK (merch order fulfillment portion) ---
# Add this inside your existing Stripe webhook handler:

def handle_merch_stripe_webhook(session):
    """
    Call this when a checkout.session.completed event has metadata.type == 'merch_order'
    It creates a draft order in Printful for fulfillment.
    """
    metadata = session.get('metadata', {})
    try:
        printful_items_json = metadata.get('printful_items', '[]')
        printful_items = json.loads(printful_items_json)
        shipping = session.get('shipping_details', {})
        address = shipping.get('address', {})

        order_data = {
            'recipient': {
                'name': shipping.get('name', ''),
                'address1': address.get('line1', ''),
                'address2': address.get('line2', ''),
                'city': address.get('city', ''),
                'state_code': address.get('state', ''),
                'country_code': address.get('country', 'US'),
                'zip': address.get('postal_code', ''),
                'email': session.get('customer_details', {}).get('email', '')
            },
            'items': printful_items
        }

        result = printful_service.create_order(order_data, confirm=False)
        if result:
            logging.info(f"Printful order created: {result.get('id')}")
        else:
            logging.error("Failed to create Printful order")

    except Exception as e:
        logging.error(f"Error processing merch order: {e}")
