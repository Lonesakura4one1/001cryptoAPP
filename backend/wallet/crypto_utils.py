import hashlib
import hmac
import secrets
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der
from mnemonic import Mnemonic
import base58
from bech32 import bech32_encode, bech32_decode
import struct


class HDWallet:
    """Hierarchical Deterministic Wallet implementation"""
    
    def __init__(self, seed=None):
        if seed:
            self.seed = seed
            self.master_key = self._generate_master_key(seed)
        else:
            self.seed = self._generate_seed()
            self.master_key = self._generate_master_key(self.seed)
    
    def _generate_seed(self, strength=256):
        """Generate random seed"""
        return secrets.token_bytes(strength // 8)
    
    def _generate_master_key(self, seed):
        """Generate master key from seed using BIP32"""
        # Simplified BIP32 implementation
        hash_bytes = hashlib.sha512(seed).digest()
        private_key = hash_bytes[:32]
        chain_code = hash_bytes[32:]
        
        return {
            'private_key': private_key,
            'chain_code': chain_code,
            'depth': 0,
            'index': 0,
            'fingerprint': b'\x00\x00\x00\x00'
        }
    
    def derive_child(self, parent_key, index, hardened=False):
        """Derive child key using BIP32"""
        if hardened:
            index |= 0x80000000
            data = b'\x00' + parent_key['private_key'] + struct.pack('>I', index)
        else:
            # Get public key (simplified)
            public_key = self._get_public_key(parent_key['private_key'])
            data = public_key + struct.pack('>I', index)
        
        # HMAC-SHA512 with chain code
        hash_bytes = hmac.new(parent_key['chain_code'], data, hashlib.sha512).digest()
        private_key = hash_bytes[:32]
        chain_code = hash_bytes[32:]
        
        # Add parent private key to child private key (mod n)
        child_private = (int.from_bytes(private_key, 'big') + 
                         int.from_bytes(parent_key['private_key'], 'big')) % SECP256k1.order
        child_private = child_private.to_bytes(32, 'big')
        
        return {
            'private_key': child_private,
            'chain_code': chain_code,
            'depth': parent_key['depth'] + 1,
            'index': index,
            'fingerprint': self._get_fingerprint(parent_key['private_key'])
        }
    
    def _get_public_key(self, private_key):
        """Get public key from private key"""
        sk = SigningKey.from_string(private_key, curve=SECP256k1)
        return sk.get_verifying_key().to_string("uncompressed")
    
    def _get_fingerprint(self, private_key):
        """Get key fingerprint"""
        public_key = self._get_public_key(private_key)
        hash_bytes = hashlib.sha256(public_key).digest()
        return hashlib.new('ripemd160', hash_bytes).digest()[:4]
    
    def derive_path(self, path):
        """Derive key from BIP32 path like m/44'/0'/0'/0/0"""
        current_key = self.master_key
        
        for part in path.split('/')[1:]:  # Skip 'm/'
            if part == '':
                continue
            
            hardened = part.endswith("'")
            index = int(part.rstrip("'"))
            current_key = self.derive_child(current_key, index, hardened)
        
        return current_key
    
    def get_address(self, private_key, address_type='p2pkh'):
        """Generate Bitcoin address from private key"""
        if address_type == 'p2pkh':
            return self._p2pkh_address(private_key)
        elif address_type == 'p2sh':
            return self._p2sh_address(private_key)
        elif address_type == 'bech32':
            return self._bech32_address(private_key)
        else:
            raise ValueError(f"Unsupported address type: {address_type}")
    
    def _p2pkh_address(self, private_key):
        """Generate P2PKH address"""
        public_key = self._get_public_key(private_key)
        hash_bytes = hashlib.sha256(public_key[1:]).digest()  # Skip prefix
        hash160 = hashlib.new('ripemd160', hash_bytes).digest()
        
        # Add version byte (0x00 for mainnet)
        payload = b'\x00' + hash160
        
        # Calculate checksum
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        # Base58 encode
        return base58.b58encode(payload + checksum).decode()
    
    def _bech32_address(self, private_key):
        """Generate Bech32 (P2WPKH) address"""
        public_key = self._get_public_key(private_key)
        hash_bytes = hashlib.sha256(public_key[1:]).digest()
        hash160 = hashlib.new('ripemd160', hash_bytes).digest()
        
        # Bech32 encoding (simplified)
        witprog = [0x00] + list(hash160)
        return bech32_encode('bc', witprog)


class MultiSigWallet:
    """Multi-signature wallet implementation"""
    
    def __init__(self, m, n):
        self.m = m  # Required signatures
        self.n = n  # Total keys
        self.public_keys = []
        self.redeem_script = None
    
    def add_public_key(self, public_key):
        """Add public key to multisig"""
        if len(self.public_keys) < self.n:
            self.public_keys.append(public_key)
            return True
        return False
    
    def generate_redeem_script(self):
        """Generate redeem script for P2SH"""
        if len(self.public_keys) != self.n:
            raise ValueError("Not enough public keys")
        
        script = bytes([0x52 + self.m - 1])  # OP_M
        
        for pubkey in self.public_keys:
            script += bytes([len(pubkey)]) + pubkey
        
        script += bytes([0x52 + self.n - 1])  # OP_N
        script += bytes([0xae])  # OP_CHECKMULTISIG
        
        self.redeem_script = script
        return script
    
    def get_address(self):
        """Get P2SH address for multisig"""
        if not self.redeem_script:
            self.generate_redeem_script()
        
        hash160 = hashlib.new('ripemd160', hashlib.sha256(self.redeem_script).digest()).digest()
        
        # Add version byte (0x05 for P2SH mainnet)
        payload = b'\x05' + hash160
        
        # Calculate checksum
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        # Base58 encode
        return base58.b58encode(payload + checksum).decode()


class CryptoUtils:
    """Cryptographic utility functions"""
    
    @staticmethod
    def generate_mnemonic(strength=256):
        """Generate mnemonic phrase"""
        mnemo = Mnemonic("english")
        return mnemo.generate(strength)
    
    @staticmethod
    def mnemonic_to_seed(mnemonic, passphrase=""):
        """Convert mnemonic to seed"""
        mnemo = Mnemonic("english")
        return mnemo.to_seed(mnemonic, passphrase)
    
    @staticmethod
    def verify_mnemonic(mnemonic):
        """Verify mnemonic phrase"""
        mnemo = Mnemonic("english")
        return mnemo.check(mnemonic)
    
    @staticmethod
    def sign_message(private_key, message):
        """Sign message with private key"""
        sk = SigningKey.from_string(private_key, curve=SECP256k1)
        message_hash = hashlib.sha256(message.encode()).digest()
        signature = sk.sign(message_hash, sigencode=sigencode_der)
        return signature
    
    @staticmethod
    def verify_signature(public_key, message, signature):
        """Verify signature"""
        from ecdsa import VerifyingKey
        vk = VerifyingKey.from_string(public_key, curve=SECP256k1)
        message_hash = hashlib.sha256(message.encode()).digest()
        try:
            return vk.verify(signature, message_hash, sigdecode=sigdecode_der)
        except:
            return False
    
    @staticmethod
    def encrypt_private_key(private_key, password):
        """Encrypt private key with password (simplified)"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        # Derive key from password
        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt private key
        f = Fernet(key)
        encrypted_data = f.encrypt(private_key)
        
        return {
            'encrypted_key': base64.b64encode(encrypted_data).decode(),
            'salt': base64.b64encode(salt).decode()
        }
    
    @staticmethod
    def decrypt_private_key(encrypted_data, password):
        """Decrypt private key with password"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HIMP
        
        encrypted_key = base64.b64decode(encrypted_data['encrypted_key'])
        salt = base64.b64decode(encrypted_data['salt'])
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt private key
        f = Fernet(key)
        return f.decrypt(encrypted_key)
