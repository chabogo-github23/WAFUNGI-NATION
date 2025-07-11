from django.core.management.base import BaseCommand
from django.conf import settings
from wafungi.mpesa_utils import MPesaAPI, process_mpesa_payment
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test M-Pesa integration with various scenarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--validate-setup',
            action='store_true',
            help='Validate M-Pesa configuration setup',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test M-Pesa API connection and access token',
        )
        parser.add_argument(
            '--test-stk-push',
            action='store_true',
            help='Test STK Push functionality',
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number for STK Push test (format: 254XXXXXXXXX or 07XXXXXXXX)',
        )
        parser.add_argument(
            '--amount',
            type=float,
            default=1.0,
            help='Amount to test (default: 1.0 KSH)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting M-Pesa Integration Tests'))
        
        if options['validate_setup']:
            self.validate_setup()
        
        if options['test_connection']:
            self.test_connection()
        
        if options['test_stk_push']:
            phone = options.get('phone')
            amount = options.get('amount', 1.0)
            if not phone:
                self.stdout.write(self.style.ERROR('❌ Phone number required for STK Push test. Use --phone=0793706728'))
                return
            self.test_stk_push(phone, amount)

    def validate_setup(self):
        """Validate M-Pesa configuration"""
        self.stdout.write('\n📋 Validating M-Pesa Configuration...')
        
        required_settings = [
            'MPESA_CONSUMER_KEY',
            'MPESA_CONSUMER_SECRET',
            'MPESA_BUSINESS_SHORT_CODE',
            'MPESA_PASSKEY',
            'MPESA_CALLBACK_URL',
        ]
        
        missing_settings = []
        for setting in required_settings:
            value = getattr(settings, setting, None)
            if not value:
                missing_settings.append(setting)
            else:
                # Mask sensitive data for display
                if 'KEY' in setting or 'SECRET' in setting or 'PASSKEY' in setting:
                    display_value = f"{value[:10]}..." if len(value) > 10 else "***"
                else:
                    display_value = value
                self.stdout.write(f'  ✅ {setting}: {display_value}')
        
        if missing_settings:
            self.stdout.write(self.style.ERROR(f'❌ Missing settings: {", ".join(missing_settings)}'))
            return False
        
        # Check environment
        environment = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        self.stdout.write(f'  ✅ Environment: {environment}')
        
        # Check URLs
        auth_url = getattr(settings, 'MPESA_AUTH_URL', '')
        stk_url = getattr(settings, 'MPESA_STK_PUSH_URL', '')
        self.stdout.write(f'  ✅ Auth URL: {auth_url}')
        self.stdout.write(f'  ✅ STK Push URL: {stk_url}')
        
        self.stdout.write(self.style.SUCCESS('✅ Configuration validation completed'))
        return True

    def test_connection(self):
        """Test M-Pesa API connection"""
        self.stdout.write('\n🔗 Testing M-Pesa API Connection...')
        
        try:
            mpesa = MPesaAPI()
            
            # Test access token
            self.stdout.write('  📡 Requesting access token...')
            token = mpesa.get_access_token()
            
            if token:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Access token obtained: {token[:20]}...'))
                
                # Test phone number formatting
                self.stdout.write('  📱 Testing phone number formatting...')
                test_numbers = ['0793706728', '793706728', '254793706728']
                for number in test_numbers:
                    formatted = mpesa.format_phone_number(number)
                    self.stdout.write(f'    {number} → {formatted}')
                
                # Test password generation
                self.stdout.write('  🔐 Testing password generation...')
                password, timestamp = mpesa.generate_password()
                self.stdout.write(f'    Password: {password[:20]}...')
                self.stdout.write(f'    Timestamp: {timestamp}')
                
                self.stdout.write(self.style.SUCCESS('✅ Connection test completed successfully'))
                return True
            else:
                self.stdout.write(self.style.ERROR('❌ Failed to obtain access token'))
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Connection test failed: {str(e)}'))
            return False

    def test_stk_push(self, phone_number, amount):
        """Test STK Push functionality"""
        self.stdout.write(f'\n💳 Testing STK Push with {phone_number} for KSH {amount}...')
        
        try:
            # Format phone number
            mpesa = MPesaAPI()
            formatted_phone = mpesa.format_phone_number(phone_number)
            self.stdout.write(f'  📱 Formatted phone: {formatted_phone}')
            
            # Confirm before proceeding
            self.stdout.write(self.style.WARNING(f'⚠️  This will send an STK Push for KSH {amount} to {formatted_phone}'))
            confirm = input('Do you want to proceed? (yes/no): ')
            
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write('❌ Test cancelled by user')
                return
            
            # Initiate STK Push
            self.stdout.write('  🚀 Initiating STK Push...')
            result = mpesa.stk_push(
                phone_number=formatted_phone,
                amount=amount,
                account_reference='TEST-001',
                transaction_desc='Test payment from WAFUNGI-NATION'
            )
            
            self.stdout.write(f'  📋 STK Push Result: {result}')
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('✅ STK Push initiated successfully!'))
                self.stdout.write(f'  🆔 Checkout Request ID: {result["checkout_request_id"]}')
                self.stdout.write(f'  💬 Customer Message: {result.get("customer_message", "N/A")}')
                
                # Wait for user to complete payment
                self.stdout.write('\n📱 Please check your phone for the M-Pesa prompt and complete the payment...')
                input('Press Enter after completing or cancelling the payment...')
                
                # Query payment status
                self.stdout.write('  🔍 Querying payment status...')
                status_result = mpesa.query_stk_status(result['checkout_request_id'])
                self.stdout.write(f'  📊 Status Result: {status_result}')
                
                if status_result['success']:
                    result_code = status_result.get('result_code')
                    result_desc = status_result.get('result_desc')
                    
                    if result_code == 0:
                        self.stdout.write(self.style.SUCCESS('✅ Payment completed successfully!'))
                    elif result_code == 1032:
                        self.stdout.write(self.style.WARNING('⚠️  Payment was cancelled by user'))
                    else:
                        self.stdout.write(self.style.ERROR(f'❌ Payment failed: {result_desc}'))
                else:
                    self.stdout.write(self.style.ERROR('❌ Failed to query payment status'))
                
            else:
                self.stdout.write(self.style.ERROR(f'❌ STK Push failed: {result["error"]}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ STK Push test failed: {str(e)}'))

    def test_with_booking(self, phone_number, amount=1.0):
        """Test payment with actual booking simulation"""
        self.stdout.write(f'\n🎯 Testing payment processing with booking simulation...')
        
        try:
            result = process_mpesa_payment(
                phone_number=phone_number,
                amount=amount,
                booking_id=999,  # Test booking ID
                recipient_phone=None
            )
            
            self.stdout.write(f'  📋 Payment Processing Result: {result}')
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('✅ Payment processing test successful!'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Payment processing failed: {result["error"]}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Payment processing test failed: {str(e)}'))
