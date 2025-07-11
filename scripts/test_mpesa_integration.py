#!/usr/bin/env python
"""
Complete M-Pesa Integration Test Script
This script tests the entire M-Pesa payment flow with your phone number
"""

import os
import sys
import django
import time

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wafungi_nation.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from wafungi.models import Booking, PaymentTransaction, InstrumentListing, Instrument
from wafungi.mpesa_utils import MPesaAPI, process_mpesa_payment
from decimal import Decimal
import json

User = get_user_model()

def create_test_booking():
    """Create a test booking for payment testing"""
    print("🏗️  Creating test booking...")
    
    # Create or get test users
    client_user, created = User.objects.get_or_create(
        username='testclient',
        defaults={
            'email': 'client@test.com',
            'user_type': 'client',
            'phone': '254793706728',
            'first_name': 'Test',
            'last_name': 'Client'
        }
    )
    
    owner_user, created = User.objects.get_or_create(
        username='testowner',
        defaults={
            'email': 'owner@test.com',
            'user_type': 'instrument_owner',
            'phone': '254700000000',
            'first_name': 'Test',
            'last_name': 'Owner'
        }
    )
    
    # Create test instrument
    instrument, created = Instrument.objects.get_or_create(
        name='Test Guitar',
        defaults={'category': 'String'}
    )
    
    instrument_listing, created = InstrumentListing.objects.get_or_create(
        owner=owner_user,
        instrument=instrument,
        brand='Test Brand',
        model='Test Model',
        defaults={
            'condition': 'excellent',
            'daily_rate': Decimal('1.00'),  # 1 KSH for testing
            'description': 'Test instrument for payment testing',
            'location': 'Nairobi',
            'is_available': True
        }
    )
    
    # Create test booking
    booking, created = Booking.objects.get_or_create(
        client=client_user,
        instrument_listing=instrument_listing,
        defaults={
            'start_date': '2024-01-15 10:00:00',
            'end_date': '2024-01-16 10:00:00',
            'total_amount': Decimal('1.00'),  # 1 KSH for testing
            'status': 'confirmed',
            'notes': 'Test booking for M-Pesa payment testing'
        }
    )
    
    print(f"✅ Test booking created: ID {booking.id}")
    return booking

def test_complete_payment_flow():
    """Test the complete payment flow"""
    print("🚀 Starting Complete M-Pesa Payment Test")
    print("=" * 50)
    
    # Step 1: Create test booking
    booking = create_test_booking()
    
    # Step 2: Test M-Pesa configuration
    print("\n📋 Testing M-Pesa Configuration...")
    mpesa = MPesaAPI()
    
    # Test access token
    token = mpesa.get_access_token()
    if not token:
        print("❌ Failed to get access token. Check configuration.")
        return False
    
    print("✅ Access token obtained successfully")
    
    # Step 3: Test phone number formatting
    test_phone = "0793706728"
    formatted_phone = mpesa.format_phone_number(test_phone)
    print(f"📱 Phone formatting: {test_phone} → {formatted_phone}")
    
    # Step 4: Confirm payment test
    print(f"\n💳 Ready to test payment:")
    print(f"   📱 Phone: {formatted_phone}")
    print(f"   💰 Amount: KSH {booking.total_amount}")
    print(f"   🆔 Booking ID: {booking.id}")
    
    confirm = input("\n⚠️  This will send a real M-Pesa STK Push. Continue? (yes/no): ")
    
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Test cancelled by user")
        return False
    
    # Step 5: Process payment
    print("\n🚀 Processing M-Pesa payment...")
    
    try:
        result = process_mpesa_payment(
            phone_number=test_phone,
            amount=float(booking.total_amount),
            booking_id=booking.id
        )
        
        print(f"📋 Payment Result:")
        print(json.dumps(result, indent=2))
        
        if result['success']:
            print("\n✅ STK Push sent successfully!")
            
            # Create payment transaction record
            transaction = PaymentTransaction.objects.create(
                booking=booking,
                checkout_request_id=result['checkout_request_id'],
                merchant_request_id=result.get('merchant_request_id', ''),
                phone_number=formatted_phone,
                amount=booking.total_amount,
                status='pending',
                mpesa_response=result
            )
            
            print(f"💾 Transaction record created: ID {transaction.id}")
            print("\n📱 Check your phone for the M-Pesa prompt...")
            print("💡 You should receive an STK Push notification")
            
            # Wait for user to complete payment
            input("\nPress Enter after completing or cancelling the payment...")
            
            # Step 6: Check payment status
            print("\n🔍 Checking payment status...")
            
            for attempt in range(3):
                print(f"   Attempt {attempt + 1}/3...")
                
                status_result = mpesa.query_stk_status(result['checkout_request_id'])
                print(f"   Status: {status_result}")
                
                if status_result['success']:
                    result_code = status_result.get('result_code')
                    result_desc = status_result.get('result_desc')
                    
                    if result_code == 0:
                        print("✅ Payment completed successfully!")
                        
                        # Update transaction
                        transaction.status = 'completed'
                        transaction.save()
                        
                        # Update booking
                        booking.payment_status = True
                        booking.save()
                        
                        print(f"💾 Booking {booking.id} marked as paid")
                        return True
                        
                    elif result_code == 1032:
                        print("⚠️  Payment was cancelled by user")
                        transaction.status = 'cancelled'
                        transaction.save()
                        return False
                        
                    elif result_code == 1037:
                        print("⏳ Payment is still pending...")
                        time.sleep(5)
                        continue
                        
                    else:
                        print(f"❌ Payment failed: {result_desc}")
                        transaction.status = 'failed'
                        transaction.save()
                        return False
                else:
                    print("❌ Failed to query payment status")
                    time.sleep(5)
            
            print("⏰ Payment status check timed out")
            return False
            
        else:
            print(f"❌ STK Push failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Payment test failed: {str(e)}")
        return False

def test_callback_simulation():
    """Simulate M-Pesa callback for testing"""
    print("\n🔄 Testing Callback Simulation...")
    
    # Sample successful callback data
    callback_data = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "test_merchant_123",
                "CheckoutRequestID": "ws_CO_test_123456789",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 1.0},
                        {"Name": "MpesaReceiptNumber", "Value": "TEST123456"},
                        {"Name": "TransactionDate", "Value": 20240115143000},
                        {"Name": "PhoneNumber", "Value": 254793706728}
                    ]
                }
            }
        }
    }
    
    from wafungi.mpesa_utils import handle_mpesa_callback
    
    result = handle_mpesa_callback(callback_data)
    print(f"📋 Callback Result:")
    print(json.dumps(result, indent=2))
    
    if result['success']:
        print("✅ Callback handling successful")
    else:
        print("❌ Callback handling failed")

if __name__ == "__main__":
    print("🧪 M-Pesa Integration Test Suite")
    print("Phone Number: 0793706728")
    print("Test Amount: 1 KSH")
    print("=" * 50)
    
    # Run complete payment flow test
    success = test_complete_payment_flow()
    
    if success:
        print("\n🎉 Payment test completed successfully!")
    else:
        print("\n❌ Payment test failed or was cancelled")
    
    # Test callback simulation
    test_callback_simulation()
    
    print("\n🏁 Test suite completed")
