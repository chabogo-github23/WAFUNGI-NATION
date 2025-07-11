#!/usr/bin/env python
"""
M-Pesa Debug Script
Run this script to debug M-Pesa integration issues
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wafungi_nation.settings')
django.setup()

from django.conf import settings
from wafungi.mpesa_utils import MPesaAPI
import requests
import base64
import json

def debug_mpesa_setup():
    """Debug M-Pesa configuration and connectivity"""
    print("🔍 M-Pesa Integration Debug Report")
    print("=" * 50)
    
    # 1. Check Configuration
    print("\n1. 📋 Configuration Check:")
    print("-" * 30)
    
    config_items = [
        ('MPESA_CONSUMER_KEY', getattr(settings, 'MPESA_CONSUMER_KEY', None)),
        ('MPESA_CONSUMER_SECRET', getattr(settings, 'MPESA_CONSUMER_SECRET', None)),
        ('MPESA_BUSINESS_SHORT_CODE', getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', None)),
        ('MPESA_PASSKEY', getattr(settings, 'MPESA_PASSKEY', None)),
        ('MPESA_CALLBACK_URL', getattr(settings, 'MPESA_CALLBACK_URL', None)),
        ('MPESA_AUTH_URL', getattr(settings, 'MPESA_AUTH_URL', None)),
        ('MPESA_STK_PUSH_URL', getattr(settings, 'MPESA_STK_PUSH_URL', None)),
    ]
    
    for key, value in config_items:
        if value:
            # Mask sensitive data
            if 'KEY' in key or 'SECRET' in key or 'PASSKEY' in key:
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {key}: {display_value}")
        else:
            print(f"❌ {key}: NOT SET")
    
    # 2. Test Network Connectivity
    print("\n2. 🌐 Network Connectivity Test:")
    print("-" * 35)
    
    test_urls = [
        'https://sandbox.safaricom.co.ke',
        'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials',
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"✅ {url}: Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {url}: {str(e)}")
    
    # 3. Test Access Token
    print("\n3. 🔑 Access Token Test:")
    print("-" * 25)
    
    try:
        mpesa = MPesaAPI()
        
        # Manual access token request for debugging
        consumer_key = mpesa.consumer_key
        consumer_secret = mpesa.consumer_secret
        
        if not consumer_key or not consumer_secret:
            print("❌ Consumer key or secret not set")
            return
        
        credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json'
        }
        
        print(f"📡 Requesting token from: {mpesa.auth_url}")
        print(f"🔐 Credentials (base64): {credentials[:20]}...")
        
        response = requests.get(mpesa.auth_url, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        print(f"📝 Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if 'access_token' in result:
                print(f"✅ Access Token: {result['access_token'][:20]}...")
                print(f"⏰ Expires In: {result.get('expires_in', 'N/A')} seconds")
            else:
                print("❌ No access token in response")
        else:
            print(f"❌ Failed to get access token: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Access token test failed: {str(e)}")
    
    # 4. Test Phone Number Formatting
    print("\n4. 📱 Phone Number Formatting Test:")
    print("-" * 40)
    
    test_phone = "0793706728"
    try:
        mpesa = MPesaAPI()
        formatted = mpesa.format_phone_number(test_phone)
        print(f"📞 Original: {test_phone}")
        print(f"📞 Formatted: {formatted}")
        
        if formatted == "254793706728":
            print("✅ Phone formatting correct")
        else:
            print("❌ Phone formatting incorrect")
    except Exception as e:
        print(f"❌ Phone formatting test failed: {str(e)}")
    
    # 5. Test Password Generation
    print("\n5. 🔐 Password Generation Test:")
    print("-" * 35)
    
    try:
        mpesa = MPesaAPI()
        password, timestamp = mpesa.generate_password()
        print(f"🔑 Password: {password[:20]}...")
        print(f"⏰ Timestamp: {timestamp}")
        print("✅ Password generation successful")
    except Exception as e:
        print(f"❌ Password generation failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🏁 Debug Report Complete")

def test_real_stk_push():
    """Test STK Push with real phone number"""
    print("\n💳 Real STK Push Test")
    print("=" * 30)
    
    phone = "0793706728"  # Your phone number
    amount = 1  # 1 shilling
    
    print(f"📱 Phone: {phone}")
    print(f"💰 Amount: KSH {amount}")
    
    confirm = input("\n⚠️  This will send a real STK Push to your phone. Continue? (yes/no): ")
    
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Test cancelled")
        return
    
    try:
        mpesa = MPesaAPI()
        
        result = mpesa.stk_push(
            phone_number=phone,
            amount=amount,
            account_reference='TEST-REAL-001',
            transaction_desc='Test payment - WAFUNGI-NATION'
        )
        
        print(f"\n📋 STK Push Result:")
        print(json.dumps(result, indent=2))
        
        if result['success']:
            print("\n✅ STK Push sent successfully!")
            print("📱 Check your phone for the M-Pesa prompt")
            
            checkout_id = result['checkout_request_id']
            
            input("\nPress Enter after completing the payment...")
            
            # Query status
            print("🔍 Checking payment status...")
            status = mpesa.query_stk_status(checkout_id)
            print(f"📊 Status Result:")
            print(json.dumps(status, indent=2))
            
        else:
            print(f"\n❌ STK Push failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ STK Push test failed: {str(e)}")

if __name__ == "__main__":
    debug_mpesa_setup()
    
    # Ask if user wants to test real STK Push
    test_real = input("\nDo you want to test real STK Push with 1 KSH? (yes/no): ")
    if test_real.lower() in ['yes', 'y']:
        test_real_stk_push()
