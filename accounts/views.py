# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from lessons.models import Lesson, UserProgress, UserProfile
from django.http import JsonResponse
from django.urls import reverse
from django.core.files.storage import default_storage

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('course_list')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'С возвращением, {user.username}!')
            return redirect('course_list')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def custom_logout(request):
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта')
    return redirect('course_list')

@login_required
def profile(request):
    profile_obj = UserProfile.objects.get_or_create(user=request.user)[0]
    completed = UserProgress.objects.filter(user=request.user, is_completed=True).count()
    total = Lesson.objects.count()
    progress = UserProgress.objects.filter(user=request.user).select_related('lesson').order_by('-lesson__order')[:5]
    
    # XP на текущем уровне
    xp_at_current = profile_obj.get_xp_at_current_level()
    xp_for_next = profile_obj.get_xp_for_next_level()
    xp_to_next = xp_for_next - xp_at_current
    if xp_to_next < 0:
        xp_to_next = 0
    
    context = {
        'completed_lessons': completed,
        'total_lessons': total,
        'progress_percent': round(completed / total * 100) if total > 0 else 0,
        'user_progress': progress,
        'user_xp': xp_at_current,
        'user_level': profile_obj.level,
        'xp_for_next_level': xp_for_next,
        'level_progress': profile_obj.get_progress_to_next_level(),
        'xp_to_next_level': xp_to_next,
        'total_xp': profile_obj.xp,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_data(request):
    profile_obj = UserProfile.objects.get_or_create(user=request.user)[0]
    completed = UserProgress.objects.filter(user=request.user, is_completed=True).count()
    total = Lesson.objects.count()
    
    xp_at_current = profile_obj.get_xp_at_current_level()
    xp_for_next = profile_obj.get_xp_for_next_level()
    xp_to_next = xp_for_next - xp_at_current
    if xp_to_next < 0:
        xp_to_next = 0
    
    data = {
        'username': request.user.username,
        'email': request.user.email,
        'bio': profile_obj.bio,
        'avatar': request.user.profile.avatar.url if request.user.profile.avatar else None,
        'level': profile_obj.level,
        'xp': xp_at_current,
        'total_xp': profile_obj.xp,
        'xp_for_next': xp_for_next,
        'level_progress': profile_obj.get_progress_to_next_level(),
        'xp_to_next': xp_to_next,
        'completed_lessons': completed,
        'total_lessons': total,
        'progress_percent': round(completed / total * 100) if total > 0 else 0,
        'date_joined': request.user.date_joined.strftime('%d.%m.%Y'),
        'edit_url': '/profile/edit/',
        'achievements_url': '/achievements/',
        'logout_url': '/logout/',
        'csrf_token': f'<input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get("CSRF_COOKIE", "")}">'
    }
    
    return JsonResponse(data)

@login_required
def edit_profile(request):
    profile_obj = UserProfile.objects.get_or_create(user=request.user)[0]
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        bio = request.POST.get('bio', '').strip()
        avatar = request.FILES.get('avatar')
        
        errors = []
        
        if username:
            if len(username) < 3:
                errors.append('Имя пользователя должно быть не менее 3 символов')
            elif len(username) > 10:
                errors.append('Имя пользователя не должно превышать 10 символов')
            elif User.objects.filter(username=username).exclude(id=request.user.id).exists():
                errors.append('Такое имя пользователя уже занято')
            else:
                request.user.username = username
        
        if email:
            if '@' not in email:
                errors.append('Некорректный email')
            elif User.objects.filter(email=email).exclude(id=request.user.id).exists():
                errors.append('Такой email уже используется')
            else:
                request.user.email = email
        
        if len(bio) > 500:
            errors.append('Биография не должна превышать 500 символов')
        else:
            profile_obj.bio = bio
        
        if avatar:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            file_ext = avatar.name.split('.')[-1].lower()
            if file_ext not in allowed_extensions:
                errors.append(f'Недопустимый формат файла. Разрешены: {", ".join(allowed_extensions)}')
            elif avatar.size > 5 * 1024 * 1024:
                errors.append('Размер файла не должен превышать 5 MB')
            else:
                if profile_obj.avatar:
                    if default_storage.exists(profile_obj.avatar.name):
                        default_storage.delete(profile_obj.avatar.name)
                profile_obj.avatar = avatar
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            request.user.save()
            profile_obj.save()
            messages.success(request, 'Профиль успешно обновлён!')
            return redirect('profile')
    
    return render(request, 'accounts/edit_profile.html', {'profile': profile_obj})

@login_required
def achievements(request):
    from lessons.models import Achievement, UserAchievement, CourseChat
    
    profile_obj = UserProfile.objects.get_or_create(user=request.user)[0]
    completed = UserProgress.objects.filter(user=request.user, is_completed=True).count()
    total = Lesson.objects.count()
    
    all_achievements = Achievement.objects.filter(is_hidden=False).order_by('order', 'title')
    
    achievements_list = []
    for ach in all_achievements:
        earned = UserAchievement.objects.filter(user=request.user, achievement=ach).exists()
        current_value = 0
        target_value = ach.condition_value
        
        # ✅ Получаем текущее значение прогресса в зависимости от типа достижения
        if ach.condition_type == 'lessons_completed':
            current_value = completed
        elif ach.condition_type == 'xp_earned':
            current_value = profile_obj.xp
            target_value = ach.condition_value
        elif ach.condition_type == 'level_reached':
            current_value = profile_obj.level
            target_value = ach.condition_value
        elif ach.condition_type == 'control_completed':
            current_value = UserProgress.objects.filter(
                user=request.user, is_completed=True, lesson__is_control=True
            ).count()
            target_value = ach.condition_value
        elif ach.condition_type == 'chat_messages':
            current_value = CourseChat.objects.filter(user=request.user).count()
            target_value = ach.condition_value
        elif ach.condition_type == 'courses_completed':
            from django.db.models import Count, F, Q
            from lessons.models import Course
            current_value = Course.objects.annotate(
                total_lessons=Count('lesson'),
                completed_lessons=Count('lesson__userprogress', filter=Q(lesson__userprogress__user=request.user, lesson__userprogress__is_completed=True))
            ).filter(total_lessons=F('completed_lessons'), total_lessons__gt=0).count()
            target_value = ach.condition_value
        
        # ✅ Рассчитываем процент прогресса
        progress = min(100, round(current_value / target_value * 100)) if target_value > 0 else 0
        
        achievements_list.append({
            'achievement': ach,
            'earned': earned,
            'current_value': current_value,  # ✅ Текущее значение
            'target_value': target_value,    # ✅ Целевое значение
            'progress': progress if not earned else 100,
        })
    
    earned_count = UserAchievement.objects.filter(user=request.user).count()
    total_count = Achievement.objects.filter(is_hidden=False).count()
    progress_percent_total = round(earned_count / total_count * 100) if total_count > 0 else 0
    
    context = {
        'completed_lessons': completed,      
        'total_lessons': total,          
        'progress_percent': round(completed / total * 100) if total > 0 else 0,
        'user_xp': profile_obj.get_xp_at_current_level(),  
        'user_level': profile_obj.level,   
        'total_xp': profile_obj.xp,        
    }
    return render(request, 'lessons/achievements.html', context)

@login_required
def view_user_profile(request, user_id):
    viewed_user = get_object_or_404(User, id=user_id)
    profile_obj = UserProfile.objects.get_or_create(user=viewed_user)[0]
    completed = UserProgress.objects.filter(user=viewed_user, is_completed=True).count()
    total = Lesson.objects.count()
    
    xp_at_current = profile_obj.get_xp_at_current_level()
    xp_for_next = profile_obj.get_xp_for_next_level()
    xp_to_next = xp_for_next - xp_at_current
    if xp_to_next < 0:
        xp_to_next = 0
    
    context = {
        'viewed_user': viewed_user,
        'profile': profile_obj,
        'completed_lessons': completed,
        'total_lessons': total,
        'progress_percent': round(completed / total * 100) if total > 0 else 0,
        'user_xp': xp_at_current,
        'user_level': profile_obj.level,
        'xp_for_next_level': xp_for_next,
        'level_progress': profile_obj.get_progress_to_next_level(),
        'xp_to_next_level': xp_to_next,
        'is_own_profile': viewed_user == request.user,
    }
    return render(request, 'accounts/view_user_profile.html', context)