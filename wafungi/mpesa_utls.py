import requests # type: ignore
import base64
from datetime import datetime
from django.conf import settings

class MPesaAPI:
    """
    M-Pesa API integration utility
    This is a basic structure for M-Pesa integration
    """
    
    def __init__(self):
        # These would be stored in settings.py or environment variables
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.business_short_code = getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', '')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        
        # M-Pesa API URLs (Sandbox)
        self.auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        self.stk_push_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa API"""
        try:
            # Encode credentials
            credentials = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(self.auth_url, headers=headers)
            response.raise_for_status()
            
            return response.json().get('access_token')
        except Exception as e:
            print(f"Error getting M-Pesa access token: {e}")
            return None
    
    def generate_password(self):
        """Generate M-Pesa API password"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_short_code}{self.passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        return password, timestamp
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Initiate STK Push payment
        
        Args:
            phone_number (str): Customer phone number (254XXXXXXXXX format)
            amount (int): Amount to be paid
            account_reference (str): Reference for the transaction
            transaction_desc (str): Description of the transaction
        """
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        password, timestamp = self.generate_password()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': self.business_short_code,
            'PhoneNumber': phone_number,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc
        }
        
        try:
            response = requests.post(self.stk_push_url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'response_description': result.get('ResponseDescription')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('ResponseDescription', 'Unknown error')
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Usage example:
def process_mpesa_payment(phone_number, amount, booking_id):
    """
    Process M-Pesa payment for a booking
    """
    mpesa = MPesaAPI()
    
    # Format phone number to M-Pesa format
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('7'):
        phone_number = '254' + phone_number
    
    result = mpesa.stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=f'BOOKING-{booking_id}',
        transaction_desc=f'Payment for booking #{booking_id}'
    )
    
    return result
