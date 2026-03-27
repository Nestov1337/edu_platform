# lessons/models.py
import ast
import re
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, F, Q

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    xp = models.IntegerField("Опыт", default=0)
    level = models.IntegerField("Уровень", default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    avatar = models.ImageField("Аватар", upload_to='avatars/', blank=True, null=True)
    bio = models.TextField("О себе", max_length=500, blank=True, default="")
    
    def __str__(self):
        return f'{self.user.username} (Уровень {self.level}, {self.xp} XP)'
    
    def get_xp_for_next_level(self):
        return 100 + (self.level - 1) * 50
    
    def get_total_xp_for_level(self, target_level):
        if target_level <= 1:
            return 0
        total = 0
        for lvl in range(1, target_level):
            total += 100 + (lvl - 1) * 50
        return total
    
    def get_xp_at_current_level(self):
        xp_for_current_level = self.get_total_xp_for_level(self.level)
        return self.xp - xp_for_current_level
    
    def get_progress_to_next_level(self):
        xp_at_current = self.get_xp_at_current_level()
        xp_needed = self.get_xp_for_next_level()
        return round(xp_at_current / xp_needed * 100) if xp_needed > 0 else 0
    
    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.get_total_xp_for_level(self.level + 1):
            self.level += 1
        self.save()
    
    def can_send_message(self):
        last_message = CourseChat.objects.filter(user=self.user).order_by('-created_at').first()
        if last_message:
            time_diff = timezone.now() - last_message.created_at
            return time_diff.total_seconds() >= 10
        return True
    
    def get_last_message_time(self):
        last_message = CourseChat.objects.filter(user=self.user).order_by('-created_at').first()
        if last_message:
            return last_message.created_at
        return None
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        ordering = ['-xp', '-level']

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Course(models.Model):
    title = models.CharField("Название курса", max_length=200)
    description = models.TextField("Описание курса")
    color = models.CharField("Цвет курса", max_length=7, default="#0ea5e9")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def get_lessons_count(self):
        return self.lesson_set.count()
    
    def get_user_progress(self, user):
        completed = UserProgress.objects.filter(
            lesson__course=self,
            user=user,
            is_completed=True
        ).count()
        total = self.get_lessons_count()
        return round(completed / total * 100) if total > 0 else 0
    
    def get_chat_messages(self):
        return CourseChat.objects.filter(course=self).select_related('user').order_by('-created_at')[:50]
    
    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ['-created_at']

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="Курс")
    title = models.CharField("Название урока", max_length=200)
    content = models.TextField("Текст урока (теория)")
    code_task = models.TextField("Задание для кода")
    order = models.IntegerField("Порядок", default=0)
    
    is_control = models.BooleanField("Контрольная работа", default=False)
    xp_reward = models.IntegerField("Награда XP", default=50)
    expected_output = models.TextField("Ожидаемый вывод кода", blank=True)
    test_input = models.TextField("Тестовые входные данные", blank=True)
    max_attempts = models.IntegerField("Максимум попыток", default=0)
    
    require_input = models.BooleanField("Требовать input()", default=True)
    require_variable = models.CharField(
        "Обязательная переменная", 
        max_length=50, 
        blank=True,
        help_text="Название переменной"
    )
    forbidden_values = models.TextField(
        "Запрещённые значения", 
        blank=True,
        help_text="Через запятую"
    )
    check_ast = models.BooleanField("Включить проверку структуры", default=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.xp_reward == 0:
            self.xp_reward = 100 if self.is_control else 50
        super().save(*args, **kwargs)
    
    def _parse_forbidden_values(self):
        if not self.forbidden_values:
            return []
        return [v.strip() for v in self.forbidden_values.split(',') if v.strip()]
    
    def _check_ast_structure(self, code):
        errors = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Синтаксическая ошибка: {e}"]
        
        has_input = False
        has_assignment = False
        variable_names = set()
        hardcoded_strings = set()
        hardcoded_numbers = set()
        print_values = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'input':
                    has_input = True
            
            if isinstance(node, ast.Assign):
                has_assignment = True
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variable_names.add(target.id)
            
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                hardcoded_strings.add(node.value)
            
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                hardcoded_numbers.add(node.value)
            
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    for arg in node.args:
                        if isinstance(arg, ast.Constant):
                            print_values.add(str(arg.value))
        
        if self.require_input and not has_input:
            errors.append("В коде должно быть использование input()")
        
        if self.require_variable and self.require_variable not in variable_names:
            errors.append(f"Должна быть создана переменная '{self.require_variable}'")
        
        forbidden = self._parse_forbidden_values()
        for value in forbidden:
            if value.isdigit() and int(value) in hardcoded_numbers:
                errors.append(f"Нельзя использовать значение {value} (хардкод)")
            elif value in hardcoded_strings:
                errors.append(f"Нельзя использовать строку '{value}' (хардкод)")
            elif value in print_values:
                errors.append(f"Нельзя просто вывести {value}")
        
        if not has_assignment and (has_input or self.require_variable):
            errors.append("В коде должно быть присваивание переменной")
        
        return errors
    
    def check_code(self, user_code):
        if self.check_ast:
            ast_errors = self._check_ast_structure(user_code)
            if ast_errors:
                return False, "\n".join(ast_errors)
        
        if not self.expected_output:
            return True, "Код прошёл проверку структуры!"
        
        try:
            safe_globals = {"__builtins__": {
                "print": print, "input": input, "len": len, "range": range,
                "int": int, "float": float, "str": str, "list": list,
                "dict": dict, "set": set, "tuple": tuple,
                "abs": abs, "min": min, "max": max, "sum": sum,
                "sorted": sorted, "enumerate": enumerate, "zip": zip,
            }}
            safe_locals = {}
            
            if self.test_input:
                inputs = self.test_input.strip().split('\n')
                input_index = [0]
                
                def mock_input(prompt=''):
                    if input_index[0] < len(inputs):
                        val = inputs[input_index[0]].strip()
                        input_index[0] += 1
                        return val
                    return ''
                
                safe_globals['input'] = mock_input
            
            import io, sys
            output_buffer = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = output_buffer
            
            exec(user_code, safe_globals, safe_locals)
            
            sys.stdout = old_stdout
            actual_output = output_buffer.getvalue()
            
            actual_lines = [line.rstrip() for line in actual_output.split('\n')]
            expected_lines = [line.rstrip() for line in self.expected_output.split('\n')]
            
            while actual_lines and actual_lines[-1] == '':
                actual_lines.pop()
            while expected_lines and expected_lines[-1] == '':
                expected_lines.pop()
            
            if actual_lines == expected_lines:
                return True, "✅ Код верный! Вывод совпадает."
            else:
                error_msg = "Неправильный вывод."
                error_msg += "\nОжидалось: "
                error_msg += '\n'.join(expected_lines) + '.'
                error_msg += " Получено:\n"
                error_msg += '\n'.join(actual_lines)
                
                if len(actual_lines) != len(expected_lines):
                    error_msg += f"\n\n⚠️ Количество строк не совпадает: ожидалось {len(expected_lines)}, получено {len(actual_lines)}"
                else:
                    for i, (exp, act) in enumerate(zip(expected_lines, actual_lines)):
                        if exp != act:
                            error_msg += f"\n\nСтрока {i+1} не совпадает.\n   Ожидалось: {exp}. \n   Получено: {act}"
                            break
                
                return False, error_msg
                
        except Exception as e:
            return False, f"❌ Ошибка выполнения: {type(e).__name__}: {e}"
    
    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ['order']

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    code_solution = models.TextField(blank=True)
    attempts_count = models.IntegerField("Попыток сделано", default=0)
    last_attempt_result = models.TextField("Результат последней проверки", blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    xp_earned = models.IntegerField("Получено XP", default=0)
    
    class Meta:
        unique_together = ('user', 'lesson')
        verbose_name = "Прогресс"
        verbose_name_plural = "Прогресс пользователей"

class CourseChat(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField("Сообщение", max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField("Удалено", default=False)
    
    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username}: {self.message[:50]}'
    
    @staticmethod
    def contains_link(text):
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
            r'(?:%[0-9a-fA-F][0-9a-fA-F]))+|'
            r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
            r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return bool(url_pattern.search(text))
    
    @staticmethod
    def is_spam(text, user_id):
        recent_messages = CourseChat.objects.filter(
            user_id=user_id,
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).values_list('message', flat=True)[:5]
        
        if recent_messages.count() >= 3 and text in recent_messages:
            return True
        return False

class Achievement(models.Model):
    CONDITION_CHOICES = [
        ('lessons_completed', 'Пройдено уроков'),
        ('courses_completed', 'Пройдено курсов'),
        ('control_completed', 'Пройдено контрольных'),
        ('xp_earned', 'Заработано XP'),
        ('level_reached', 'Достигнут уровень'),
        ('first_login', 'Первый вход'),
        ('chat_messages', 'Сообщений в чате'),
    ]
    
    title = models.CharField("Название", max_length=100)
    description = models.TextField("Описание")
    icon = models.CharField("Иконка", max_length=10, default="🏆")
    condition_type = models.CharField("Тип условия", max_length=30, choices=CONDITION_CHOICES)
    condition_value = models.IntegerField("Значение условия")
    xp_reward = models.IntegerField("Награда XP", default=0)
    is_hidden = models.BooleanField("Скрытое достижение", default=False)
    order = models.IntegerField("Порядок отображения", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.icon} {self.title}"
    
    def check_and_award(self, user):
        if UserAchievement.objects.filter(user=user, achievement=self).exists():
            return False
        
        earned = False
        
        if self.condition_type == 'lessons_completed':
            completed = UserProgress.objects.filter(user=user, is_completed=True).count()
            earned = completed >= self.condition_value
        elif self.condition_type == 'courses_completed':
            courses = Course.objects.annotate(
                total_lessons=Count('lesson'),
                completed_lessons=Count('lesson__userprogress', filter=Q(lesson__userprogress__user=user, lesson__userprogress__is_completed=True))
            ).filter(total_lessons=F('completed_lessons'), total_lessons__gt=0)
            earned = courses.count() >= self.condition_value
        elif self.condition_type == 'control_completed':
            completed = UserProgress.objects.filter(user=user, is_completed=True, lesson__is_control=True).count()
            earned = completed >= self.condition_value
        elif self.condition_type == 'xp_earned':
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                earned = profile.xp >= self.condition_value
        elif self.condition_type == 'level_reached':
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                earned = profile.level >= self.condition_value
        elif self.condition_type == 'first_login':
            earned = user.last_login is not None and self.condition_value == 1
        elif self.condition_type == 'chat_messages':
            count = CourseChat.objects.filter(user=user).count()
            earned = count >= self.condition_value
        
        if earned:
            UserAchievement.objects.create(user=user, achievement=self, earned_at=timezone.now())
            if self.xp_reward > 0:
                profile = UserProfile.objects.get_or_create(user=user)[0]
                profile.add_xp(self.xp_reward)
            return True
        
        return False
    
    class Meta:
        verbose_name = "Достижение"
        verbose_name_plural = "Достижения"
        ordering = ['order', 'title']

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField("Получено", auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'achievement')
        verbose_name = "Полученное достижение"
        verbose_name_plural = "Полученные достижения"
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} — {self.achievement.title}"