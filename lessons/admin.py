from django.contrib import admin
from .models import Course, Lesson, UserProgress, UserProfile, CourseChat, Achievement, UserAchievement

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'xp', 'created_at']
    list_filter = ['level']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-xp', '-level']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_lessons_count', 'created_at']
    search_fields = ['title', 'description']
    fields = ['title', 'description', 'color']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_control', 'xp_reward', 'id']
    list_editable = ['order']
    list_filter = ['course', 'is_control']
    search_fields = ['title', 'content']
    ordering = ['course', 'order']
    
    fieldsets = (
        ('Основное', {
            'fields': ['course', 'title', 'order', 'content']
        }),
        ('Задание', {
            'fields': ['code_task']
        }),
        ('Автопроверка вывода', {
            'fields': ['expected_output', 'test_input'],
            'description': 'Для проверки результата выполнения кода'
        }),
        ('Проверка структуры кода', {
            'fields': ['check_ast', 'require_input', 'require_variable', 'forbidden_values'],
            'description': 'Что должно/не должно быть в коде ученика'
        }),
        ('Награда и контрольная', {
            'fields': ['is_control', 'xp_reward', 'max_attempts'],
            'description': 'Настройки для контрольных работ и XP'
        }),
    )

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'is_completed', 'xp_earned', 'attempts_count', 'completed_at']
    list_filter = ['is_completed', 'lesson__course']
    search_fields = ['user__username']

@admin.register(CourseChat)
class CourseChatAdmin(admin.ModelAdmin):
    list_display = ['course', 'user', 'message', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['icon', 'title', 'condition_type', 'condition_value', 'xp_reward', 'order', 'is_hidden']
    list_editable = ['order', 'is_hidden']
    list_filter = ['condition_type', 'is_hidden']
    search_fields = ['title', 'description']
    ordering = ['order', 'title']
    
    fieldsets = (
        ('Основное', {
            'fields': ['title', 'description', 'icon', 'order']
        }),
        ('Условие получения', {
            'fields': ['condition_type', 'condition_value']
        }),
        ('Награда', {
            'fields': ['xp_reward']
        }),
        ('Настройки', {
            'fields': ['is_hidden']
        }),
    )

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'earned_at']
    list_filter = ['achievement', 'earned_at']
    search_fields = ['user__username', 'achievement__title']
    ordering = ['-earned_at']
    readonly_fields = ['earned_at']