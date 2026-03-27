from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import register, custom_login, custom_logout, profile, view_user_profile, edit_profile, achievements, profile_data
from lessons.views import course_list, lesson_list, lesson_detail, leaderboard, send_chat_message, get_chat_messages

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', course_list, name='course_list'),
    path('course/<int:course_id>/', lesson_list, name='lesson_list'),
    path('lesson/<int:pk>/', lesson_detail, name='lesson_detail'),
    path('register/', register, name='register'),
    path('login/', custom_login, name='login'),
    path('logout/', custom_logout, name='logout'),
    path('profile/', profile, name='profile'),
    path('profile/<int:user_id>/', view_user_profile, name='view_user_profile'),
    path('profile/data/', profile_data, name='profile_data'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('achievements/', achievements, name='achievements'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('course/<int:course_id>/chat/send/', send_chat_message, name='send_chat_message'),
    path('course/<int:course_id>/chat/get/', get_chat_messages, name='get_chat_messages'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)