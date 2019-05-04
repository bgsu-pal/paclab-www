import json

from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from .mixins import EmailRequiredMixin
from .models import Paper, Profile, FilterDetail, ProjectSelector, Filter
from .forms import UserForm, UserPasswordForm, UserFormLogin, UserFormRegister, ProfileForm, ProjectSelectionForm, FilterDetailForm, FilterFormSet, EmailForm
from PIL import Image
from .tokens import email_verify_token
from .validators import validate_gh_token

class PapersView(ListView):
    template_name='website/papers.html'
    context_object_name='allPapers'
    def get_queryset(self):
        return Paper.objects.all()

class PeopleView(ListView):
    template_name='website/people.html'
    context_object_name = 'allPeople'
    def get_queryset(self):
        return User.objects.all().order_by('last_name')

class RegisterView(View):
    form_class = UserFormRegister
    template_name = 'website/register.html'
    def get(self, request):
        form = self.form_class(None)
        return render(request, self.template_name, { 'form' : form })

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.privacy_agreement = form.cleaned_data['privacy_agreement']
            user.profile.terms_agreement = form.cleaned_data['terms_agreement']
            user.profile.age_confirmation = form.cleaned_data['age_confirmation']
            user.profile.token = form.cleaned_data['token']
            user.profile.save()
            login(request, user)
            send_email_verify(request, user, 'Verify your email with PAClab')
            messages.info(request, 'Please check and confirm your email to complete registration.')
            return redirect('website:index')
        return render(request, self.template_name, { 'form' : form })

def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64)
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and email_verify_token.check_token(user, token):
        user.profile.active_email = True
        user.profile.save()
        login(request, user)
    messages.info(request, 'If you followed a valid email verification link, your email is now verified.')
    return redirect('website:index')

class LoginView(View):
    form_class = UserFormLogin
    template_name = 'website/login.html'

    def get(self, request):
        form = self.form_class(None)
        return render(request, self.template_name, { 'form' : form })

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if not user.profile.active_email:
                        messages.warning(request, ('Your email address is not yet verified!  Please verify email from your profile page.'))
                    return redirect('website:index')
        return render(request, self.template_name, { 'form' : form })

class ProjectListView(EmailRequiredMixin, ListView):
    template_name='website/projects.html'
    context_object_name='projects'
    def get_queryset(self):
        return ProjectSelector.objects.all().filter(user=self.request.user, is_alive=True)

def project_detail(request, slug):
    try:
        model = ProjectSelector.objects.get(slug=slug)
    except:
        raise Http404
    if model.is_alive == False:
        raise Http404
    if request.method == 'POST':
        form = EmailForm(request.POST)
        user = str(request.user.username)
        url = request.META['HTTP_HOST'] + '/project/detail/' + slug
        variables = { 'user' : user, 'url' : url }
        msg_html = get_template('website/project_selection_email.html')
        if form.is_valid():
            subject, from_email, to = 'Shared Project', request.user.email, form.cleaned_data['email'].split(',')
            text_content = 'A project has been shared with you!'
            html_content = msg_html.render(variables)
            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            messages.success(request, ('Success!'))
        else:
            messages.warning(request, ('Invalid form entry'))
    else:
        form = EmailForm()
    return render(request, 'website/projectsDetail.html', { 'project' : model, 'form' : form })

def project_delete(request, slug):
    try:
        model = ProjectSelector.objects.get(slug=slug)
    except:
        raise Http404
    if request.method == 'POST':
        if request.user == model.user or request.user.is_superuser:
            if request.user.profile.active_email:
                model.is_alive = False
                model.save()
                messages.info(request, ('You have deleted this project selector'))
                return redirect('website:project_list')
            else:
                messages.warning(request, ('Please activate your email before performing this task'))
        else:
            messages.warning(request, ('You are not the owner of this selector and cannot perform this task'))
    return render(request, 'website/delete.html')

def ajax_search(request):
    if request.is_ajax():
        q = request.GET.get('term', '').capitalize()
        search_qs = User.objects.filter(email__startswith=q)
        results = []
        for r in search_qs:
            results.append(r.email)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)

def logoutView(request):
    logout(request)
    messages.success(request, 'You have successfully logged out.')
    return redirect('website:index')

@login_required
def profile(request):
    if request.method == 'POST':
        userForm = UserForm(request.POST, instance=request.user)
        profileForm = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if userForm.is_valid() and profileForm.is_valid():
            userForm.save()
            profileForm.save()
            if 'email' in userForm.changed_data:
                request.user.profile.active_email = False
                request.user.profile.save()
                send_email_verify(request, request.user, 'Verify your email with PAClab')

            if profileForm.cleaned_data['photo']:
                image = Image.open(request.user.profile.photo)

                try:
                    x = float(request.POST.get('crop_x', 0))
                    y = float(request.POST.get('crop_y', 0))
                    w = float(request.POST.get('crop_w', 0))
                    h = float(request.POST.get('crop_h', 0))
                    if x and y and w and h:
                        image = image.crop((x, y, w + x, h + y))
                except:
                    pass

                image = image.resize(settings.THUMBNAIL_SIZE, Image.LANCZOS)
                image.save(request.user.profile.photo.path)

            messages.success(request, 'Profile successfully updated')
            return redirect('website:edit_profile')
        else:
            messages.error(request, 'Invalid form entry')
    else:    
        userForm = UserForm(instance=request.user)
        profileForm = ProfileForm(instance=request.user.profile)
    return render(request, 'website/editprofile.html', { 'userForm' : userForm, 'profileForm' : profileForm, 'min_width' : settings.THUMBNAIL_SIZE, 'min_height' : settings.THUMBNAIL_SIZE })

@login_required
def password_change(request):
    if request.method == 'POST':
        form = UserPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password updated!')
            return redirect('website:index')
        messages.error(request, 'Invalid form entry')
    else:
        form = UserPasswordForm(request.user)
    return render(request, 'website/password_change.html', { 'form' : form })

def project_selection(request):
    try:
        validate_gh_token(request.user.profile.token)
    except:
        request.user.profile.token = ''
        request.user.profile.save()
        messages.error(request, 'Your GitHub token is no longer valid. You must fix it.')
        return redirect('website:edit_profile')

    template_name = 'website/create_normal.html'
    if request.method == 'GET':
        p_form = ProjectSelectionForm(request.GET or None)
        formset = FilterFormSet(request.GET or None)
    elif request.method == 'POST':
        p_form = ProjectSelectionForm(request.POST)
        formset = FilterFormSet(request.POST)
        if p_form.is_valid() and formset.is_valid():
            selector = ProjectSelector()
            selector.user = request.user
            selector.input_dataset = p_form.cleaned_data['input_dataset']
            selector.save()
            for form in formset:
                pfilter = form.cleaned_data.get('pfilter')
                value = form.cleaned_data.get('value')
                if value and pfilter:
                    try:
                        connection = FilterDetail()
                        connection.project_selector = ProjectSelector.objects.all().last()
                        pk = form.cleaned_data.get('pfilter').id
                        connection.pfilter = Filter.objects.get(pk=pk)
                        connection.value = form.cleaned_data['value']
                        connection.save()
                    except:
                        pass
            messages.success(request, ('Project selection created successfully.'))
            return redirect(reverse_lazy('website:project_detail', args=(selector.slug,)))
        messages.error(request, ('Invalid form entry'))
    return render(request, template_name, {
        'p_form' : p_form,
        'formset': formset,
    })

def filter_default(request):
    val = int(request.GET.get('id', 0))
    pfilter = Filter.objects.get(pk=val)
    return JsonResponse({ 'id' : val, 'default' : pfilter.default_val })

def verify_email_link(request):
    return send_email_verify(request, request.user, 'Reconfirm email address')

def send_email_verify(request, user, title):
    current_site = get_current_site(request)
    message = render_to_string('website/email_verification_email.html', {
        'user' : user,
        'domain' : current_site.domain,
        'uid' : urlsafe_base64_encode(force_bytes(user.pk)),
        'token' : email_verify_token.make_token(user),
    })
    to_email = user.email
    email = EmailMessage(title, message, to=[to_email])
    email.send()
    messages.info(request, "If an account exists with the email you entered, we've emailed you a link for verifying the email address. You should receive the email shortly. If you don't receive an email, check your spam/junk folder and please make sure your email address is entered correctly in your profile.")
    return redirect('website:index')
