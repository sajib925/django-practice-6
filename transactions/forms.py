from django import forms
from .models import Transaction
from accounts.models import UserBankAccount

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'amount',
            'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account') # account value ke pop kore anlam
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].disabled = True # ei field disable thakbe
        self.fields['transaction_type'].widget = forms.HiddenInput() # user er theke hide kora thakbe

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()


class DepositForm(TransactionForm):
    def clean_amount(self): # amount field ke filter korbo
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount') # user er fill up kora form theke amra amount field er value ke niye aslam, 50
        if amount < min_deposit_amount:
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} $'
            )

        return amount


class WithdrawForm(TransactionForm):

    def clean_amount(self):
        account = self.account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance # 1000
        amount = self.cleaned_data.get('amount')
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $'
            )

        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $'
            )

        if amount > balance: # amount = 5000, tar balance ache 200
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not withdraw more than your account balance'
            )

        return amount



class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        return amount





class TransferForm(forms.ModelForm):
    recipient_username = forms.CharField(max_length=150)

    class Meta:
        model = Transaction
        fields = ['amount', 'recipient_username']

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)

    def clean_recipient_username(self):
        recipient_username = self.cleaned_data.get('recipient_username')
        try:
            self.recipient_account = UserBankAccount.objects.get(user__username=recipient_username)
        except UserBankAccount.DoesNotExist:
            raise forms.ValidationError('Recipient account not found.')
        return recipient_username

    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.account = self.account
        transaction.balance_after_transaction = self.account.balance - self.cleaned_data['amount']
        transaction.save()
        
        recipient_transaction = Transaction.objects.create(
            account=self.recipient_account,
            amount=self.cleaned_data['amount'],
            balance_after_transaction=self.recipient_account.balance + self.cleaned_data['amount'],
            transaction_type=3 # Assuming 3 is the code for transfer
        )
        
        self.account.balance -= self.cleaned_data['amount']
        self.account.save()
        
        self.recipient_account.balance += self.cleaned_data['amount']
        self.recipient_account.save()
        
        return transaction
