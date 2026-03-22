from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from backend.compliance.models import KYCProfile, KYCDocument, AMLTransaction
from backend.compliance.services import KYCService, AMLService, ComplianceEngine

User = get_user_model()

class KYCTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123'
        )
    
    def test_kyc_profile_creation(self):
        profile_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        }
        
        profile = KYCService.create_kyc_profile(self.user, profile_data)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.verification_level, 0)
        self.assertEqual(profile.first_name, 'John')
    
    def test_verification_level_update(self):
        profile_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        }
        
        profile = KYCService.create_kyc_profile(self.user, profile_data)
        result = KYCService.update_verification_level(self.user, 2)
        self.assertTrue(result)
        
        profile.refresh_from_db()
        self.assertEqual(profile.verification_level, 2)
    
    def test_transaction_limits_check(self):
        profile_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        }
        
        profile = KYCService.create_kyc_profile(self.user, profile_data)
        limits, details = KYCService.check_transaction_limits(self.user, Decimal('100'))
        
        self.assertIn('daily', limits)
        self.assertIn('monthly', limits)
        self.assertIn('annual', limits)


class AMLTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123'
        )
    
    def test_transaction_risk_analysis(self):
        transaction_data = {
            'amount': Decimal('15000'),  # High amount
            'to_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
        }
        
        analysis = AMLService.analyze_transaction(self.user, transaction_data)
        
        self.assertIn('risk_score', analysis)
        self.assertIn('risk_level', analysis)
        self.assertIn('risk_factors', analysis)
        self.assertIn('requires_review', analysis)
        
        # High amount should increase risk score
        self.assertGreater(analysis['risk_score'], 0)
    
    def test_high_risk_address_detection(self):
        transaction_data = {
            'amount': Decimal('1000'),
            'to_address': 'mixing_service_address_xyz'
        }
        
        analysis = AMLService.analyze_transaction(self.user, transaction_data)
        
        # Should detect high-risk address pattern
        self.assertTrue('high_risk_address' in analysis['risk_factors'])
    
    def test_compliance_engine_evaluation(self):
        transaction_data = {
            'amount': Decimal('100'),
            'to_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
        }
        
        result = ComplianceEngine.evaluate_transaction(self.user, transaction_data)
        
        self.assertIn('kyc_check', result)
        self.assertIn('aml_check', result)
        self.assertIn('limit_check', result)
        self.assertIn('approved', result)
        self.assertIn('reasons', result)


class ComplianceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123'
        )
    
    def test_kyc_document_creation(self):
        document = KYCDocument.objects.create(
            user=self.user,
            document_type='passport',
            document_number='P123456789',
            status='pending'
        )
        
        self.assertEqual(document.user, self.user)
        self.assertEqual(document.document_type, 'passport')
        self.assertEqual(document.status, 'pending')
    
    def test_aml_transaction_creation(self):
        aml_tx = AMLTransaction.objects.create(
            user=self.user,
            transaction_hash='0x1234567890abcdef',
            amount=Decimal('1000'),
            currency='BTC',
            from_address='1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            to_address='1B1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb',
            risk_level='medium',
            risk_score=30
        )
        
        self.assertEqual(aml_tx.user, self.user)
        self.assertEqual(aml_tx.risk_level, 'medium')
        self.assertEqual(aml_tx.risk_score, 30)
