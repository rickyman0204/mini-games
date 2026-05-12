"""Wallet system - manages player money"""
from src.settings import INITIAL_WALLET


class Wallet:
    """Manages player's money balance"""

    def __init__(self):
        self.balance = INITIAL_WALLET
        self.total_spent = 0
        self.total_earned = 0
        self.animating = False
        self.anim_timer = 0.0
        self.anim_from = 0
        self.anim_to = 0

    def can_afford(self, cost: int) -> bool:
        """Check if player can afford something"""
        return self.balance >= cost

    def spend(self, amount: int) -> bool:
        """Spend money. Returns True if successful."""
        if self.balance < amount:
            return False
        self.balance -= amount
        self.total_spent += amount
        return True

    def add(self, amount: int):
        """Add money to wallet"""
        if amount > 0:
            self.balance += amount
            self.total_earned += amount

    def subtract(self, amount: int):
        """Subtract money (can go negative). Used for penalties."""
        self.balance -= amount

    def clear_all(self):
        """Clear all money (bug effect)"""
        self.balance = 0

    def reset(self):
        """Reset wallet to initial state"""
        self.balance = INITIAL_WALLET
        self.total_spent = 0
        self.total_earned = 0
