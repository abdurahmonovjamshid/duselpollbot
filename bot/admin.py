from django.contrib import admin
from .models import TgUser, PollVote, Poll, PollOption

@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'phone', 'created_at')

    fieldsets = (
        ("User Information", {
            'fields': ('telegram_id', 'first_name', 'last_name', 'phone', 'username'),
        }),
        ('Additional Information', {
            'fields': ('created_at', 'step', 'deleted'),
        }),
    )

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_add_permission(self, *args, **kwargs):
        return False

class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 1


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ['id', 'question']
    inlines = [PollOptionInline]


@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'poll', 'text']
    list_filter = ['poll']


@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_poll_question', 'get_option_text', 'get_user_full_name', 'telegram_id', 'chat_id', 'channel_title', 'voted_at']
    list_filter = ['poll__question', 'option__text', 'chat_id', 'voted_at']
    search_fields = ['telegram_id', 'user__first_name', 'user__last_name', 'user__username', 'poll__question', 'option__text']

    def get_poll_question(self, obj):
        return obj.poll.question
    get_poll_question.short_description = 'Poll Question'

    def get_option_text(self, obj):
        return obj.option.text
    get_option_text.short_description = 'Option'

    def get_user_full_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name} (@{obj.user.username})"
        return obj.telegram_id
    get_user_full_name.short_description = 'User'

