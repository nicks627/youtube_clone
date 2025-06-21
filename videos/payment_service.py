import requests
import json
import hashlib
import hmac
import time
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import PaymentSettings, Donation, Purchase

class LinkPaymentService:
    """
    Link決済APIとの統合サービス
    """
    
    def __init__(self, user=None, api_key=None, secret_key=None):
        """
        Initialize the Link Payment Service
        
        Args:
            user: User object (will use their payment settings)
            api_key: Direct API key (optional)
            secret_key: Direct secret key (optional)
        """
        if user and hasattr(user, 'payment_settings'):
            self.api_key = user.payment_settings.link_api_key
            self.secret_key = user.payment_settings.link_secret_key
        else:
            self.api_key = api_key
            self.secret_key = secret_key
        
        # Link API endpoints (これは実際のLink APIエンドポイントに置き換える必要があります)
        self.base_url = getattr(settings, 'LINK_API_BASE_URL', 'https://api.link.example.com')
        self.payment_endpoint = f"{self.base_url}/v1/payments"
        
    def _generate_signature(self, payload, timestamp):
        """
        Generate HMAC signature for API authentication
        """
        if not self.secret_key:
            raise ValueError("Secret key is required for signature generation")
        
        message = f"{timestamp}.{json.dumps(payload, sort_keys=True)}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_request(self, method, url, data=None):
        """
        Make authenticated request to Link API
        """
        if not self.api_key:
            raise ValueError("API key is required")
        
        timestamp = str(int(time.time()))
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Timestamp': timestamp,
        }
        
        if data and self.secret_key:
            signature = self._generate_signature(data, timestamp)
            headers['X-Signature'] = signature
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Link API request failed: {str(e)}")
    
    def create_payment(self, amount, description, callback_url, metadata=None):
        """
        Create a payment request
        
        Args:
            amount: Payment amount (Decimal or float)
            description: Payment description
            callback_url: URL to redirect after payment
            metadata: Additional metadata (dict)
        
        Returns:
            dict: Payment response from Link API
        """
        if not self.api_key:
            raise ValueError("API key is not configured")
        
        payload = {
            'amount': int(Decimal(str(amount)) * 100),  # Convert to cents
            'currency': 'JPY',
            'description': description,
            'callback_url': callback_url,
            'metadata': metadata or {}
        }
        
        # For development/testing purposes, return a mock response
        # In production, replace this with actual API call
        if not hasattr(settings, 'LINK_API_BASE_URL'):
            return {
                'id': f'payment_mock_{int(time.time())}',
                'status': 'pending',
                'amount': payload['amount'],
                'currency': payload['currency'],
                'description': payload['description'],
                'payment_url': f'https://checkout.link.example.com/pay/mock_{int(time.time())}',
                'created_at': timezone.now().isoformat()
            }
        
        return self._make_request('POST', self.payment_endpoint, payload)
    
    def get_payment_status(self, payment_id):
        """
        Get payment status from Link API
        
        Args:
            payment_id: Payment ID from Link
        
        Returns:
            dict: Payment status response
        """
        if not hasattr(settings, 'LINK_API_BASE_URL'):
            # Mock response for development
            return {
                'id': payment_id,
                'status': 'completed',
                'amount': 100000,  # ¥1000 in cents
                'currency': 'JPY'
            }
        
        url = f"{self.payment_endpoint}/{payment_id}"
        return self._make_request('GET', url)
    
    def process_donation(self, from_user, to_user, amount, message="", video=None):
        """
        Process a donation payment
        
        Args:
            from_user: User making the donation
            to_user: User receiving the donation
            amount: Donation amount
            message: Optional message
            video: Optional video associated with donation
        
        Returns:
            tuple: (donation_object, payment_response)
        """
        # Create donation record
        donation = Donation.objects.create(
            from_user=from_user,
            to_user=to_user,
            video=video,
            amount=Decimal(str(amount)),
            message=message,
            status='pending'
        )
        
        try:
            # Create payment with Link
            description = f"投げ銭: {to_user.username}さんへ"
            if video:
                description += f" ({video.title})"
            
            callback_url = f"{settings.SITE_URL}/payments/donation/callback/"
            metadata = {
                'donation_id': donation.id,
                'type': 'donation'
            }
            
            payment_response = self.create_payment(
                amount=amount,
                description=description,
                callback_url=callback_url,
                metadata=metadata
            )
            
            # Update donation with payment ID
            donation.link_transaction_id = payment_response.get('id')
            donation.save()
            
            return donation, payment_response
        
        except Exception as e:
            # Mark donation as failed
            donation.status = 'failed'
            donation.save()
            raise e
    
    def process_content_purchase(self, user, paid_content):
        """
        Process a paid content purchase
        
        Args:
            user: User making the purchase
            paid_content: PaidContent object
        
        Returns:
            tuple: (purchase_object, payment_response)
        """
        # Check if user already purchased this content
        existing_purchase = Purchase.objects.filter(
            user=user,
            paid_content=paid_content,
            status='completed'
        ).first()
        
        if existing_purchase:
            raise ValueError("このコンテンツは既に購入済みです")
        
        # Create purchase record
        purchase = Purchase.objects.create(
            user=user,
            paid_content=paid_content,
            amount=paid_content.price,
            status='pending'
        )
        
        try:
            # Create payment with Link
            description = f"コンテンツ購入: {paid_content.title}"
            callback_url = f"{settings.SITE_URL}/payments/purchase/callback/"
            metadata = {
                'purchase_id': purchase.id,
                'type': 'purchase'
            }
            
            payment_response = self.create_payment(
                amount=paid_content.price,
                description=description,
                callback_url=callback_url,
                metadata=metadata
            )
            
            # Update purchase with payment ID
            purchase.link_transaction_id = payment_response.get('id')
            purchase.save()
            
            return purchase, payment_response
        
        except Exception as e:
            # Mark purchase as failed
            purchase.status = 'failed'
            purchase.save()
            raise e
    
    def handle_payment_callback(self, payment_id, status):
        """
        Handle payment completion callback
        
        Args:
            payment_id: Payment ID from Link
            status: Payment status
        
        Returns:
            bool: Success status
        """
        try:
            # Update donation if exists
            donation = Donation.objects.filter(link_transaction_id=payment_id).first()
            if donation:
                if status == 'completed':
                    donation.status = 'completed'
                    donation.completed_at = timezone.now()
                elif status == 'failed':
                    donation.status = 'failed'
                donation.save()
                return True
            
            # Update purchase if exists
            purchase = Purchase.objects.filter(link_transaction_id=payment_id).first()
            if purchase:
                if status == 'completed':
                    purchase.status = 'completed'
                    purchase.completed_at = timezone.now()
                elif status == 'failed':
                    purchase.status = 'failed'
                purchase.save()
                return True
            
            return False
        
        except Exception as e:
            print(f"Error handling payment callback: {e}")
            return False

def get_payment_service(user=None):
    """
    Factory function to get a payment service instance
    """
    if user and hasattr(user, 'payment_settings') and user.payment_settings.is_payments_enabled:
        return LinkPaymentService(user=user)
    return None