from django.utils.translation import ugettext_lazy as _
from django import forms
from django.conf import settings

from allauth.account.models import EmailAddress
from allauth.account.forms import BaseSignupForm
from allauth.account.utils import send_email_confirmation, setup_user_email

from models import SocialAccount

class SignupForm(BaseSignupForm):

    def __init__(self, *args, **kwargs):
        self.sociallogin = kwargs.pop('sociallogin')
        user = self.sociallogin.account.user
        initial = { 'email': user.email or '',
                    'username': user.username or '',
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '' }
        kwargs['initial'] = initial
        super(SignupForm, self).__init__(*args, **kwargs)

    def save(self, request):
        new_user = self.create_user()
        self.sociallogin.account.user = new_user
        self.sociallogin.save()
        super(SignupForm, self).save(new_user) 
        # Confirmation last (save may alter first_name etc -- used in mail)
        setup_user_email(request, new_user)
        if settings.SEND_EMAIL_CONFIRMATIONS_TO_SOCIAL:
            send_email_confirmation(request, new_user)
        return new_user


class DisconnectForm(forms.Form):
    account = forms.ModelChoiceField(queryset=SocialAccount.objects.none(),
                                     widget=forms.RadioSelect,
                                     required=True)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.accounts = SocialAccount.objects.filter(user=self.user)
        super(DisconnectForm, self).__init__(*args, **kwargs)
        self.fields['account'].queryset = self.accounts

    def clean(self):
        if len(self.accounts) == 1:
            # No usable password would render the local account unusable
            if not self.user.has_usable_password():
                raise forms.ValidationError(_("Your account has no password set up."))
            # No email address, no password reset
            if EmailAddress.objects.filter(user=self.user,
                                           verified=True).count() == 0:
                raise forms.ValidationError(_("Your account has no verified e-mail address."))
        return self.cleaned_data

    def save(self):
        self.cleaned_data['account'].delete()
