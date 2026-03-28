from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, F
from .models import Course, Lesson, UserProgress, UserProfile, CourseChat, Achievement, UserAchievement

@login_required
def course_list(request):
    courses = Course.objects.all()
    courses_data = []
    
    for course in courses:
        lessons_count = course.lesson_set.count()
        completed = UserProgress.objects.filter(
            lesson__course=course,
            user=request.user,
            is_completed=True
        ).count()
        progress = round(completed / lessons_count * 100) if lessons_count > 0 else 0
        
        courses_data.append({
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'color': course.color,
            'lessons_count': lessons_count,
            'progress': progress,
        })
    
    return render(request, 'lessons/course_list.html', {'courses': courses_data})

@login_required
def lesson_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lesson_set.all().order_by('order')
    
    completed_ids = UserProgress.objects.filter(
        user=request.user,
        is_completed=True
    ).values_list('lesson_id', flat=True)
    
    unlocked_until = 0
    for lesson in lessons:
        if lesson.order == 1 or lesson.order <= unlocked_until + 1:
            lesson.is_accessible = True
            if lesson.id in completed_ids:
                unlocked_until = lesson.order
        else:
            lesson.is_accessible = False
        lesson.is_completed = lesson.id in completed_ids
    
    chat_messages = CourseChat.objects.filter(course=course).select_related('user').order_by('-created_at')[:20]
    
    return render(request, 'lessons/lesson_list.html', {
        'course': course,
        'lessons': lessons,
        'chat_messages': chat_messages,
    })

@login_required
def lesson_detail(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    
    course_lessons = Lesson.objects.filter(course=lesson.course).order_by('order')
    completed_ids = UserProgress.objects.filter(
        user=request.user,
        is_completed=True
    ).values_list('lesson_id', flat=True)
    
    for prev in course_lessons:
        if prev.order >= lesson.order:
            break
        if prev.id not in completed_ids:
            messages.warning(request, f'Сначала пройдите урок "{prev.title}"')
            return redirect('lesson_list', course_id=lesson.course.id)
    
    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )
    
    if lesson.is_control and lesson.max_attempts > 0:
        if progress.attempts_count >= lesson.max_attempts and not progress.is_completed:
            messages.error(
                request, 
                f'Превышено количество попыток ({lesson.max_attempts}). Обратитесь к преподавателю.'
            )
            return redirect('lesson_list', course_id=lesson.course.id)
    
    if request.method == 'POST':
        user_code = request.POST.get('code', '')
        
        progress.attempts_count += 1
        
        is_correct, message = lesson.check_code(user_code)
        progress.last_attempt_result = message
        
        if is_correct:
            if not progress.is_completed:
                progress.is_completed = True
                progress.code_solution = user_code
                progress.completed_at = timezone.now()
                progress.xp_earned = lesson.xp_reward
                
                profile = UserProfile.objects.get_or_create(user=request.user)[0]
                profile.add_xp(lesson.xp_reward)
                
                # 🔔 Проверка достижений
                check_achievements_for_user(request.user)
                
            else:
                messages.info(request, 'Вы уже прошли этот урок')
            
            progress.save()
            return redirect('lesson_detail', pk=lesson.id)
        else:
            progress.code_solution = user_code
            progress.save()
            # ❌ Не показываем ошибку в messages — она в last_result
            return redirect('lesson_detail', pk=lesson.id)
    
    # Находим следующий урок
    next_lesson = Lesson.objects.filter(
        course=lesson.course, 
        order__gt=lesson.order
    ).order_by('order').first()
    
    context = {
        'lesson': lesson,
        'saved_code': progress.code_solution,
        'last_result': progress.last_attempt_result,
        'attempts_left': (
            lesson.max_attempts - progress.attempts_count 
            if lesson.is_control and lesson.max_attempts > 0 
            else None
        ),
        'is_control': lesson.is_control,
        'is_completed': progress.is_completed,
        'xp_reward': lesson.xp_reward,
        'next_lesson': next_lesson,
    }
    
    return render(request, 'lessons/detail.html', context)

@login_required
def profile(request):
    profile_obj = UserProfile.objects.get_or_create(user=request.user)[0]
    completed = UserProgress.objects.filter(user=request.user, is_completed=True).count()
    total = Lesson.objects.count()
    progress = UserProgress.objects.filter(user=request.user).select_related('lesson').order_by('-lesson__order')[:5]
    
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
    from django.contrib.auth.models import User
    from django.core.files.storage import default_storage
    
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
    profile_obj = UserProfile.objects.get_or_create(user=request.user)[0]
    completed = UserProgress.objects.filter(user=request.user, is_completed=True).count()
    total = Lesson.objects.count()
    
    all_achievements = Achievement.objects.filter(is_hidden=False).order_by('order', 'title')
    
    achievements_list = []
    for ach in all_achievements:
        earned = UserAchievement.objects.filter(user=request.user, achievement=ach).exists()
        current_value = 0
        target_value = ach.condition_value
        
        if ach.condition_type == 'lessons_completed':
            current_value = completed
        elif ach.condition_type == 'xp_earned':
            current_value = profile_obj.xp
        elif ach.condition_type == 'level_reached':
            current_value = profile_obj.level
        elif ach.condition_type == 'control_completed':
            current_value = UserProgress.objects.filter(
                user=request.user, is_completed=True, lesson__is_control=True
            ).count()
        elif ach.condition_type == 'chat_messages':
            current_value = CourseChat.objects.filter(user=request.user).count()
        elif ach.condition_type == 'courses_completed':
            current_value = Course.objects.annotate(
                total_lessons=Count('lesson'),
                completed_lessons=Count('lesson__userprogress', filter=Q(lesson__userprogress__user=request.user, lesson__userprogress__is_completed=True))
            ).filter(total_lessons=F('completed_lessons'), total_lessons__gt=0).count()
        
        progress = min(100, round(current_value / target_value * 100)) if target_value > 0 else 0
        
        achievements_list.append({
            'achievement': ach,
            'earned': earned,
            'current_value': current_value,
            'target_value': target_value,
            'progress': progress if not earned else 100,
        })
    
    earned_count = UserAchievement.objects.filter(user=request.user).count()
    total_count = Achievement.objects.filter(is_hidden=False).count()
    progress_percent_total = round(earned_count / total_count * 100) if total_count > 0 else 0
    
    context = {
        'completed_lessons': completed,
        'total_lessons': total,
        'progress_percent': round(completed / total * 100) if total > 0 else 0,
        'user_xp': profile_obj.xp,
        'user_level': profile_obj.level,
        'achievements': achievements_list,
        'earned_count': earned_count,
        'total_count': total_count,
        'progress_percent_total': progress_percent_total,
    }
    return render(request, 'lessons/achievements.html', context)

@login_required
def leaderboard(request):
    leaders = UserProfile.objects.select_related('user').all().order_by('-xp', '-level')[:50]
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    user_rank = UserProfile.objects.filter(xp__gt=user_profile.xp).count() + 1
    
    return render(request, 'lessons/leaderboard.html', {
        'leaders': leaders,
        'user_rank': user_rank,
        'user_profile': user_profile,
    })

@login_required
@require_POST
def send_chat_message(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    message_text = request.POST.get('message', '').strip()
    profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    if not profile.can_send_message():
        last_msg_time = profile.get_last_message_time()
        if last_msg_time:
            time_diff = timezone.now() - last_msg_time
            wait_time = int(10 - time_diff.total_seconds())
            return JsonResponse({
                'error': f'Подождите {wait_time} сек. перед следующим сообщением'
            }, status=429)
    
    if not message_text:
        return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)
    
    if len(message_text) > 1000:
        return JsonResponse({'error': 'Сообщение слишком длинное (макс. 1000 символов)'}, status=400)
    
    if CourseChat.contains_link(message_text):
        return JsonResponse({'error': 'Отправка ссылок запрещена'}, status=403)
    
    if CourseChat.is_spam(message_text, request.user.id):
        return JsonResponse({'error': 'Не отправляйте одинаковые сообщения'}, status=403)
    
    forbidden_words = ['спам', 'реклама', 'казино', 'ставки']
    for word in forbidden_words:
        if word in message_text.lower():
            return JsonResponse({'error': f'Сообщение содержит запрещённое слово'}, status=403)
    
    CourseChat.objects.create(
        course=course,
        user=request.user,
        message=message_text
    )
    
    check_achievements_for_user(request.user)
    
    chat_messages = CourseChat.objects.filter(course=course).select_related('user').order_by('-created_at')[:20]
    
    messages_html = ''
    for msg in reversed(chat_messages):
        messages_html += f'''
        <div class="chat-message" style="padding: 10px; margin: 5px 0; background: var(--bg); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <strong style="color: var(--primary);">{msg.user.username}</strong>
                <span style="font-size: 0.75rem; color: var(--text-light);">{msg.created_at.strftime("%H:%M")}</span>
            </div>
            <p style="margin: 0; color: var(--text);">{msg.message}</p>
        </div>
        '''
    
    return JsonResponse({'messages': messages_html, 'success': True})

@login_required
def get_chat_messages(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    chat_messages = CourseChat.objects.filter(course=course).select_related('user').order_by('-created_at')[:20]
    
    messages_html = ''
    for msg in reversed(chat_messages):
        messages_html += f'''
        <div class="chat-message" style="padding: 10px; margin: 5px 0; background: var(--bg); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <strong style="color: var(--primary);">{msg.user.username}</strong>
                <span style="font-size: 0.75rem; color: var(--text-light);">{msg.created_at.strftime("%H:%M")}</span>
            </div>
            <p style="margin: 0; color: var(--text);">{msg.message}</p>
        </div>
        '''
    
    return JsonResponse({'messages': messages_html})

def check_achievements_for_user(user):
    for achievement in Achievement.objects.all():
        achievement.check_and_award(user)