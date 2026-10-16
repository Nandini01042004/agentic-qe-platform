"""Enterprise Payment Gateway with Idempotency and Currency Validation."""

import uuid
import time
from typing import Dict, Any, Optional


class PaymentError(Exception):
    """Base exception for payment operations."""
    pass


class InsufficientFundsError(PaymentError):
    """Raised when account balance is less than transaction amount."""
    pass


class IdempotencyConflictError(PaymentError):
    """Raised when an idempotency key is reused with mismatched parameters."""
    pass


class PaymentGateway:
    """
    Mock payment processing engine supporting idempotency keys,
    multi-currency validation, ledger debiting, and refunds.
    """

    SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "INR"}

    def __init__(self, api_key: str = "sk_live_enterprise_default"):
        if not api_key:
            raise ValueError("API key must be provided.")
        self.api_key = api_key
        self._accounts: Dict[str, float] = {}
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}

    def set_account_balance(self, account_id: str, balance: float) -> None:
        """Helper to initialize or update account funds."""
        if balance < 0:
            raise ValueError("Initial balance cannot be negative.")
        self._accounts[account_id] = float(balance)

    def get_account_balance(self, account_id: str) -> float:
        """Returns current balance for account."""
        return self._accounts.get(account_id, 0.0)

    def charge(
        self,
        account_id: str,
        amount: float,
        currency: str = "USD",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Charges an account for a given amount.
        Guarantees idempotency when an idempotency_key is provided.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        clean_currency = currency.upper()
        if clean_currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"Currency '{clean_currency}' not supported. Must be in {self.SUPPORTED_CURRENCIES}")

        # Idempotency Check
        if idempotency_key:
            if idempotency_key in self._idempotency_cache:
                cached = self._idempotency_cache[idempotency_key]
                if cached["account_id"] != account_id or cached["amount"] != amount or cached["currency"] != clean_currency:
                    raise IdempotencyConflictError("Idempotency key reused with conflicting transaction parameters.")
                return cached["transaction"]

        current_balance = self._accounts.get(account_id, 0.0)
        if current_balance < amount:
            raise InsufficientFundsError(
                f"Account '{account_id}' has insufficient balance ({current_balance}) for charge of {amount}."
            )

        # Debit ledger
        self._accounts[account_id] = round(current_balance - amount, 2)

        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        tx_record = {
            "transaction_id": tx_id,
            "account_id": account_id,
            "amount": float(amount),
            "currency": clean_currency,
            "status": "succeeded",
            "timestamp": time.time(),
        }
        self._transactions[tx_id] = tx_record

        if idempotency_key:
            self._idempotency_cache[idempotency_key] = {
                "account_id": account_id,
                "amount": amount,
                "currency": clean_currency,
                "transaction": tx_record,
            }

        return tx_record

    def refund(self, transaction_id: str) -> Dict[str, Any]:
        """Refunds a settled charge and restores account funds."""
        if transaction_id not in self._transactions:
            raise ValueError(f"Transaction '{transaction_id}' not found.")

        tx = self._transactions[transaction_id]
        if tx["status"] == "refunded":
            raise ValueError("Transaction has already been refunded.")

        account_id = tx["account_id"]
        amount = tx["amount"]

        # Credit funds back
        self._accounts[account_id] = round(self._accounts.get(account_id, 0.0) + amount, 2)
        tx["status"] = "refunded"
        tx["refunded_at"] = time.time()

        return tx
