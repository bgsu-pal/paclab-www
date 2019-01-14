from django.contrib.auth.models import User
from django import forms
from django.forms import modelformset_factory
from .models import Profile, ProjectSelector, Filter, FilterDetail
from .validators import validate_file_size

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class UserFormLogin(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'password']

class UserFormRegister(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

class ProfileForm(forms.ModelForm):
    photo = forms.ImageField(validators=[validate_file_size])
    class Meta:
        model = Profile
        fields = ['photo', 'bio', 'token']
        labels = {
            'photo' : 'Photo',
            'bio' : 'Bio',
            'token' : 'Github Personal Access Token'
        }

class ProjectSelectionForm(forms.ModelForm):
    # pfilter = forms.ModelMultipleChoiceField(Filter.objects.all())
    class Meta:
        model = ProjectSelector
        fields = ['input_dataset', 'input_selection', 'output_selection', 'user']

class FilterDetailForm(forms.Form):
    pfilter = forms.ModelMultipleChoiceField(Filter.objects.all())
    value = forms.CharField(max_length=1000, widget=forms.Textarea)
    INT = 'Integer'
    STRING = 'String'
    LIST = 'List'
    TYPE_CHOICES = (
        (INT, 'Integer'),
        (STRING, 'String'),
        (LIST, 'List'),
    )
    val_type = forms.ChoiceField(choices=TYPE_CHOICES)
