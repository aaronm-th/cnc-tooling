from django import forms
from django.contrib.auth import get_user_model
from django.forms.widgets import ClearableFileInput



User = get_user_model()

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['photo', 'first_name', 'last_name', 'email', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set the widget for the 'photo' field
        #self.fields['photo'].widget = forms.FileInput()
        self.fields['photo'].widget = ClearableFileInput()


        # Set attributes for the 'photo' field's widget
        self.fields['photo'].widget.attrs = {
            'class': 'profile-photo',
            'id': 'profile-photo-id'
        }
