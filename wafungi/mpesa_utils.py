import logging
import requests
import base64
import json
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import urllib3
from requests.exceptions import RequestException
from pyngrok import ngrok # type: ignore

logger = logging.getLogger(__name__)

class MPesaAPI:
    """
    M-Pesa API integration utility for STK Push payments
    """
    
    def __init__(self):
        # M-Pesa API credentials from settings
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.business_short_code = getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', '174379')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        public_url = ngrok.connect(8000).public_url
        self.callback_url = f"{public_url}/mpesa/callback/"
        print(f"\n * Ngrok callback URL: {self.callback_url}\n")
       
        
        # M-Pesa API URLs
        self.auth_url = getattr(settings, 'MPESA_AUTH_URL', 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials')
        self.stk_push_url = getattr(settings, 'MPESA_STK_PUSH_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest')
        self.query_url = getattr(settings, 'MPESA_QUERY_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query')
        
        # Log configuration for debugging
        logger.info(f"M-Pesa API initialized with:")
        logger.info(f"Consumer Key: {self.consumer_key[:10]}..." if self.consumer_key else "Consumer Key: NOT SET")
        logger.info(f"Business Short Code: {self.business_short_code}")
        logger.info(f"Auth URL: {self.auth_url}")
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa API"""
        try:
            # Check if credentials are set
            if not self.consumer_key or not self.consumer_secret:
                logger.error("M-Pesa credentials not set. Please check MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET in settings.")
                return None
            
            # Encode credentials
            credentials = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Requesting access token from: {self.auth_url}")
            logger.debug(f"Request headers: {headers}")
            
            response = requests.get(self.auth_url, headers=headers, timeout=30)
            
            logger.info(f"Access token response status: {response.status_code}")
            logger.debug(f"Access token response: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            access_token = result.get('access_token')
            
            if access_token:
                logger.info("Successfully obtained M-Pesa access token")
                return access_token
            else:
                logger.error(f"No access token in response: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting M-Pesa access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting M-Pesa access token: {e}")
            return None
    
    def generate_password(self):
        """Generate M-Pesa API password"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_short_code}{self.passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        return password, timestamp
    
    def format_phone_number(self, phone_number):
        """Format phone number to M-Pesa format (254XXXXXXXXX)"""
        # Remove any non-digit characters
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different formats
        if phone_number.startswith('254'):
            return phone_number
        elif phone_number.startswith('0'):
            return '254' + phone_number[1:]
        elif phone_number.startswith('7') or phone_number.startswith('1'):
            return '254' + phone_number
        else:
            # Assume it's a 9-digit number starting with 7 or 1
            return '254' + phone_number
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Initiate STK Push payment
        
        Args:
            phone_number (str): Customer phone number
            amount (float): Amount to be paid
            account_reference (str): Reference for the transaction
            transaction_desc (str): Description of the transaction
        
        Returns:
            dict: Response with success status and transaction details
        """
        access_token = self.get_access_token()
        if not access_token:
            return {
                'success': False, 
                'error': 'Failed to get access token. Please check M-Pesa credentials.',
                'error_code': 'AUTH_ERROR'
            }
        
        password, timestamp = self.generate_password()
        formatted_phone = self.format_phone_number(phone_number)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(float(amount)),  # M-Pesa expects integer
            'PartyA': formatted_phone,
            'PartyB': self.business_short_code,
            'PhoneNumber': formatted_phone,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc
        }
        
        try:
            logger.info(f"Initiating STK Push for {formatted_phone}, Amount: {amount}")
            logger.debug(f"STK Push payload: {payload}")
            
            response = requests.post(self.stk_push_url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"STK Push response status: {response.status_code}")
            logger.debug(f"STK Push response: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"STK Push response: {result}")
            
            if result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'response_description': result.get('ResponseDescription'),
                    'customer_message': result.get('CustomerMessage')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('ResponseDescription', 'Unknown error'),
                    'error_code': result.get('ResponseCode', 'UNKNOWN')
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during STK Push: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"STK Push error response: {e.response.text}")
            return {
                'success': False, 
                'error': f'Network error: {str(e)}',
                'error_code': 'NETWORK_ERROR'
            }
        except Exception as e:
            logger.error(f"Unexpected error during STK Push: {e}")
            return {
                'success': False, 
                'error': f'Unexpected error: {str(e)}',
                'error_code': 'SYSTEM_ERROR'
            }
    
    def query_stk_status(self, checkout_request_id):
        """
        Query the status of an STK Push transaction
        
        Args:
            checkout_request_id (str): CheckoutRequestID from STK Push response
            
        Returns:
            dict: Transaction status information
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
            'CheckoutRequestID': checkout_request_id
        }
        
        try:
            response = requests.post(self.query_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return {
                'success': True,
                'result_code': result.get('ResultCode'),
                'result_desc': result.get('ResultDesc'),
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Error querying STK status: {e}")
            return {'success': False, 'error': str(e)}

# Payment processing functions
def process_mpesa_payment(phone_number, amount, booking_id=None, recipient_phone=None):
    """
    Process M-Pesa payment for a booking
    
    Args:
        phone_number (str): Customer's phone number
        amount (float): Amount to pay
        booking_id (int, optional): Booking ID
        recipient_phone (str, optional): Phone number to receive the money
    
    Returns:
        dict: Payment processing result
    """
    mpesa = MPesaAPI()
    
    # Format the account reference and description
    if booking_id:
        account_reference = f'BOOKING-{booking_id}'
        transaction_desc = f'Payment for booking #{booking_id} - WAFUNGI-NATION'
    else:
        account_reference = f'PAYMENT-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        transaction_desc = 'Payment - WAFUNGI-NATION'
    
    result = mpesa.stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=account_reference,
        transaction_desc=transaction_desc
    )
    
    # Log the transaction attempt
    logger.info(f"Payment attempt for booking {booking_id}: {result}")
    
    return result

def verify_payment_status(checkout_request_id):
    """
    Verify the status of a payment transaction
    
    Args:
        checkout_request_id (str): CheckoutRequestID from STK Push
        
    Returns:
        dict: Payment verification result
    """
    mpesa = MPesaAPI()
    return mpesa.query_stk_status(checkout_request_id)

# Callback handling
def handle_mpesa_callback(callback_data):
    """
    Handle M-Pesa callback data
    
    Args:
        callback_data (dict): Callback data from M-Pesa
        
    Returns:
        dict: Processing result
    """
    try:
        # Extract relevant information from callback
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        if result_code == 0:  # Success
            # Extract transaction details
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            transaction_data = {}
            
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')
                transaction_data[name] = value
            
            return {
                'success': True,
                'transaction_id': transaction_data.get('MpesaReceiptNumber'),
                'amount': transaction_data.get('Amount'),
                'phone_number': transaction_data.get('PhoneNumber'),
                'transaction_date': transaction_data.get('TransactionDate'),
                'checkout_request_id': checkout_request_id
            }
        else:
            return {
                'success': False,
                'error': result_desc,
                'checkout_request_id': checkout_request_id
            }
            
    except Exception as e:
        logger.error(f"Error handling M-Pesa callback: {e}")
        return {'success': False, 'error': str(e)}
