from django.contrib.auth.models import User
from django import forms
from django.forms import formset_factory
from .models import Profile, ProjectSelector, Filter, FilterDetail, Book
from .validators import validate_file_size

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

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
        fields = ['input_dataset', 'input_selection', 'output_selection']

class FilterDetailForm(forms.Form):
    pfilter = forms.ModelChoiceField(Filter.objects.all())
    value = forms.CharField(
        max_length=1000,
        widget=forms.TextInput(attrs={
            'class' : 'form-control',
            'placeholder' : 'Enter value'
        }),
        required=False)

howmany = Filter.objects.all().count()
FilterFormSet = formset_factory(FilterDetailForm, extra=howmany)

class BookForm(forms.Form):
    name = forms.CharField(
        label='Book Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Book Name here'
        })
    )
BookFormset = formset_factory(BookForm)
